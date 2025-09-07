"""
星取表生成ユーティリティ
Star Chart Generation Utility
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from typing import List, Dict, Any
import logging

from app.models.validation import ValidationResult, TestResult

logger = logging.getLogger(__name__)

def create_star_chart_dataframe(results: List[ValidationResult]) -> pd.DataFrame:
    """
    検証結果から星取表のDataFrameを作成
    
    Args:
        results: 検証結果のリスト
        
    Returns:
        pd.DataFrame: 星取表形式のデータフレーム
    """
    if not results:
        return pd.DataFrame()
    
    try:
        # データを整理
        chart_data = {}
        
        # 行: 検証項目ID、列: 設備タイプ
        test_item_ids = sorted(list(set(result.test_item_id for result in results)))
        equipment_types = sorted(list(set(result.equipment_type.value for result in results)))
        
        # データフレームの初期化
        df_data = {}
        
        # 検証項目IDを行として設定（検証条件のみ）
        condition_texts = []
        
        for i, test_item_id in enumerate(test_item_ids):
            # 検証条件を取得
            condition_text = "検証条件不明"
            
            # セッション状態から検証条件を取得（Streamlitのグローバル状態を使用）
            try:
                import streamlit as st
                test_items = st.session_state.get('test_items', [])
                for item in test_items:
                    if item.id == test_item_id:
                        condition_text = item.condition.condition_text
                        break
            except:
                # セッション状態が利用できない場合はデフォルト
                pass
            
            condition_texts.append(condition_text)
        
        # 検証条件を設定
        df_data['検証条件'] = condition_texts
        
        # 各設備タイプを列として追加
        for equipment_type in equipment_types:
            column_data = []
            
            for test_item_id in test_item_ids:
                # 該当する結果を検索
                matching_result = None
                for result in results:
                    if result.test_item_id == test_item_id and result.equipment_type.value == equipment_type:
                        matching_result = result
                        break
                
                # 結果を記号に変換
                if matching_result:
                    symbol = convert_result_to_symbol(matching_result.result)
                else:
                    symbol = "-"  # 未実行
                
                column_data.append(symbol)
            
            df_data[equipment_type] = column_data
        
        # DataFrameを作成
        df = pd.DataFrame(df_data)
        
        logger.info(f"Star chart created: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Failed to create star chart: {e}")
        # エラー時は空のDataFrameを返す
        return pd.DataFrame()

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

def create_detailed_star_chart(results: List[ValidationResult]) -> pd.DataFrame:
    """
    詳細な星取表を作成（実行時間や信頼度も含む）
    
    Args:
        results: 検証結果のリスト
        
    Returns:
        pd.DataFrame: 詳細な星取表
    """
    if not results:
        return pd.DataFrame()
    
    try:
        # データを整理
        detailed_data = []
        
        for result in results:
            detailed_data.append({
                'シナリオ': result.scenario,
                '設備タイプ': result.equipment_type.value,
                '結果': convert_result_to_symbol(result.result),
                '実行時間(秒)': round(result.execution_time, 2),
                '信頼度': round(result.confidence, 2),
                'エラーメッセージ': result.error_message or "-",
                '実行時刻': result.created_at.strftime("%H:%M:%S")
            })
        
        df = pd.DataFrame(detailed_data)
        
        logger.info(f"Detailed star chart created: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Failed to create detailed star chart: {e}")
        return pd.DataFrame()

def create_summary_chart(results: List[ValidationResult]) -> Dict[str, Any]:
    """
    サマリーチャートを作成
    
    Args:
        results: 検証結果のリスト
        
    Returns:
        Dict[str, Any]: サマリー情報
    """
    if not results:
        return {}
    
    try:
        # 基本統計
        total_tests = len(results)
        pass_count = sum(1 for r in results if r.result == TestResult.PASS)
        fail_count = sum(1 for r in results if r.result == TestResult.FAIL)
        warning_count = sum(1 for r in results if r.result == TestResult.WARNING)
        
        # 設備別統計
        equipment_stats = {}
        for result in results:
            eq_type = result.equipment_type.value
            if eq_type not in equipment_stats:
                equipment_stats[eq_type] = {
                    'total': 0,
                    'pass': 0,
                    'fail': 0,
                    'warning': 0,
                    'avg_execution_time': 0.0,
                    'avg_confidence': 0.0
                }
            
            stats = equipment_stats[eq_type]
            stats['total'] += 1
            
            if result.result == TestResult.PASS:
                stats['pass'] += 1
            elif result.result == TestResult.FAIL:
                stats['fail'] += 1
            elif result.result == TestResult.WARNING:
                stats['warning'] += 1
            
            stats['avg_execution_time'] += result.execution_time
            stats['avg_confidence'] += result.confidence
        
        # 平均値を計算
        for eq_type, stats in equipment_stats.items():
            if stats['total'] > 0:
                stats['avg_execution_time'] /= stats['total']
                stats['avg_confidence'] /= stats['total']
                stats['success_rate'] = stats['pass'] / stats['total']
        
        # シナリオ別統計
        scenario_stats = {}
        for result in results:
            scenario = result.scenario
            if scenario not in scenario_stats:
                scenario_stats[scenario] = {
                    'total': 0,
                    'pass': 0,
                    'fail': 0,
                    'warning': 0
                }
            
            stats = scenario_stats[scenario]
            stats['total'] += 1
            
            if result.result == TestResult.PASS:
                stats['pass'] += 1
            elif result.result == TestResult.FAIL:
                stats['fail'] += 1
            elif result.result == TestResult.WARNING:
                stats['warning'] += 1
        
        # 成功率を計算
        for scenario, stats in scenario_stats.items():
            if stats['total'] > 0:
                stats['success_rate'] = stats['pass'] / stats['total']
        
        summary = {
            'overall': {
                'total_tests': total_tests,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'warning_count': warning_count,
                'success_rate': pass_count / total_tests if total_tests > 0 else 0.0,
                'average_execution_time': sum(r.execution_time for r in results) / total_tests,
                'average_confidence': sum(r.confidence for r in results) / total_tests
            },
            'equipment_stats': equipment_stats,
            'scenario_stats': scenario_stats
        }
        
        logger.info("Summary chart created successfully")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to create summary chart: {e}")
        return {}

def export_star_chart_to_excel(results: List[ValidationResult], filename: str = None) -> str:
    """
    星取表をExcelファイルにエクスポート
    
    Args:
        results: 検証結果のリスト
        filename: 出力ファイル名
        
    Returns:
        str: 出力ファイルパス
    """
    if not filename:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"star_chart_{timestamp}.xlsx"
    
    try:
        # 星取表を作成
        star_chart_df = create_star_chart_dataframe(results)
        detailed_df = create_detailed_star_chart(results)
        summary = create_summary_chart(results)
        
        # Excelファイルに書き込み
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 星取表シート
            star_chart_df.to_excel(writer, sheet_name='星取表')
            
            # 詳細結果シート
            detailed_df.to_excel(writer, sheet_name='詳細結果', index=False)
            
            # サマリーシート
            if summary:
                overall_df = pd.DataFrame([summary['overall']])
                overall_df.to_excel(writer, sheet_name='サマリー', index=False)
        
        logger.info(f"Star chart exported to: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Failed to export star chart: {e}")
        raise Exception(f"Excelエクスポートに失敗しました: {str(e)}")

def create_sample_star_chart() -> pd.DataFrame:
    """
    サンプルの星取表を作成（テスト用）
    
    Returns:
        pd.DataFrame: サンプル星取表
    """
    data = {
        'シナリオ': ['正常スリープ', '不正なデータ', '異常系テスト'],
        'Ericsson-MMU': ['●', '×', '△'],
        'Ericsson-RRU': ['●', '-', '×'],
        'Samsung-AUv1': ['●', '●', '●'],
        'Samsung-AUv2': ['●', '●', '●']
    }
    
    df = pd.DataFrame(data)
    df.set_index('シナリオ', inplace=True)
    
    return df
