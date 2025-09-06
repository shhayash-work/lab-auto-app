"""
ラボ検証自動化システム - メインアプリケーション
Lab Validation Automation System - Main Application

KDDI様向けデモアプリケーション
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import uuid
from typing import List, Dict, Any, Optional
import logging
import time

# アプリケーション内部モジュール
from app.config.settings import STREAMLIT_CONFIG, APP_NAME, APP_VERSION
from app.models.validation import (
    TestItem, ValidationBatch, ValidationResult, TestCondition,
    TestCategory, EquipmentType, ValidationStatus, TestResult
)
from app.models.database import db_manager
from app.services.llm_service import get_llm_service
from app.services.validation_engine import get_validation_engine
from app.utils.excel_parser import parse_excel_test_items
from app.utils.star_chart import create_star_chart_dataframe

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit設定
st.set_page_config(**STREAMLIT_CONFIG)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2e86ab 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2e86ab;
    }
    .success-result {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
    }
    .fail-result {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
    }
    .warning-result {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

def initialize_app():
    """アプリケーションを初期化"""
    if 'initialized' not in st.session_state:
        # データベース初期化
        db_manager.create_tables()
        db_manager.init_sample_data()
        
        # セッション状態初期化
        st.session_state.initialized = True
        st.session_state.current_batch = None
        st.session_state.test_items = []
        st.session_state.validation_results = []
        
        logger.info("Application initialized")

def render_header():
    """ヘッダーを描画"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{APP_NAME}</h1>
        <p>AIエージェントを活用したネットワーク設備検証自動化システム v{APP_VERSION}</p>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard():
    """メインダッシュボードを描画"""
    st.header("ダッシュボード")
    
    # メトリクス表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="今日の検証",
            value="12件",
            delta="↑3"
        )
    
    with col2:
        st.metric(
            label="成功率",
            value="85%",
            delta="↑5%"
        )
    
    with col3:
        st.metric(
            label="実行中",
            value="3件",
            delta=""
        )
    
    with col4:
        st.metric(
            label="要確認",
            value="2件",
            delta="↓1"
        )
    
    # グラフ表示
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("検証結果分布")
        # サンプルデータでグラフ作成
        results_data = {
            'Result': ['PASS', 'FAIL', 'WARNING'],
            'Count': [15, 3, 2]
        }
        fig = px.pie(
            results_data, 
            values='Count', 
            names='Result',
            color_discrete_map={
                'PASS': '#28a745',
                'FAIL': '#dc3545', 
                'WARNING': '#ffc107'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("設備別成功率")
        equipment_data = {
            'Equipment': ['Ericsson-MMU', 'Ericsson-RRU', 'Samsung-AUv1', 'Samsung-AUv2'],
            'Success Rate': [90, 85, 88, 92]
        }
        fig = px.bar(
            equipment_data,
            x='Equipment',
            y='Success Rate',
            color='Success Rate',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def render_test_management():
    """検証項目管理を描画"""
    st.header("検証項目管理")
    
    # 作成方法選択
    method = st.radio(
        "検証項目の作成方法",
        ["AI自動生成", "Excelアップロード", "手動作成"],
        horizontal=True
    )
    
    if method == "AI自動生成":
        render_ai_generation()
    elif method == "Excelアップロード":
        render_excel_upload()
    elif method == "手動作成":
        render_manual_creation()
    
    # 既存の検証項目表示
    if st.session_state.test_items:
        st.subheader("現在の検証項目")
        render_test_items_table()

def render_ai_generation():
    """AI生成UI"""
    st.subheader("AI自動生成")
    
    col1, col2 = st.columns(2)
    
    with col1:
        feature_name = st.text_input("新機能名", placeholder="例: 基地局スリープ機能")
    
    with col2:
        equipment_types = st.multiselect(
            "対象設備",
            options=[eq.value for eq in EquipmentType],
            default=[EquipmentType.ERICSSON_MMU.value, EquipmentType.SAMSUNG_AUV1.value]
        )
    
    llm_provider = st.selectbox(
        "LLMプロバイダー",
        options=["ollama", "openai", "anthropic", "bedrock"],
        index=0
    )
    
    if st.button("AI生成実行", type="primary"):
        if feature_name and equipment_types:
            with st.spinner("検証項目を生成中..."):
                try:
                    llm_service = get_llm_service(llm_provider)
                    generated_items = llm_service.generate_test_items(feature_name, equipment_types)
                    
                    # TestItemオブジェクトに変換
                    test_items = []
                    for i, item in enumerate(generated_items):
                        test_item = TestItem(
                            id=str(uuid.uuid4()),
                            test_block=item.get('test_block', f'ブロック{i+1}'),
                            category=TestCategory.CM_DATA_ACQUISITION,  # デフォルト
                            condition=TestCondition(
                                condition_text=item.get('condition_text', ''),
                                expected_count=item.get('expected_count', 1),
                                equipment_types=[EquipmentType(eq) for eq in equipment_types]
                            ),
                            scenarios=item.get('scenarios', [f'{feature_name}正常動作'])
                        )
                        test_items.append(test_item)
                    
                    st.session_state.test_items = test_items
                    st.success(f"✅ {len(test_items)}個の検証項目を生成しました！")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 生成に失敗しました: {str(e)}")
        else:
            st.warning("機能名と対象設備を入力してください")

def render_excel_upload():
    """ExcelアップロードUI"""
    st.subheader("Excelアップロード")
    
    uploaded_file = st.file_uploader(
        "Excelファイルをアップロード",
        type=['xlsx', 'xls'],
        help="基地局スリープ機能の検証観点例のような形式のファイルをアップロードしてください"
    )
    
    if uploaded_file is not None:
        try:
            with st.spinner("Excelファイルを解析中..."):
                test_items = parse_excel_test_items(uploaded_file)
                st.session_state.test_items = test_items
                st.success(f"✅ {len(test_items)}個の検証項目をインポートしました！")
                st.rerun()
        except Exception as e:
            st.error(f"❌ ファイル解析に失敗しました: {str(e)}")

def render_manual_creation():
    """手動作成UI"""
    st.subheader("手動作成")
    
    with st.form("manual_test_item"):
        col1, col2 = st.columns(2)
        
        with col1:
            test_block = st.text_input("試験ブロック", placeholder="例: ESG選定")
            category = st.selectbox("カテゴリ", options=[cat.value for cat in TestCategory])
        
        with col2:
            condition_text = st.text_area("検証条件", placeholder="例: CMデータの取得成功")
            expected_count = st.number_input("期待件数", min_value=0, value=1)
        
        equipment_types = st.multiselect(
            "対象設備",
            options=[eq.value for eq in EquipmentType],
            default=[EquipmentType.ERICSSON_MMU.value]
        )
        
        scenarios = st.text_area(
            "シナリオ（改行区切り）",
            placeholder="正常スリープ\n異常データ"
        ).split('\n')
        scenarios = [s.strip() for s in scenarios if s.strip()]
        
        if st.form_submit_button("検証項目を追加"):
            if test_block and condition_text and equipment_types:
                test_item = TestItem(
                    id=str(uuid.uuid4()),
                    test_block=test_block,
                    category=TestCategory(category),
                    condition=TestCondition(
                        condition_text=condition_text,
                        expected_count=expected_count,
                        equipment_types=[EquipmentType(eq) for eq in equipment_types]
                    ),
                    scenarios=scenarios or [f"{test_block}正常動作"]
                )
                
                if 'test_items' not in st.session_state:
                    st.session_state.test_items = []
                st.session_state.test_items.append(test_item)
                st.success("✅ 検証項目を追加しました！")
                st.rerun()
            else:
                st.warning("必須項目を入力してください")

def render_test_items_table():
    """検証項目テーブルを描画"""
    if not st.session_state.test_items:
        st.info("検証項目がありません")
        return
    
    # データフレーム作成
    data = []
    for item in st.session_state.test_items:
        data.append({
            "ID": item.id[:8],
            "試験ブロック": item.test_block,
            "カテゴリ": item.category.value,
            "検証条件": item.condition.condition_text,
            "期待件数": item.condition.expected_count,
            "対象設備": ", ".join([eq.value for eq in item.condition.equipment_types]),
            "シナリオ数": len(item.scenarios)
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    # アクション
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("全削除"):
            st.session_state.test_items = []
            st.rerun()
    
    with col2:
        if st.button("保存"):
            # TODO: データベースに保存
            st.success("検証項目を保存しました")
    
    with col3:
        if st.button("検証実行"):
            if st.session_state.test_items:
                st.session_state.show_execution = True
                st.rerun()

def render_validation_execution():
    """検証実行UI"""
    st.header("検証実行")
    
    if not st.session_state.test_items:
        st.warning("検証項目がありません。まず検証項目を作成してください。")
        return
    
    # バッチ設定
    col1, col2 = st.columns(2)
    
    with col1:
        batch_name = st.text_input(
            "バッチ名",
            value=f"検証バッチ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    with col2:
        llm_provider = st.selectbox(
            "LLMプロバイダー",
            options=["ollama", "openai", "anthropic", "bedrock"],
            index=0
        )
    
    # 実行対象の選択
    st.subheader("実行対象")
    selected_items = []
    for i, item in enumerate(st.session_state.test_items):
        if st.checkbox(f"{item.test_block} - {item.category.value}", value=True, key=f"item_{i}"):
            selected_items.append(item)
    
    if st.button("検証開始", type="primary"):
        if selected_items:
            execute_validation_batch(selected_items, batch_name, llm_provider)
        else:
            st.warning("実行する検証項目を選択してください")

def execute_validation_batch(test_items: List[TestItem], batch_name: str, llm_provider: str):
    """検証バッチを実行"""
    # 検証エンジン初期化
    validation_engine = get_validation_engine(llm_provider)
    
    # バッチ作成
    batch = validation_engine.create_batch_from_test_items(test_items, batch_name)
    
    # 進捗表示
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    
    # 実行時間計測
    start_time = time.time()
    
    def progress_callback(progress: float, result: ValidationResult):
        """進捗コールバック"""
        progress_bar.progress(progress)
        status_text.text(f"実行中... {progress:.1%} 完了")
        
        # リアルタイム結果表示
        if batch.results:
            with results_container.container():
                render_realtime_results(batch.results[-5:])  # 最新5件
    
    try:
        # バッチ実行
        with st.spinner("検証を実行中..."):
            completed_batch = validation_engine.execute_batch(batch, progress_callback)
        
        execution_time = time.time() - start_time
        
        # 結果表示
        progress_bar.progress(1.0)
        status_text.text(f"✅ 完了! 実行時間: {execution_time:.1f}秒")
        
        # セッション状態に保存
        st.session_state.current_batch = completed_batch
        st.session_state.validation_results = completed_batch.results
        
        # 結果サマリー表示
        render_batch_summary(completed_batch)
        
    except Exception as e:
        st.error(f"❌ 検証実行に失敗しました: {str(e)}")
        logger.error(f"Validation execution failed: {e}")

def render_realtime_results(results: List[ValidationResult]):
    """リアルタイム結果表示"""
    st.subheader("最新の結果")
    
    for result in results:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        with col1:
            st.text(f"{result.equipment_type.value}")
        
        with col2:
            st.text(f"{result.scenario}")
        
        with col3:
            if result.result == TestResult.PASS:
                st.markdown('<div class="success-result">PASS</div>', unsafe_allow_html=True)
            elif result.result == TestResult.FAIL:
                st.markdown('<div class="fail-result">FAIL</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="warning-result">WARNING</div>', unsafe_allow_html=True)
        
        with col4:
            st.text(f"{result.execution_time:.1f}s")

def render_batch_summary(batch: ValidationBatch):
    """バッチサマリーを表示"""
    st.subheader("📊 実行結果サマリー")
    
    validation_engine = get_validation_engine()
    summary = validation_engine.get_batch_summary(batch)
    
    # メトリクス表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総テスト数", summary['total_tests'])
    
    with col2:
        st.metric("成功率", f"{summary['success_rate']:.1%}")
    
    with col3:
        st.metric("平均実行時間", f"{summary['average_execution_time']:.1f}秒")
    
    with col4:
        st.metric("完了時刻", batch.completed_at.strftime("%H:%M:%S") if batch.completed_at else "N/A")
    
    # 詳細結果
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("結果分布")
        result_counts = {
            'PASS': summary['pass_count'],
            'FAIL': summary['fail_count'],
            'WARNING': summary['warning_count']
        }
        
        fig = px.pie(
            values=list(result_counts.values()),
            names=list(result_counts.keys()),
            color_discrete_map={
                'PASS': '#28a745',
                'FAIL': '#dc3545',
                'WARNING': '#ffc107'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("設備別結果")
        equipment_summary = validation_engine.get_equipment_summary(batch)
        
        eq_data = []
        for eq_type, stats in equipment_summary.items():
            eq_data.append({
                'Equipment': eq_type,
                'Success Rate': stats['success_rate'],
                'Total Tests': stats['total']
            })
        
        if eq_data:
            eq_df = pd.DataFrame(eq_data)
            fig = px.bar(
                eq_df,
                x='Equipment',
                y='Success Rate',
                color='Success Rate',
                color_continuous_scale='RdYlGn',
                text='Total Tests'
            )
            fig.update_traces(texttemplate='%{text} tests', textposition='outside')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def render_results_viewer():
    """結果表示"""
    st.header("検証結果")
    
    if not st.session_state.validation_results:
        st.info("検証結果がありません。検証を実行してください。")
        return
    
    # フィルター
    col1, col2, col3 = st.columns(3)
    
    with col1:
        equipment_filter = st.multiselect(
            "設備フィルター",
            options=[eq.value for eq in EquipmentType],
            default=[eq.value for eq in EquipmentType]
        )
    
    with col2:
        result_filter = st.multiselect(
            "結果フィルター",
            options=[result.value for result in TestResult],
            default=[result.value for result in TestResult]
        )
    
    with col3:
        show_details = st.checkbox("詳細表示", value=False)
    
    # 結果をフィルタリング
    filtered_results = [
        result for result in st.session_state.validation_results
        if result.equipment_type.value in equipment_filter
        and result.result.value in result_filter
    ]
    
    # 星取表表示
    if st.checkbox("星取表表示", value=True):
        render_star_chart(filtered_results)
    
    # 詳細テーブル表示
    if show_details:
        render_detailed_results_table(filtered_results)

def render_star_chart(results: List[ValidationResult]):
    """星取表を表示"""
    st.subheader("⭐ 星取表")
    
    try:
        df = create_star_chart_dataframe(results)
        
        # スタイル適用
        def style_star_chart(val):
            if val == "●":
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif val == "×":
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            elif val == "△":
                return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            return ""
        
        styled_df = df.style.applymap(style_star_chart)
        st.dataframe(styled_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"星取表の生成に失敗しました: {str(e)}")
        logger.error(f"Star chart generation failed: {e}")

def render_detailed_results_table(results: List[ValidationResult]):
    """詳細結果テーブルを表示"""
    st.subheader("📋 詳細結果")
    
    # データフレーム作成
    data = []
    for result in results:
        data.append({
            "設備": result.equipment_type.value,
            "シナリオ": result.scenario,
            "結果": result.result.value,
            "実行時間": f"{result.execution_time:.2f}s",
            "信頼度": f"{result.confidence:.2f}",
            "エラー": result.error_message or "-",
            "実行時刻": result.created_at.strftime("%H:%M:%S")
        })
    
    df = pd.DataFrame(data)
    
    # 結果に応じて色分け
    def color_result(val):
        if val == "PASS":
            return "background-color: #d4edda"
        elif val == "FAIL":
            return "background-color: #f8d7da"
        elif val == "WARNING":
            return "background-color: #fff3cd"
        return ""
    
    styled_df = df.style.applymap(color_result, subset=['結果'])
    st.dataframe(styled_df, use_container_width=True)

def main():
    """メインアプリケーション"""
    # 初期化
    initialize_app()
    
    # ヘッダー
    render_header()
    
    # サイドバー
    with st.sidebar:
        st.title("メニュー")
        
        page = st.radio(
            "ページを選択",
            ["ダッシュボード", "検証項目管理", "検証実行", "結果表示"],
            index=0
        )
        
        st.divider()
        
        # システム情報
        st.subheader("システム情報")
        st.info(f"バージョン: {APP_VERSION}")
        
        # モック設備ステータス
        from mock_equipment.equipment_simulator import mock_equipment_manager
        equipment_status = mock_equipment_manager.get_equipment_status()
        
        st.subheader("設備ステータス")
        for eq_type, status in equipment_status.items():
            status_icon = "🟢" if status['status'] == 'active' else "🔴"
            st.text(f"{status_icon} {eq_type}")
    
    # メインコンテンツ
    if page == "ダッシュボード":
        render_dashboard()
    elif page == "検証項目管理":
        render_test_management()
    elif page == "検証実行":
        render_validation_execution()
    elif page == "結果表示":
        render_results_viewer()

if __name__ == "__main__":
    main()
