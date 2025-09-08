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
from app.services.mcp_validation_engine import get_unified_validation_engine
from app.services.provider_manager import get_provider_manager, ProviderStatus
from app.utils.excel_parser import parse_excel_test_items
from app.ui.qa_panel import render_qa_panel
from app.ui.review_panel import render_review_panel

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 星取表関数
def create_star_chart_dataframe(results: List[ValidationResult]) -> pd.DataFrame:
    """
    検証結果から星取表のDataFrameを作成（検証条件×設備のマトリクス形式）
    
    Args:
        results: 検証結果のリスト
        
    Returns:
        pd.DataFrame: 星取表形式のデータフレーム
    """
    if not results:
        return pd.DataFrame({"メッセージ": ["表示するデータがありません"]})
    
    try:
        # 検証条件別、設備別に結果を整理
        chart_data = []
        equipment_set = set()
        
        for i, result in enumerate(results, 1):
            # 結果の値を取得
            if isinstance(result, dict):
                equipment = result.get('equipment_type', 'Unknown')
                result_value = result.get('result', 'FAIL')
                condition = result.get('condition_text', '検証条件情報なし')
                test_item_id = result.get('test_item_id', '')
            else:
                # フル設備名を使用（高輪ゲートウェイシティ_Ericsson形式）
                equipment = result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type)
                result_value = result.result.value if hasattr(result.result, 'value') else str(result.result)
                test_item_id = getattr(result, 'test_item_id', '')
                
                # 検証条件を取得（複数の方法で試行）
                condition = '検証条件情報なし'
                
                # 1. 直接属性から取得
                if hasattr(result, 'condition_text'):
                    condition = result.condition_text
                # 2. セッション状態から検証項目を検索
                elif test_item_id:
                    test_items = st.session_state.get('test_items', [])
                    for item in test_items:
                        if hasattr(item, 'id') and item.id == test_item_id:
                            if hasattr(item, 'condition') and hasattr(item.condition, 'condition_text'):
                                condition = item.condition.condition_text
                                break
                # 3. scenarioから推測
                elif hasattr(result, 'scenario') and result.scenario:
                    condition = result.scenario
            
            # 設備名はフル名のまま使用（高輪ゲートウェイシティ_Ericsson形式）
            equipment_set.add(equipment)
            
            # 結果をシンボルに変換
            if result_value == 'PASS':
                symbol = "●"
            elif result_value == 'FAIL':
                symbol = "×"
            elif result_value == 'NEEDS_CHECK':
                symbol = "△"
            else:
                symbol = "-"
            
            # 行データとして保存（検証条件のみ）
            chart_data.append({
                '検証条件': condition,
                equipment: symbol
            })
        
        # DataFrameを作成
        if not chart_data:
            return pd.DataFrame({"メッセージ": ["表示するデータがありません"]})
        
        # 設備別にデータを統合
        consolidated_data = {}
        for row in chart_data:
            key = row['検証条件']
            if key not in consolidated_data:
                consolidated_data[key] = {'検証条件': key}
            
            # 設備の結果を追加
            for col, val in row.items():
                if col != '検証条件':
                    consolidated_data[key][col] = val
        
        # DataFrameに変換
        df_rows = list(consolidated_data.values())
        df = pd.DataFrame(df_rows)
        
        # 全設備に対して列を作成（存在しない組み合わせは"-"）
        for equipment in sorted(equipment_set):
            if equipment not in df.columns:
                df[equipment] = "-"
        
        # 欠損値を"-"で埋める
        df = df.fillna("-")
        
        # 列の順序を調整（検証条件、設備名でソート）
        fixed_cols = ['検証条件']
        equipment_cols = sorted([col for col in df.columns if col not in fixed_cols])
        df = df[fixed_cols + equipment_cols]
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to create star chart: {e}")
        return pd.DataFrame({"エラー": [f"星取表の作成に失敗しました: {str(e)}"]})

def convert_result_to_symbol(result: TestResult) -> str:
    """
    テスト結果を星取表の記号に変換
    
    Args:
        result: テスト結果
        
    Returns:
        str: 対応する記号
    """
    symbol_mapping = {
        TestResult.PASS: "●",        # 合格
        TestResult.FAIL: "×",        # 不合格
        TestResult.WARNING: "△",     # 警告
        TestResult.NOT_EXECUTED: "-" # 未実行
    }
    
    return symbol_mapping.get(result, "-")

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
    
    /* メトリクスカード */
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 12px;
        border-left: 5px solid #0052CC;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        margin: 12px 0;
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
    }
    
    .metric-card h3 {
        font-size: 26px !important;
        font-weight: 600 !important;
        margin: 0 0 8px 0 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        color: #2C3E50 !important;
    }
    
    .metric-value {
        font-size: 56px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        line-height: 1 !important;
        color: #0052CC !important;
    }
    
    .metric-delta {
        font-size: 20px !important;
        font-weight: 600 !important;
        margin: 4px 0 0 0 !important;
    }
    
    /* カスタムヘッダー（参考アプリスタイル） */
    .custom-header {
        font-size: 26px;
        font-weight: 700;
        color: #0052CC;
        margin: 24px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #0052CC;
        line-height: 1.3;
    }
</style>
""", unsafe_allow_html=True)

def load_realistic_batches():
    """リアルな検証バッチデータを読み込み"""
    try:
        import os
        realistic_file = 'data/realistic/realistic_batches.json'
        if os.path.exists(realistic_file):
            with open(realistic_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load realistic data: {e}")
    return []

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
    
    # 検証統計セクション
    st.markdown("<div class='custom-header'>検証統計</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>検証バッチの実行状況と成功率を一目で確認できます</p>", unsafe_allow_html=True)
    
    # リアルなデータを読み込み
    realistic_batches = load_realistic_batches()
    
    # 本日の検証数を計算（バッチ単位）
    today = datetime.now().strftime('%Y-%m-%d')
    today_batches = [b for b in realistic_batches if b.get('created_at', '').startswith(today)]
    today_count = len(today_batches)  # バッチ数
    
    # 成功数・失敗数・要確認数・実行中を計算（バッチ単位）
    success_count = 0
    fail_count = 0
    needs_check_count = 0
    running_count = 0
    
    for batch in today_batches:
        batch_status = calculate_batch_status(batch.get('results', []))
        
        if batch_status == "成功":
            success_count += 1
        elif batch_status == "失敗":
            fail_count += 1
        elif batch_status == "要確認":
            needs_check_count += 1
        elif batch_status == "実行中":
            running_count += 1
    
    # ダミーデータで補完（デモ用）
    if today_count == 0:
        today_count = 6
        success_count = 4
        fail_count = 1
        needs_check_count = 0
        running_count = 1
    
    # 失敗数（要確認）＝失敗数＋要確認数
    fail_and_check_count = fail_count + needs_check_count
    
    # 今日の検証に対する割合計算
    total_today = success_count + fail_count + needs_check_count + running_count
    success_percentage = int((success_count / total_today) * 100) if total_today > 0 else 67
    fail_and_check_percentage = int((fail_and_check_count / total_today) * 100) if total_today > 0 else 17
    running_percentage = int((running_count / total_today) * 100) if total_today > 0 else 16
    
    # メトリクス表示（件数ベースで4つのパネル）
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>本日の検証数</h3>
            <div class="metric-value">
                {today_count}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                100%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>成功数</h3>
            <div class="metric-value">
                {success_count}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                {success_percentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>失敗数（要確認）</h3>
            <div class="metric-value">
                {fail_and_check_count}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                {fail_and_check_percentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>実行中</h3>
            <div class="metric-value">
                {running_count}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                {running_percentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 検証バッチ一覧セクション（上に移動）
    st.markdown("<div class='custom-header'>検証バッチ一覧</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>過去に実行された検証バッチの履歴と実行結果を確認できます</p>", unsafe_allow_html=True)
    
    # タブで分類表示
    tab1, tab2, tab3, tab4 = st.tabs(["最新", "成功", "失敗", "実行中"])
    
    with tab1:
        st.write("**最新の10件を表示**")
        render_recent_batches("all", 10)
    
    with tab2:
        st.write("**最新の成功したもの10件**")
        render_recent_batches("success", 10)
    
    with tab3:
        st.write("**最新の検証が失敗したもの10件**")
        render_recent_batches("failed", 10)
    
    with tab4:
        st.write("**現在実行中の検証バッチ**")
        render_recent_batches("running", 10)
    
    # グラフ表示（下に移動）
    st.markdown("<div class='custom-header'>検証結果分析</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>検証結果の分布と設備別の成功率を可視化して傾向を把握できます</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**<span style='font-size: 22px; color: #000000;'>検証結果分布</span>**", unsafe_allow_html=True)
        
        # 実データに基づく結果分布計算
        def calculate_result_distribution(all_batches):
            success_count = fail_count = needs_check_count = running_count = 0
            
            for batch in all_batches:
                batch_status = calculate_batch_status(batch.get('results', []))
                if batch_status == "成功":
                    success_count += 1
                elif batch_status == "失敗":
                    fail_count += 1
                elif batch_status == "要確認":
                    needs_check_count += 1
                elif batch_status == "実行中":
                    running_count += 1
            
            return {
                'Result': ['成功', '失敗', '要確認', '実行中'],
                'Count': [success_count, fail_count, needs_check_count, running_count]
            }
        
        results_data = calculate_result_distribution(realistic_batches)
        
        fig = px.pie(
            results_data, 
            values='Count', 
            names='Result',
            color_discrete_map={
                '成功': '#28a745',  # 緑
                '失敗': '#dc3545',  # 赤
                '要確認': '#fd7e14', # オレンジ
                '実行中': '#007bff'  # 青
            }
        )
        # 参考アプリスタイルに合わせてフォントサイズを調整
        fig.update_traces(
            textfont_size=16, 
            textposition='inside',
            textinfo='label+percent'
        )
        fig.update_layout(
            font=dict(size=16),
            showlegend=True,
            legend=dict(
                font=dict(size=16),
                orientation="v",
                yanchor="middle",
                y=0.5
            ),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.markdown("**<span style='font-size: 22px; color: #000000;'>設備別成功率</span>**", unsafe_allow_html=True)
        
        # 実データに基づく設備別成功率計算
        def calculate_equipment_success_rate(all_batches):
            equipment_stats = {}
            
            for batch in all_batches:
                for result in batch.get('results', []):
                    eq_type = result.get('equipment_type', 'Unknown')
                    if eq_type not in equipment_stats:
                        equipment_stats[eq_type] = {'total': 0, 'success': 0}
                    
                    equipment_stats[eq_type]['total'] += 1
                    if result.get('result') == 'PASS':
                        equipment_stats[eq_type]['success'] += 1
            
            # 成功率計算とデータ構造変換
            equipment_data = {'Equipment': [], 'Success Rate': []}
            for eq_type, stats in equipment_stats.items():
                success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                equipment_data['Equipment'].append(eq_type)
                equipment_data['Success Rate'].append(round(success_rate, 1))
            
            return equipment_data
        
        equipment_data = calculate_equipment_success_rate(realistic_batches)
        fig = px.bar(
            equipment_data,
            x='Equipment',
            y='Success Rate',
            color='Success Rate',
            color_continuous_scale=[[0, '#dc3545'], [1, '#007bff']],  # 0%赤から100%青のグラデーション
            range_color=[0, 100]  # 色スケールを0-100に固定
        )
        fig.update_layout(
            showlegend=False,
            font=dict(size=14),
            xaxis=dict(
                tickfont=dict(size=12),
                title_font=dict(size=14)
            ),
            yaxis=dict(
                range=[0, 100],  # 縦軸を0-100に固定
                tickfont=dict(size=12),
                title_font=dict(size=14)
            ),
            margin=dict(t=50, b=50, l=50, r=50)
        )
        st.plotly_chart(fig, width="stretch")

def calculate_batch_status(batch_results):
    """バッチの統一ステータス判定"""
    if not batch_results:
        return "実行中"
    
    has_fail = any(r.get('result') == 'FAIL' for r in batch_results)
    has_needs_check = any(r.get('result') == 'NEEDS_CHECK' for r in batch_results) 
    has_running = any(r.get('result') == 'RUNNING' for r in batch_results)
    
    if has_running:
        return "実行中"  # 青
    elif has_fail:
        return "失敗"     # 赤  
    elif has_needs_check:
        return "要確認"   # オレンジ
    else:
        return "成功"     # 緑

def render_recent_batches(filter_type: str, limit: int):
    """最近の検証バッチを表示（リアルなデータ連携）"""
    # リアルなデータを読み込み
    realistic_batches = load_realistic_batches()
    
    # 実行時刻でソート（新しい順）
    sorted_batches = sorted(realistic_batches, key=lambda x: x.get('created_at', ''), reverse=True)
    
    # データを表示用に変換
    batch_data = []
    for batch in sorted_batches:
        # 成功率を計算
        results = batch.get('results', [])
        if results:
            pass_count = len([r for r in results if r.get('result') == 'PASS'])
            success_rate = int((pass_count / len(results)) * 100)
        else:
            success_rate = 0
        
        # 統一ステータス判定を使用
        status = calculate_batch_status(results)
        
        # フィルタリング
        if filter_type == "success" and status != "成功":
            continue
        elif filter_type == "failed" and status not in ["失敗", "要確認"]:
            continue
        elif filter_type == "running" and status != "実行中":
            continue
        
        # 実行時間を計算
        execution_time_display = '不明'
        if status == '実行中':
            execution_time_display = 'None（実行中）'
        else:
            # バッチの実行時間を計算
            results = batch.get('results', [])
            if results:
                # 全ての検証項目の実行時間を合計
                total_time = sum(r.get('execution_time', 0) for r in results)
                execution_time_display = f"{total_time:.1f}s"
            elif batch.get('completed_at') and batch.get('created_at'):
                # バッチレベルの時間計算
                try:
                    start_time = datetime.fromisoformat(batch['created_at'].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(batch['completed_at'].replace('Z', '+00:00'))
                    duration = (end_time - start_time).total_seconds()
                    execution_time_display = f"{duration:.1f}s"
                except:
                    execution_time_display = '不明'
        
        # 実行時刻を変換（表示用）
        created_at = batch.get('created_at', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                execution_date = dt.strftime('%m/%d %H:%M')
            except:
                execution_date = created_at[:16].replace('T', ' ')
        else:
            execution_date = '不明'
        
        # 実行時間を計算
        started_at = batch.get('started_at')
        completed_at = batch.get('completed_at')
        if started_at and completed_at:
            try:
                start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                duration = (end_dt - start_dt).total_seconds() / 60
                duration_str = f"{duration:.1f}分"
            except:
                duration_str = "不明"
        else:
            duration_str = "実行中" if status == "実行中" else "不明"
        
        batch_data.append({
            "バッチ名": batch.get('name', ''),
            "実行時刻": execution_date,
            "検証項目数": len(batch.get('test_items', [])),
            "成功率": f"{success_rate}%",
            "ステータス": status,
            "実行時間": execution_time_display
        })
        
        if len(batch_data) >= limit:
            break
    
    if batch_data:
        df = pd.DataFrame(batch_data)
        
        # ステータスに応じた色付け
        def color_status(val):
            if val == "成功":
                return 'background-color: #d4edda; color: #155724'
            elif val == "失敗":
                return 'background-color: #f8d7da; color: #721c24'
            elif val == "実行中":
                return 'background-color: #d1ecf1; color: #0c5460'
            return ''
        
        styled_df = df.style.map(color_status, subset=['ステータス'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("該当するバッチがありません")

def render_test_management(selected_provider=None):
    """検証項目管理を描画"""
    st.header("検証項目入力")
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>検証項目の作成・編集・管理を行い、AI自動生成やExcelインポートが可能です</p>", unsafe_allow_html=True)
    
    # 過去バッチ選択機能
    st.subheader("バッチ選択")
    saved_batches = st.session_state.get('saved_batches', [])
    
    if saved_batches:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            batch_options = ["新規作成"] + [f"{batch['name']} ({batch['created_at']}, {batch['item_count']}項目)" for batch in saved_batches]
            selected_batch_option = st.selectbox(
                "過去のバッチから選択",
                options=batch_options,
                help="過去に保存したバッチを選択して編集できます"
            )
        
        with col2:
            if st.button("バッチ読み込み") and selected_batch_option != "新規作成":
                # 選択されたバッチを読み込み
                batch_name = selected_batch_option.split(" (")[0]
                selected_batch = next((b for b in saved_batches if b['name'] == batch_name), None)
                
                if selected_batch:
                    st.session_state.test_items = selected_batch['test_items'].copy()
                    st.session_state.current_batch_name = selected_batch['name']
                    st.session_state.batch_saved = True
                    st.success(f"バッチ '{selected_batch['name']}' を読み込みました")
                    st.rerun()
    else:
        st.info("保存済みバッチがありません。新規作成してください。")
    
    # 作成方法選択
    method = st.radio(
        "検証項目の作成方法",
        ["AI自動生成", "Excelアップロード", "手動作成"],
        horizontal=True
    )
    
    if method == "AI自動生成":
        render_ai_generation(selected_provider)
    elif method == "Excelアップロード":
        render_excel_upload()
    elif method == "手動作成":
        render_manual_creation()
    
    # 既存の検証項目表示
    if st.session_state.test_items:
        st.subheader("現在の検証項目")
        render_test_items_table()

def render_ai_generation(selected_provider=None):
    """AI生成UI"""
    st.subheader("AI自動生成")
    
    col1, col2 = st.columns(2)
    
    with col1:
        feature_name = st.text_input("新機能名", placeholder="例: 基地局スリープ機能")
    
    with col2:
        # 生成項目数は自動決定（削除）
        pass
    
    # 設備選択を分離
    col3, col4 = st.columns(2)
    
    with col3:
        lab_name = st.text_input(
            "ラボ設備名",
            placeholder="例: 高輪ゲートウェイシティ",
            help="検証を実行するラボ設備名を入力"
        )
    
    with col4:
        vendors = ["Ericsson", "Nokia", "Samsung", "その他"]
        vendor_name = st.selectbox(
            "対象設備",
            options=vendors,
            help="検証対象の設備ベンダーを選択"
        )
        
        if vendor_name == "その他":
            vendor_name = st.text_input(
                "対象設備（手入力）",
                placeholder="例: Huawei"
            )
    
    # サイドバーで選択されたプロバイダーを使用
    if selected_provider:
        llm_provider = selected_provider
    else:
        st.warning("サイドバーでプロバイダーを選択してください")
        return
    
    if st.button("AI生成実行", type="primary"):
        if feature_name and lab_name and vendor_name:
            # 設備タイプを組み合わせ形式で作成
            equipment_type_str = f"{lab_name}_{vendor_name}"
            equipment_types = [equipment_type_str]
            try:
                # プロバイダー情報を表示
                provider_manager = get_provider_manager()
                provider_info = provider_manager.get_provider_info(llm_provider)
                
                # LLMサービスを初期化
                llm_service = get_llm_service(llm_provider)
                
                # AWS Bedrockの場合は進捗バーとAI思考を表示
                if llm_provider == "bedrock":
                    progress_bar = st.progress(0)
                    spinner_placeholder = st.empty()
                    thinking_container = st.empty()
                    
                    # AWS Bedrockの思考段階（偽装でも可）
                    thinking_stages = [
                        "検証項目の要件を分析中...",
                        "過去の類似検証項目をRAGで検索中...",
                        "対象設備の特性を考慮中...",
                        "正常系・異常系のシナリオを検討中...",
                        "検証条件の詳細を策定中...",
                        "検証項目の妥当性を確認中...",
                        "最終的な検証項目リストを作成中..."
                    ]
                    current_stage = 0
                    
                    def bedrock_progress_callback(progress: float, message: str):
                        nonlocal current_stage
                        
                        # プログレス値の範囲チェック
                        if progress > 1.0:
                            progress = 1.0
                        elif progress < 0.0:
                            progress = 0.0
                        
                        # プログレスバー更新
                        progress_bar.progress(progress)
                        
                        # スピナー表示（実行中... xx%済み）
                        with spinner_placeholder:
                            with st.spinner(f"実行中... {progress*100:.1f}%済み"):
                                pass
                        
                        # 進捗に応じて思考段階を更新
                        stage_index = min(int(progress * len(thinking_stages)), len(thinking_stages) - 1)
                        if stage_index != current_stage:
                            current_stage = stage_index
                        
                        current_thinking = thinking_stages[current_stage]
                        thinking_container.info(f"💭 {current_thinking}")
                    
                    generated_items = llm_service.generate_test_items(
                        feature_name, 
                        equipment_types,
                        progress_callback=bedrock_progress_callback
                    )
                    
                    # 完了表示
                    progress_bar.progress(1.0)
                    spinner_placeholder.empty()
                    thinking_container.success("💭 検証項目生成完了")
                    st.success("✅ 検証項目生成完了")
                    
                else:
                    # Ollama等の場合は進捗表示とステップ表示
                    progress_bar = st.progress(0)
                    spinner_placeholder = st.empty()
                    step_container = st.empty()
                    
                    # Ollamaのステップ表示
                    step_messages = [
                        "Ollamaモデルを初期化中...",
                        "検証項目の要件を分析中...",
                        "ベクトル検索で類似資料取得中...",
                        "対象設備の特性を考慮中...",
                        "検証条件の詳細を策定中...",
                        "検証項目リストを生成中..."
                    ]
                    current_step = 0
                    
                    def ollama_progress_callback(progress: float, message: str):
                        nonlocal current_step
                        
                        if progress > 1.0:
                            progress = 1.0
                        elif progress < 0.0:
                            progress = 0.0
                        
                        # プログレスバー更新
                        progress_bar.progress(progress)
                        
                        # スピナー表示（実行中... xx%済み）
                        with spinner_placeholder:
                            with st.spinner(f"実行中... {progress*100:.1f}%済み"):
                                pass
                        
                        # 進捗に応じてステップを更新
                        step_index = min(int(progress * len(step_messages)), len(step_messages) - 1)
                        if step_index != current_step:
                            current_step = step_index
                        
                        current_step_msg = step_messages[current_step]
                        step_container.info(f"🔄 {current_step_msg}")
                    
                    generated_items = llm_service.generate_test_items(
                        feature_name, 
                        equipment_types,
                        progress_callback=ollama_progress_callback
                    )
                    
                    # 完了表示
                    progress_bar.progress(1.0)
                    spinner_placeholder.empty()
                    step_container.success("🔄 検証項目生成完了")
                    st.success("✅ 検証項目生成完了")
                
                # TestItemオブジェクトに変換
                test_items = []
                for i, item in enumerate(generated_items):
                    test_item = TestItem(
                        id=str(uuid.uuid4()),
                        test_block=item.get('test_block', f'ブロック{i+1}'),
                        category=TestCategory.CM_DATA_ACQUISITION,  # デフォルト
                        condition=TestCondition(
                            condition_text=item.get('condition_text', ''),
                            equipment_types=[equipment_type_str]
                        ),
                    )
                    test_items.append(test_item)
                
                # セッション状態に保存
                st.session_state.test_items = test_items
                st.success(f"✅ AIエージェントが{len(test_items)}個の検証項目を生成しました！")
                
                # 生成されたLLM応答の詳細を表示
                with st.expander("AIエージェントの生成詳細"):
                    st.json(generated_items)
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ AIエージェント生成失敗: {str(e)}")
                st.warning("💡 LLMサービスの接続やAPI設定を確認してください")
                
                # エラー詳細を表示
                with st.expander("🔍 エラー詳細"):
                    st.code(f"Provider: {llm_provider}\nError: {str(e)}")
                
                logger.error(f"AI generation error: {e}")
        else:
            st.warning("機能名、ラボ設備名、対象設備を入力してください")

def render_excel_upload():
    """ExcelアップロードUI"""
    st.subheader("Excelアップロード")
    
    # アップロード説明
    st.markdown("""
    **アップロード可能なExcelファイル形式:**
    - 列: 検証シナリオ（正常系、準正常系、異常系など）
    - 行: 検証観点（CMデータ取得、スリープ機能動作など）
    - セル: 各シナリオ×観点の検証内容
    
    **参考例:** `/home/share/lab-auto-app/reference/lab-auto-app_検証観点例_v0.1.xlsx`
    """)
    
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
    
    # クリアフラグをチェック
    clear_inputs = st.session_state.get('clear_manual_inputs', False)
    if clear_inputs:
        st.session_state.clear_manual_inputs = False
    
    with st.form("manual_test_item", clear_on_submit=clear_inputs):
        # 基本情報
        col1, col2 = st.columns(2)
        
        with col1:
            test_block = st.text_input(
                "試験ブロック", 
                placeholder="例: 基地局スリープ機能",
                help="検証対象の機能名を入力"
            )
        
        with col2:
            category = st.text_input(
                "カテゴリ", 
                placeholder="例: CMデータの取得",
                help="検証観点を自由に記載してください",
                value="" if clear_inputs else st.session_state.get('manual_category', "")
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            lab_name = st.text_input(
                "ラボ設備名",
                placeholder="例: 高輪ゲートウェイシティ",
                value="" if clear_inputs else st.session_state.get('manual_lab_name', ""),
                help="検証を実行するラボ設備名を入力"
            )
        
        with col4:
            vendors = ["Ericsson", "Nokia", "Samsung", "その他"]
            vendor_name = st.selectbox(
                "対象設備",
                options=vendors,
                index=0 if clear_inputs else st.session_state.get('manual_vendor_index', 0),
                help="検証対象の設備ベンダーを選択"
            )
            
            if vendor_name == "その他":
                vendor_name = st.text_input(
                    "対象設備（手入力）",
                    placeholder="例: Huawei",
                    value="" if clear_inputs else st.session_state.get('manual_custom_vendor', "")
                )
        
        # 検証条件
        condition_text = st.text_area(
            "検証条件", 
            placeholder="例: スリープモード移行時のCMデータ取得",
            help="具体的な検証内容を記載",
            value="" if clear_inputs else st.session_state.get('manual_condition_text', "")
        )
        
        
        if st.form_submit_button("検証項目を追加"):
            if test_block and condition_text and lab_name and vendor_name:
                # カテゴリをTestCategoryから探すか、デフォルトを使用
                try:
                    test_category = TestCategory(category) if category in [cat.value for cat in TestCategory] else TestCategory.CM_DATA_ACQUISITION
                except:
                    test_category = TestCategory.CM_DATA_ACQUISITION
                
                # 設備タイプを組み合わせ形式で作成
                equipment_type_str = f"{lab_name}_{vendor_name}"
                
                test_item = TestItem(
                    id=str(uuid.uuid4()),
                    test_block=test_block,
                    category=test_category,
                    condition=TestCondition(
                        condition_text=condition_text,
                        equipment_types=[equipment_type_str]
                    )
                )
                
                if 'test_items' not in st.session_state:
                    st.session_state.test_items = []
                st.session_state.test_items.append(test_item)
                
                # バッチ名を更新（初回のみ）
                if 'current_batch_name' not in st.session_state:
                    jst_time = datetime.now() + timedelta(hours=9)
                    date_str = jst_time.strftime('%Y%m%d')
                    time_str = jst_time.strftime('%H%M%S')
                    st.session_state.current_batch_name = f"検証バッチ_{test_block}_{date_str}_{time_str}"
                
                # 保存ステータスを未保存に変更
                st.session_state.batch_saved = False
                
                # 入力欄をクリア（試験ブロック以外）
                st.session_state.clear_manual_inputs = True
                
                st.success("✅ 検証項目を追加しました！")
                st.rerun()
            else:
                st.warning("必須項目を入力してください")

def render_test_items_table():
    """検証項目テーブルを描画"""
    # バッチ名表示・編集
    if 'current_batch_name' not in st.session_state and st.session_state.get('test_items'):
        # 検証項目があるのにバッチ名がない場合、自動生成
        # JST時間で生成
        jst_time = datetime.now() + timedelta(hours=9)
        date_str = jst_time.strftime('%Y%m%d')
        time_str = jst_time.strftime('%H%M%S')
        st.session_state.current_batch_name = f"検証バッチ_基地局スリープ機能_{date_str}_{time_str}"
    
    current_batch_name = st.session_state.get('current_batch_name', '未保存のバッチ')
    
    # バッチ名編集機能
    col1, col2 = st.columns([3, 1])
    with col1:
        new_batch_name = st.text_input(
            "現在のバッチ名",
            value=current_batch_name,
            help="バッチ名を編集できます"
        )
        if new_batch_name != current_batch_name:
            st.session_state.current_batch_name = new_batch_name
    
    with col2:
        pass  # ステータス表示を削除
    
    if not st.session_state.test_items:
        st.info("検証項目がありません")
        return
    
    # データフレーム作成（チェックボックス付き）
    data = []
    for i, item in enumerate(st.session_state.test_items):
        data.append({
            "選択": False,
            "ID": item.id[:8],
            "試験ブロック": item.test_block,
            "カテゴリ": item.category.value if hasattr(item.category, 'value') else str(item.category),
            "検証条件": item.condition.condition_text,
            "対象設備": ", ".join([eq.value if hasattr(eq, 'value') else str(eq) for eq in item.condition.equipment_types]),
            "インデックス": i
        })
    
    df = pd.DataFrame(data)
    
    # チェックボックス付きの表を表示
    edited_df = st.data_editor(
        df.drop('インデックス', axis=1),
        column_config={
            "選択": st.column_config.CheckboxColumn(
                "選択",
                help="修正・削除する項目を選択してください",
                default=False,
            )
        },
        disabled=["ID", "試験ブロック", "カテゴリ", "検証条件", "期待件数", "対象設備", "シナリオ数"],
        hide_index=True,
        width="stretch"
    )
    
    # 選択された項目を取得
    selected_indices = []
    for i, row in edited_df.iterrows():
        if row["選択"]:
            selected_indices.append(i)
    
    # アクション（右寄せで3つ並べる）
    st.markdown("<div style='text-align: right; margin-top: 16px;'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("修正", disabled=len(selected_indices) == 0, use_container_width=True):
            if selected_indices:
                st.session_state.edit_items = [st.session_state.test_items[i] for i in selected_indices]
                st.session_state.show_edit_form = True
                st.rerun()
    
    with col2:
        if st.button("削除", disabled=len(selected_indices) == 0, use_container_width=True):
            if selected_indices:
                st.session_state.delete_indices = selected_indices
                st.session_state.show_delete_confirm = True
                st.rerun()
    
    with col3:
        if st.button("保存", use_container_width=True):
            # データベースに保存
            try:
                for item in st.session_state.test_items:
                    db_manager.save_test_item(item)
                
                # バッチ情報を保存
                batch_info = {
                    'name': st.session_state.current_batch_name,
                    'created_at': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                    'test_items': st.session_state.test_items,
                    'item_count': len(st.session_state.test_items)
                }
                
                # セッション状態に保存済みバッチを追加
                if 'saved_batches' not in st.session_state:
                    st.session_state.saved_batches = []
                
                # 既存バッチの更新または新規追加
                existing_batch = next((b for b in st.session_state.saved_batches if b['name'] == batch_info['name']), None)
                if existing_batch:
                    existing_batch.update(batch_info)
                else:
                    st.session_state.saved_batches.append(batch_info)
                
                # 保存ステータス更新
                st.session_state.batch_saved = True
                
                st.success(f"✅ 検証項目を '{st.session_state.current_batch_name}' として保存しました")
                
            except Exception as e:
                st.error(f"❌ 保存に失敗しました: {str(e)}")
                logger.error(f"Batch save failed: {e}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 削除確認ダイアログ
    if st.session_state.get('show_delete_confirm', False):
        st.warning("⚠️ 削除確認")
        st.write("以下の検証項目が選択されています。本当に削除しますか？")
        
        for idx in st.session_state.delete_indices:
            item = st.session_state.test_items[idx]
            st.write(f"- {item.id[:8]}: {item.test_block}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("削除実行", type="primary"):
                # 逆順でソートして削除（インデックスのずれを防ぐ）
                for idx in sorted(st.session_state.delete_indices, reverse=True):
                    st.session_state.test_items.pop(idx)
                st.session_state.show_delete_confirm = False
                st.session_state.delete_indices = []
                st.success("✅ 選択した項目を削除しました")
                st.rerun()
        
        with col2:
            if st.button("キャンセル"):
                st.session_state.show_delete_confirm = False
                st.session_state.delete_indices = []
                st.rerun()
    
    # 修正フォーム
    if st.session_state.get('show_edit_form', False):
        st.subheader("選択項目の修正")
        
        for i, item in enumerate(st.session_state.edit_items):
            with st.expander(f"項目 {i+1}: {item.test_block}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_test_block = st.text_input(
                        "試験ブロック", 
                        value=item.test_block, 
                        key=f"edit_block_{i}"
                    )
                    new_category = st.text_input(
                        "カテゴリ", 
                        value=item.category.value if hasattr(item.category, 'value') else str(item.category),
                        key=f"edit_category_{i}"
                    )
                
                with col2:
                    # 既存の設備タイプを文字列として取得（カンマ区切り）
                    current_equipment_text = ""
                    for eq in item.condition.equipment_types:
                        if hasattr(eq, 'value'):
                            value = eq.value
                        else:
                            value = str(eq)
                        if current_equipment_text:
                            current_equipment_text += ", "
                        current_equipment_text += value
                    
                    new_equipment_types = st.text_input(
                        "対象設備",
                        value=current_equipment_text,
                        key=f"edit_equipment_{i}",
                        help="設備名をカンマ区切りで入力してください"
                    )
                
                new_condition_text = st.text_area(
                    "検証条件", 
                    value=item.condition.condition_text,
                    key=f"edit_condition_{i}"
                )
                
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("更新", type="primary"):
                # 修正内容を反映
                for i, item in enumerate(st.session_state.edit_items):
                    # 元の項目を見つけて更新
                    original_idx = next(j for j, orig_item in enumerate(st.session_state.test_items) if orig_item.id == item.id)
                    
                    # カテゴリ処理
                    try:
                        category_value = st.session_state[f"edit_category_{i}"]
                        test_category = TestCategory(category_value) if category_value in [cat.value for cat in TestCategory] else TestCategory.FUNCTIONAL
                    except:
                        test_category = TestCategory.FUNCTIONAL
                    
                    # 設備タイプを文字列から分割してリストに変換（カンマ区切り）
                    equipment_text = st.session_state[f"edit_equipment_{i}"]
                    equipment_list = [eq.strip() for eq in equipment_text.split(',') if eq.strip()]
                    
                    # 利用可能な設備タイプに一致するもののみ使用、そうでなければそのまま文字列として保持
                    equipment_types = []
                    for eq_name in equipment_list:
                        try:
                            # EquipmentTypeに存在するかチェック
                            eq_type = None
                            for et in EquipmentType:
                                if et.value == eq_name:
                                    eq_type = et
                                    break
                            if eq_type:
                                equipment_types.append(eq_type)
                            else:
                                # 存在しない場合は文字列として保持（互換性のため）
                                equipment_types.append(eq_name)
                        except:
                            equipment_types.append(eq_name)
                    
                    # 更新されたTestItemを作成
                    updated_item = TestItem(
                        id=item.id,
                        test_block=st.session_state[f"edit_block_{i}"],
                        category=test_category,
                        condition=TestCondition(
                            condition_text=st.session_state[f"edit_condition_{i}"],
                            equipment_types=equipment_types
                        ),
                        created_at=item.created_at,
                        updated_at=datetime.now()
                    )
                    
                    st.session_state.test_items[original_idx] = updated_item
                
                st.session_state.show_edit_form = False
                st.session_state.edit_items = []
                st.success("✅ 検証項目を更新しました")
                st.rerun()
        
        with col2:
            if st.button("キャンセル"):
                st.session_state.show_edit_form = False
                st.session_state.edit_items = []
                st.rerun()

def render_validation_execution(selected_provider=None):
    """検証実行UI"""
    st.header("検証実行")
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>作成した検証項目をAIエージェントで自動実行し、リアルタイムで結果を確認できます</p>", unsafe_allow_html=True)
    
    if not st.session_state.test_items:
        st.warning("検証項目がありません。まず検証項目を作成してください。")
        return
    
    # バッチ選択・設定
    st.subheader("バッチ選択")
    
    # 既存バッチ選択
    saved_batches = st.session_state.get('saved_batches', [])
    if saved_batches:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_batch = st.selectbox(
                "既存バッチから選択",
                options=["新規バッチ"] + [f"{batch['name']} ({batch['created_at']})" for batch in saved_batches],
                help="過去に作成したバッチを選択して実行できます"
            )
        
        with col2:
            if st.button("バッチ読み込み") and selected_batch != "新規バッチ":
                # 選択されたバッチを読み込み
                batch_index = int(selected_batch.split(" (")[0].split("_")[-1]) if "_" in selected_batch else 0
                if batch_index < len(saved_batches):
                    selected_batch_data = saved_batches[batch_index]
                    st.session_state.test_items = selected_batch_data['test_items']
                    st.session_state.current_batch_name = selected_batch_data['name']
                    st.success(f"バッチ '{selected_batch_data['name']}' を読み込みました")
                    st.rerun()
    
    # バッチ名設定
    col1, col2 = st.columns(2)
    
    with col1:
        batch_name = st.text_input(
            "バッチ名",
            value=f"検証バッチ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    with col2:
        # サイドバーで選択されたプロバイダーを使用
        if selected_provider:
            llm_provider = selected_provider
        else:
            st.warning("サイドバーでプロバイダーを選択してください")
            return
    
    # 実行対象の選択
    st.subheader("実行対象")
    
    if st.session_state.test_items:
        # 表形式で検証項目を表示し、チェックボックスで選択
        selection_data = []
        for i, item in enumerate(st.session_state.test_items):
            selection_data.append({
                "選択": True,  # デフォルトで選択状態
                "試験ブロック": item.test_block,
                "カテゴリ": item.category.value if hasattr(item.category, 'value') else str(item.category),
                "検証条件": item.condition.condition_text,
                "対象設備": ", ".join([eq.value if hasattr(eq, 'value') else str(eq) for eq in item.condition.equipment_types]),
                "インデックス": i
            })
        
        # データフレームを作成
        import pandas as pd
        df = pd.DataFrame(selection_data)
        
        # チェックボックス付きの表を表示
        edited_df = st.data_editor(
            df.drop('インデックス', axis=1),
            column_config={
                "選択": st.column_config.CheckboxColumn(
                    "選択",
                    help="実行する検証項目を選択してください",
                    default=True,
                )
            },
            disabled=["試験ブロック", "カテゴリ", "検証条件", "対象設備"],
            hide_index=True,
            width="stretch"
        )
        
        # 選択された項目を取得
        selected_items = []
        for i, row in edited_df.iterrows():
            if row["選択"]:
                selected_items.append(st.session_state.test_items[i])
        
        st.info(f"選択された項目: {len(selected_items)}件")
    else:
        st.warning("検証項目がありません")
        selected_items = []
    
    if st.button("検証開始", type="primary"):
        if selected_items:
            execute_validation_batch(selected_items, batch_name, llm_provider)
        else:
            st.warning("実行する検証項目を選択してください")

def execute_validation_batch(test_items: List[TestItem], batch_name: str, llm_provider: str):
    """検証バッチを実行"""
    # 統合検証エンジン初期化（MCP対応）
    validation_engine = get_unified_validation_engine(llm_provider)
    
    # バッチ作成
    batch = validation_engine.create_batch_from_test_items(test_items, batch_name)
    
    # 実行方式の表示
    execution_method = validation_engine.get_execution_method()
    capabilities = validation_engine.get_capabilities()
    
    if capabilities["mcp_supported"]:
        st.success("AIエージェントが自律的に検証を実行します")
    else:
        st.info("Pythonスクリプトベースで検証を実行、LLMが結果を評価します")
    
    # 実行時間計測
    start_time = time.time()
    
    # 進捗表示用コンテナ
    progress_bar = st.progress(0)
    spinner_placeholder = st.empty()
    thinking_container = st.empty()
    results_container = st.empty()
    
    # 検証実行の思考段階を定義
    if capabilities["mcp_supported"]:
        # MCPエージェントの思考段階
        thinking_stages = [
            "検証バッチの構成を分析中...",
            "MCPツールを準備中...",
            "設備との通信を確立中...",
            "検証項目を順次実行中...",
            "検証結果を分析中...",
            "最終レポートを作成中..."
        ]
    else:
        # 従来エンジンのステップ表示
        thinking_stages = [
            "検証バッチの構成を分析中...",
            "モック設備との接続を確立中...",
            "検証項目を順次実行中...",
            "LLMで結果を分析中...",
            "検証レポートを作成中..."
        ]
    
    current_stage = 0
    
    def progress_callback(progress: float, result_or_message):
        """進捗コールバック"""
        nonlocal current_stage
        
        # プログレス値の範囲チェック
        if progress > 1.0:
            progress = 1.0
        elif progress < 0.0:
            progress = 0.0
        
        # プログレスバー更新
        progress_bar.progress(progress)
        
        # スピナー表示（実行中... xx%済み）
        with spinner_placeholder:
            with st.spinner(f"実行中... {progress*100:.1f}%済み"):
                pass
        
        # 進捗に応じて思考段階を更新
        stage_index = min(int(progress * len(thinking_stages)), len(thinking_stages) - 1)
        if stage_index != current_stage:
            current_stage = stage_index
        
        current_thinking = thinking_stages[current_stage]
        if capabilities["mcp_supported"]:
            thinking_container.info(f"💭 {current_thinking}")
        else:
            thinking_container.info(f"🔄 {current_thinking}")
        
        # 検証結果をリアルタイム表示
        if hasattr(result_or_message, 'result'):
            if batch.results:
                with results_container.container():
                    render_realtime_results(batch.results)
    
    try:
        # デバッグ情報
        logger.info(f"Batch created: {batch.id}, name: {batch.name}")
        logger.info(f"Test items count: {len(batch.test_items)}")
        
        # バッチ実行
        completed_batch = validation_engine.execute_batch(batch, progress_callback)
        
        execution_time = time.time() - start_time
        
        # 完了表示
        progress_bar.progress(1.0)
        spinner_placeholder.empty()
        if capabilities["mcp_supported"]:
            thinking_container.success("💭 検証実行完了")
        else:
            thinking_container.success("🔄 検証実行完了")
        st.success(f"✅ 完了! 実行時間: {execution_time:.1f}秒")
        
        # セッション状態に保存
        st.session_state.current_batch = completed_batch
        st.session_state.validation_results = completed_batch.results
        
        # 最終結果表示
        if completed_batch.results:
            with results_container.container():
                render_realtime_results(completed_batch.results)
        
        # 結果サマリー表示
        render_batch_summary(completed_batch)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # エラー時の表示更新
        progress_bar.progress(0.0)
        spinner_placeholder.empty()
        thinking_container.error("❌ 検証実行に失敗しました")
        
        st.error(f"❌ 検証実行に失敗しました: {str(e)}")
        st.code(error_details)
        logger.error(f"Validation execution failed: {e}")
        logger.error(f"Full traceback: {error_details}")

def render_realtime_results(results: List[ValidationResult]):
    """リアルタイム結果表示"""
    st.subheader("検証結果一覧")
    
    # データフレーム作成
    data = []
    for i, result in enumerate(results):
        # 判定根拠を取得
        details = ""
        if hasattr(result, 'details') and result.details:
            details = result.details
        elif hasattr(result, 'error_message') and result.error_message:
            details = f"エラー: {result.error_message}"
        else:
            details = "詳細情報なし"
        
        # 検証条件を取得（test_item_idから逆引き）
        condition_text = "検証条件情報なし"
        if hasattr(result, 'test_item_id') and result.test_item_id:
            # セッション状態から該当するtest_itemを検索
            test_items = st.session_state.get('test_items', [])
            for item in test_items:
                if item.id == result.test_item_id:
                    condition_text = item.condition.condition_text
                    break
        
        # 辞書とオブジェクトの両方に対応
        if isinstance(result, dict):
            equipment_type = result.get('equipment_type', 'Unknown')
            result_value = result.get('result', 'Unknown')
            confidence = result.get('confidence', 0.0)
            execution_time = result.get('execution_time', 0.0)
        else:
            equipment_type = result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type)
            result_value = result.result.value if hasattr(result.result, 'value') else str(result.result)
            confidence = result.confidence
            execution_time = result.execution_time
        
        # 結果を日本語化
        result_map = {
            "PASS": "合格",
            "FAIL": "不合格", 
            "NEEDS_CHECK": "要確認",
            "WARNING": "警告"
        }
        result_value = result_map.get(result_value, result_value)
        
        data.append({
            "検証条件": condition_text,
            "対象設備": equipment_type,
            "結果": result_value,
            "判定根拠": details,
            "信頼度": f"{confidence:.2f}",
            "実行時間": f"{execution_time:.2f}s"
        })
    
    if data:
        df = pd.DataFrame(data)
        
        # 結果に応じて色分け
        def color_result(val):
            if val == "PASS" or val == "合格":
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif val == "FAIL" or val == "不合格":
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            elif val == "NEEDS_CHECK" or val == "要確認":
                return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            return ""
        
        # スタイル適用
        styled_df = df.style.map(color_result, subset=['結果'])
        
        # 判定根拠列の幅を調整
        st.dataframe(
            styled_df,
            column_config={
                "判定根拠": st.column_config.TextColumn(
                    "判定根拠",
                    width="large",
                    help="AIによる判定の根拠と詳細"
                )
            },
            width="stretch",
            hide_index=True
        )
    else:
        st.info("検証結果がありません")

def render_batch_summary(batch: ValidationBatch):
    """バッチサマリーを表示"""
    st.subheader("実行結果サマリー")
    
    # バッチから直接サマリーを計算
    if not batch.results:
        summary = {
            "total_tests": 0,
            "completed_tests": 0,
            "pass_count": 0,
            "fail_count": 0,
            "warning_count": 0,
            "success_rate": 0.0,
            "average_execution_time": 0.0,
            "status": batch.status.value if hasattr(batch.status, 'value') else str(batch.status)
        }
    else:
        total_tests = len(batch.results)
        pass_count = sum(1 for r in batch.results if r.result == TestResult.PASS)
        fail_count = sum(1 for r in batch.results if r.result == TestResult.FAIL)
        warning_count = sum(1 for r in batch.results if r.result == TestResult.NEEDS_CHECK)
        
        success_rate = pass_count / total_tests if total_tests > 0 else 0.0
        avg_execution_time = sum(r.execution_time for r in batch.results) / total_tests if total_tests > 0 else 0.0
        
        summary = {
            "total_tests": total_tests,
            "completed_tests": total_tests,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "warning_count": warning_count,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "status": batch.status if isinstance(batch.status, str) else (batch.status.value if hasattr(batch.status, 'value') else str(batch.status))
        }
    
    # メトリクス表示（文字サイズを大きく）
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="text-align: center; padding: 16px; background: white; border-radius: 8px; border: 1px solid #ddd;">
            <div style="font-size: 24px; font-weight: 600; color: #333; margin-bottom: 8px;">総テスト数</div>
            <div style="font-size: 42px; font-weight: 700; color: #0052CC;">{summary['total_tests']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 16px; background: white; border-radius: 8px; border: 1px solid #ddd;">
            <div style="font-size: 24px; font-weight: 600; color: #333; margin-bottom: 8px;">成功数</div>
            <div style="font-size: 42px; font-weight: 700; color: #0052CC;">{summary['pass_count']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="text-align: center; padding: 16px; background: white; border-radius: 8px; border: 1px solid #ddd;">
            <div style="font-size: 24px; font-weight: 600; color: #333; margin-bottom: 8px;">平均実行時間</div>
            <div style="font-size: 42px; font-weight: 700; color: #0052CC;">{summary['average_execution_time']:.1f}秒</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # 日本時間で表示（JST = UTC+9）
        if batch.completed_at:
            # 9時間加算してJSTに変換
            from datetime import timedelta
            jst_time = batch.completed_at + timedelta(hours=9)
            time_str = jst_time.strftime("%H:%M:%S")
        else:
            time_str = "N/A"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 16px; background: white; border-radius: 8px; border: 1px solid #ddd;">
            <div style="font-size: 24px; font-weight: 600; color: #333; margin-bottom: 8px;">完了時刻（JST）</div>
            <div style="font-size: 42px; font-weight: 700; color: #0052CC;">{time_str}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # スペースを追加
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 詳細結果
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**<span style='font-size: 22px; color: #000000;'>検証結果分布</span>**", unsafe_allow_html=True)
        result_counts = {
            'PASS': summary['pass_count'],
            'FAIL': summary['fail_count'],
            'NEEDS_CHECK': summary['warning_count']
        }
        
        # データを日本語ラベルに変換
        result_data = {
            'Result': [],
            'Count': []
        }
        
        if result_counts['PASS'] > 0:
            result_data['Result'].append('成功')
            result_data['Count'].append(result_counts['PASS'])
        if result_counts['FAIL'] > 0:
            result_data['Result'].append('失敗')
            result_data['Count'].append(result_counts['FAIL'])
        if result_counts['NEEDS_CHECK'] > 0:
            result_data['Result'].append('要確認')
            result_data['Count'].append(result_counts['NEEDS_CHECK'])
        
        if result_data['Count']:
            fig = px.pie(
                result_data, 
                values='Count', 
                names='Result',
                color_discrete_map={
                    '成功': '#28a745',  # 緑
                    '失敗': '#dc3545',  # 赤
                    '要確認': '#fd7e14', # オレンジ
                    '実行中': '#007bff'  # 青
                }
            )
            # ダッシュボードと完全に同じスタイル
            fig.update_traces(
                textfont_size=16, 
                textposition='inside',
                textinfo='label+percent'
            )
            fig.update_layout(
                font=dict(size=16),
                showlegend=True,
                legend=dict(
                    font=dict(size=16),
                    orientation="v",
                    yanchor="middle",
                    y=0.5
                ),
                margin=dict(t=50, b=50, l=50, r=50)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("表示するデータがありません")
    
    with col2:
        st.markdown("**<span style='font-size: 22px; color: #000000;'>設備別成功率</span>**", unsafe_allow_html=True)
        
        # 設備別統計を直接計算
        equipment_stats = {}
        for result in batch.results:
            eq_type = result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type)
            if eq_type not in equipment_stats:
                equipment_stats[eq_type] = {'total': 0, 'passed': 0}
            
            equipment_stats[eq_type]['total'] += 1
            if result.result.value == 'PASS':
                equipment_stats[eq_type]['passed'] += 1
        
        eq_data = []
        for eq_type, stats in equipment_stats.items():
            success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            eq_data.append({
                'Equipment': eq_type,
                'Success Rate': success_rate,
                'Total Tests': stats['total']
            })
        
        if eq_data:
            eq_df = pd.DataFrame(eq_data)
            fig = px.bar(
                eq_df,
                x='Equipment',
                y='Success Rate',
                color='Success Rate',
                color_continuous_scale=[[0, '#dc3545'], [1, '#007bff']],  # 0%赤から100%青のグラデーション
                range_color=[0, 100]  # 色スケールを0-100に固定
            )
            fig.update_layout(
                showlegend=False,
                font=dict(size=14),
                xaxis=dict(
                    tickfont=dict(size=12),
                    title_font=dict(size=14)
                ),
                yaxis=dict(
                    range=[0, 100],  # 縦軸を0-100に固定
                    tickfont=dict(size=12),
                    title_font=dict(size=14)
                ),
                margin=dict(t=50, b=50, l=50, r=50)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("設備別データがありません")

def render_results_viewer():
    """結果表示"""
    st.header("検証結果表示")
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>実行済み検証の詳細結果を確認・分析し、設備別や結果別のフィルタリングが可能です</p>", unsafe_allow_html=True)
    
    # バッチ選択
    st.subheader("検証バッチ選択")
    
    # 実行済みバッチ一覧（セッション状態から取得）
    executed_batches = st.session_state.get('executed_batches', [])
    current_batch = st.session_state.get('current_batch')
    
    # デバッグ情報
    st.info(f"セッション状態の実行済みバッチ数: {len(executed_batches)}")
    if current_batch:
        st.info(f"現在のバッチ: {current_batch.name} (結果数: {len(current_batch.results) if current_batch.results else 0})")
    
    # 実行済みバッチリストを作成（current_batchの重複を避ける）
    batch_list = []
    
    # 既存の実行済みバッチを追加
    for batch in executed_batches:
        batch_list.append(batch)
    
    # 現在のバッチを追加（重複チェック）
    if current_batch and current_batch.results:  # 結果がある場合のみ
        # 重複チェック
        existing_ids = [b.get('id') for b in batch_list]
        if current_batch.id not in existing_ids:
            batch_list.append({
                'name': current_batch.name,
                'id': current_batch.id,
                'completed_at': current_batch.completed_at.strftime("%Y/%m/%d %H:%M:%S") if current_batch.completed_at else "実行中",
                'results': current_batch.results
            })
    
    if not batch_list:
        st.warning("実行済み検証バッチがありません。")
        st.markdown("**検証を実行する手順:**")
        st.markdown("1. 左側メニューで「検証手動実行」を選択")
        st.markdown("2. 「検証項目入力」で検証項目を作成")
        st.markdown("3. 「検証実行」でバッチを実行")
        st.markdown("4. 実行完了後にこのページで結果を確認")
        return
    
    # バッチ選択
    batch_options = [f"{batch['name']} ({batch['completed_at']})" for batch in batch_list]
    selected_batch_name = st.selectbox(
        "表示するバッチを選択",
        options=batch_options,
        help="表示したい検証バッチを選択してください"
    )
    
    # 選択されたバッチの結果を取得
    selected_batch_index = batch_options.index(selected_batch_name)
    selected_batch = batch_list[selected_batch_index]
    validation_results = selected_batch['results']
    
    if not validation_results:
        st.info("選択されたバッチに検証結果がありません。")
        return
    
    # フィルター
    col1, col2 = st.columns(2)
    
    with col1:
        equipment_filter = st.multiselect(
            "設備フィルター",
            options=[eq.value for eq in EquipmentType],
            default=[]  # デフォルトはフィルターなし
        )
    
    with col2:
        result_filter = st.multiselect(
            "結果フィルター",
            options=[result.value for result in TestResult],
            default=[]  # デフォルトはフィルターなし
        )
    
    # 結果をフィルタリング（フィルターが空の場合は全て表示）
    filtered_results = []
    for result in validation_results:
        # 設備フィルター
        if equipment_filter and result.equipment_type.value not in equipment_filter:
            continue
        # 結果フィルター
        if result_filter and result.result.value not in result_filter:
            continue
        filtered_results.append(result)
    
    # 表示オプション（左寄せ横並び）
    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        show_star_chart = st.checkbox("星取表を表示", value=True)
    with col2:
        show_details = st.checkbox("詳細を表示", value=False)
    
    if show_star_chart:
        render_star_chart(filtered_results)
    
    # 詳細テーブル表示
    if show_details:
        render_detailed_results_table(filtered_results)


def render_star_chart(results: List[ValidationResult]):
    """星取表を表示"""
    st.subheader("星取表")
    
    try:
        df = create_star_chart_dataframe(results)
        
        # スタイル適用（設備列に対して）
        def style_star_chart(val):
            if val == "●":
                return "background-color: #d4edda; color: #155724; font-weight: bold;"
            elif val == "×":
                return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
            elif val == "△":
                return "background-color: #fff3cd; color: #856404; font-weight: bold;"
            return ""
        
        # 設備列のみにスタイルを適用（検証条件、メッセージは除外）
        equipment_columns = [col for col in df.columns if col not in ["メッセージ", "検証条件"]]
        if equipment_columns:
            styled_df = df.style.applymap(style_star_chart, subset=equipment_columns)
        else:
            styled_df = df.style
        
        # 列幅の設定
        column_config = {}
        for col in df.columns:
            if col == "検証条件":
                column_config[col] = st.column_config.TextColumn(
                    "検証条件",
                    width="large"
                )
            elif col not in ["メッセージ"]:
                column_config[col] = st.column_config.Column(
                    col,
                    width="medium"
                )
        
        st.dataframe(
            styled_df, 
            use_container_width=True, 
            hide_index=False,
            column_config=column_config
        )
        
    except Exception as e:
        st.error(f"星取表の生成に失敗しました: {str(e)}")
        logger.error(f"Star chart generation failed: {e}")

def render_detailed_results_table(results: List[ValidationResult]):
    """詳細結果テーブルを表示"""
    st.subheader("詳細結果")
    
    # データフレーム作成
    data = []
    for i, result in enumerate(results):
        # 検証条件を取得 - バッチデータから直接取得
        condition_text = "検証条件情報なし"
        if isinstance(result, dict):
            # 辞書形式の場合、test_idから条件を推定
            condition_text = result.get('condition_text', "検証条件情報なし")
            if condition_text == "検証条件情報なし":
                # 判定根拠から条件を推定
                details = result.get('details', '')
                if '測定値:' in details and '閾値:' in details:
                    condition_text = f"測定条件（詳細は判定根拠を参照）"
        elif hasattr(result, 'test_item_id') and result.test_item_id:
            # オブジェクト形式の場合、セッションから検索
            test_items = st.session_state.get('test_items', [])
            for item in test_items:
                if item.id == result.test_item_id:
                    condition_text = item.condition.condition_text
                    break
        
        # 判定根拠を取得
        details = ""
        if hasattr(result, 'details') and result.details:
            details = result.details
        elif hasattr(result, 'error_message') and result.error_message:
            details = f"エラー: {result.error_message}"
        else:
            details = "詳細情報なし"
        
        # 辞書とオブジェクトの両方に対応
        if isinstance(result, dict):
            equipment_type = result.get('equipment_type', 'Unknown')
            result_value = result.get('result', 'Unknown')
            confidence = result.get('confidence', 0.0)
            execution_time = result.get('execution_time', 0.0)
            created_at = result.get('created_at', 'Unknown')
            if created_at != 'Unknown':
                try:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at_str = created_at.strftime("%H:%M:%S")
                except:
                    created_at_str = str(created_at)
            else:
                created_at_str = "Unknown"
        else:
            equipment_type = result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type)
            result_value = result.result.value if hasattr(result.result, 'value') else str(result.result)
            confidence = result.confidence
            execution_time = result.execution_time
            created_at_str = result.created_at.strftime("%H:%M:%S")
        
        # 結果を日本語化
        result_map = {
            "PASS": "合格",
            "FAIL": "不合格", 
            "NEEDS_CHECK": "要確認",
            "WARNING": "警告"
        }
        result_value = result_map.get(result_value, result_value)
        
        data.append({
            "検証条件": condition_text,
            "対象設備": equipment_type,
            "結果": result_value,
            "判定根拠": details,
            "信頼度": f"{confidence:.2f}",
            "実行時間": f"{execution_time:.2f}s",
            "実行時刻": created_at_str
        })
    
    df = pd.DataFrame(data)
    
    # 結果に応じて色分け
    def color_result(val):
        if val == "PASS" or val == "合格":
            return "background-color: #d4edda"
        elif val == "FAIL" or val == "不合格":
            return "background-color: #f8d7da"
        elif val == "NEEDS_CHECK" or val == "要確認":
            return "background-color: #fff3cd"
        elif val == "WARNING":
            return "background-color: #fff3cd"
        return ""
    
    styled_df = df.style.applymap(color_result, subset=['結果'])
    st.dataframe(styled_df, use_container_width=True)

def render_batch_list():
    """検証バッチ一覧を表示"""
    st.header("検証バッチ一覧")
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>実行済み検証バッチの履歴を確認し、詳細結果を表示できます</p>", unsafe_allow_html=True)
    
    # リアルなデータを読み込み
    realistic_batches = load_realistic_batches()
    
    # セッション状態のバッチも追加
    executed_batches = st.session_state.get('executed_batches', [])
    current_batch = st.session_state.get('current_batch')
    
    if current_batch:
        # 重複チェック
        existing_ids = [batch.get('id') for batch in executed_batches]
        if current_batch.id not in existing_ids:
            executed_batches.append({
                'name': current_batch.name,
                'id': current_batch.id,
                'completed_at': current_batch.completed_at.strftime("%Y/%m/%d %H:%M:%S") if current_batch.completed_at else "実行中",
                'results': current_batch.results,
                'status': current_batch.status if isinstance(current_batch.status, str) else current_batch.status.value,
                'test_count': len(current_batch.test_items)
            })
            # セッション状態を更新
            st.session_state.executed_batches = executed_batches
    
    # リアルなデータと結合
    all_batches = []
    for batch in realistic_batches:
        all_batches.append({
            'name': batch.get('name', 'Unknown'),
            'id': batch.get('id', 'Unknown'),
            'completed_at': batch.get('completed_at', batch.get('created_at', 'Unknown')),
            'results': batch.get('results', []),
            'status': batch.get('status', 'completed'),
            'test_count': len(batch.get('test_items', []))
        })
    
    # セッション状態のバッチも追加
    all_batches.extend(executed_batches)
    
    if not all_batches:
        st.info("検証バッチがありません。")
        return
    
    # フィルター
    col1, col2 = st.columns(2)
    
    with col1:
        date_filter = st.date_input("実行日フィルター", value=None)
    
    with col2:
        status_filter = st.multiselect(
            "ステータスフィルター",
            options=["COMPLETED", "RUNNING", "FAILED"],
            default=[]  # デフォルトはフィルターなし
        )
    
    # バッチ一覧表示
    st.subheader("バッチ一覧")
    
    # データフレーム作成
    batch_data = []
    for batch in all_batches:
        # ステータスのデフォルト値設定
        batch_status = batch.get('status', 'COMPLETED')
        
        # フィルター適用
        if status_filter and batch_status not in status_filter:
            continue
        
        if date_filter:
            try:
                batch_date = datetime.strptime(batch['completed_at'].split(' ')[0], "%Y/%m/%d").date()
                if batch_date != date_filter:
                    continue
            except:
                continue
        
        # 成功率計算
        if batch.get('results'):
            success_count = 0
            for r in batch['results']:
                # 辞書とオブジェクトの両方に対応
                if isinstance(r, dict):
                    result_value = r.get('result')
                else:
                    result_value = getattr(r, 'result', None)
                    if hasattr(result_value, 'value'):
                        result_value = result_value.value
                
                if result_value == 'PASS':
                    success_count += 1
            
            success_rate = f"{success_count / len(batch['results']) * 100:.1f}%"
        else:
            success_rate = "N/A"
        
        batch_data.append({
            "選択": False,
            "バッチ名": batch['name'],
            "実行時刻": batch['completed_at'],
            "ステータス": batch_status,
            "テスト数": batch.get('test_count', 0),
            "成功率": success_rate,
            "ID": batch.get('id', batch['name'])
        })
    
    if not batch_data:
        st.info("フィルター条件に一致するバッチがありません。")
        return
    
    df = pd.DataFrame(batch_data)
    
    # チェックボックス付きの表を表示
    edited_df = st.data_editor(
        df.drop('ID', axis=1),
        column_config={
            "選択": st.column_config.CheckboxColumn(
                "選択",
                help="詳細を表示するバッチを選択してください",
                default=False,
            )
        },
        disabled=["バッチ名", "実行時刻", "ステータス", "テスト数", "成功率"],
        hide_index=True,
        width="stretch"
    )
    
    # 選択されたバッチの詳細表示
    selected_batches = []
    for i, row in edited_df.iterrows():
        if row["選択"]:
            batch_id = df.iloc[i]["ID"]
            selected_batch = next((b for b in all_batches if b.get('id') == batch_id or b.get('name') == batch_id), None)
            if selected_batch:
                selected_batches.append(selected_batch)
    
    if selected_batches:
        st.subheader("選択されたバッチの詳細")
        
        for batch in selected_batches:
            with st.expander(f"{batch['name']}", expanded=True):
                if batch['results']:
                    # バッチサマリー
                    col1, col2, col3, col4 = st.columns(4)
                    
                    total_tests = len(batch['results'])
                    pass_count = 0
                    fail_count = 0
                    
                    for r in batch['results']:
                        # 辞書とオブジェクトの両方に対応
                        if isinstance(r, dict):
                            result_value = r.get('result')
                        else:
                            result_value = getattr(r, 'result', None)
                            if hasattr(result_value, 'value'):
                                result_value = result_value.value
                        
                        if result_value == 'PASS':
                            pass_count += 1
                        elif result_value == 'FAIL':
                            fail_count += 1
                    
                    with col1:
                        st.metric("総テスト数", total_tests)
                    with col2:
                        st.metric("成功", pass_count)
                    with col3:
                        st.metric("失敗", fail_count)
                    with col4:
                        success_rate = f"{(pass_count / total_tests * 100):.1f}%" if total_tests > 0 else "0%"
                        st.metric("成功率", success_rate)
                    
                    # 詳細結果テーブル
                    render_detailed_results_table(batch['results'])
                else:
                    st.info("このバッチには結果がありません。")

def main():
    """メインアプリケーション"""
    # 初期化
    initialize_app()
    
    # ヘッダー
    render_header()
    
    # サイドバー
    with st.sidebar:
        st.title("メニュー")
        
        main_menu = st.radio(
            "メインメニュー",
            ["ダッシュボード", "検証手動実行"],
            index=0
        )
        
        # サブメニュー
        if main_menu == "ダッシュボード":
            sub_page = st.radio(
                "ダッシュボード",
                ["検証サマリ", "検証レビュー", "検証バッチ一覧", "AI質疑応答"],
                index=0
            )
        else:  # 検証手動実行
            sub_page = st.radio(
                "検証手動実行",
                ["検証項目入力", "検証実行", "検証結果"],
                index=0
            )
        
        st.divider()
        
        # LLMプロバイダー選択
        st.subheader("LLMプロバイダー")
        provider_manager = get_provider_manager()
        available_providers = provider_manager.get_available_providers()
        all_providers = provider_manager.get_all_providers()
        
        if available_providers:
            # 利用可能なプロバイダーのみ表示
            provider_options = []
            provider_labels = []
            
            for provider in available_providers:
                provider_options.append(provider.name)
                provider_labels.append(provider.display_name)
            
            # デフォルトプロバイダーを選択
            default_provider = provider_manager.get_default_provider()
            default_index = 0
            if default_provider in provider_options:
                default_index = provider_options.index(default_provider)
            
            selected_provider = st.selectbox(
                "プロバイダーを選択",
                options=provider_options,
                format_func=lambda x: next(label for opt, label in zip(provider_options, provider_labels) if opt == x),
                index=default_index,
                key="selected_provider"
            )
            
            # 選択されたプロバイダーの詳細表示
            selected_info = provider_manager.get_provider_info(selected_provider)
            if selected_info:
                if selected_info.is_mcp_supported:
                    st.success("AIエージェント実行")
                    st.caption("自律的にコマンドを判断・実行")
                else:
                    st.info("スクリプト実行")
                    st.caption("事前定義されたロジックで実行")
                
                st.caption(f"モデル: {selected_info.model_name}")
        else:
            st.error("利用可能なプロバイダーがありません")
            selected_provider = None
        
        # 利用不可プロバイダーの表示
        unavailable_providers = [p for p in all_providers.values() if p.status != ProviderStatus.AVAILABLE]
        if unavailable_providers:
            with st.expander("利用不可プロバイダー", expanded=False):
                for provider in unavailable_providers:
                    status_icon = "❌" if provider.status == ProviderStatus.UNAVAILABLE else "⚠️"
                    st.text(f"{status_icon} {provider.display_name}")
                    if provider.error_message:
                        st.caption(f"理由: {provider.error_message}")
        
        st.divider()
        
        # Embedding情報
        st.subheader("Embedding設定")
        embedding_provider, embedding_model = provider_manager.get_embedding_provider()
        st.info(f"プロバイダー: {embedding_provider}")
        st.caption(f"モデル: {embedding_model}")
        st.caption("※RAG・ベクターDB用")
        
        st.divider()
        
        # システム情報
        st.subheader("システム情報")
        st.info(f"バージョン: {APP_VERSION}")
        
        # モック設備ステータス
        st.subheader("設備ステータス")
        # 新しい設備名での表示
        mock_equipment_list = [
            "高輪ゲートウェイシティ_Ericsson",
            "高輪ゲートウェイシティ_Nokia", 
            "大岡山ラボ_Samsung"
        ]
        for eq_type in mock_equipment_list:
            status_icon = "🟢"  # デモ用に全てアクティブ
            st.text(f"{status_icon} {eq_type}")
    
    # メインコンテンツ
    if main_menu == "ダッシュボード":
        if sub_page == "検証サマリ":
            render_dashboard()
        elif sub_page == "検証レビュー":
            render_review_panel()
        elif sub_page == "検証バッチ一覧":
            render_batch_list()
        elif sub_page == "AI質疑応答":
            render_qa_panel()
    else:  # 検証手動実行
        if sub_page == "検証項目入力":
            render_test_management(selected_provider)
        elif sub_page == "検証実行":
            render_validation_execution(selected_provider)
        elif sub_page == "検証結果":
            render_results_viewer()

if __name__ == "__main__":
    main()
