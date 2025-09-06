"""
Excelファイル解析ユーティリティ
Excel File Parser Utility
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import uuid
from typing import List, Dict, Any
from datetime import datetime
import logging

from app.models.validation import TestItem, TestCondition, TestCategory, EquipmentType

logger = logging.getLogger(__name__)

def parse_excel_test_items(uploaded_file) -> List[TestItem]:
    """
    アップロードされたExcelファイルから検証項目を解析
    
    Args:
        uploaded_file: Streamlitのアップロードファイル
        
    Returns:
        List[TestItem]: 解析された検証項目のリスト
    """
    try:
        # Excelファイルを読み込み
        df = pd.read_excel(uploaded_file, sheet_name=0)  # 最初のシートを使用
        
        logger.info(f"Excel file loaded: {df.shape}")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        test_items = []
        
        # 参考ファイルの形式に基づいて解析
        # 列: #, 試験ブロック, 項目, 条件, COUNT, 各設備のシナリオ...
        
        for index, row in df.iterrows():
            try:
                # 基本情報を取得
                test_number = row.get('#', index + 1)
                test_block = row.get('試験ブロック', f'ブロック{test_number}')
                category_name = row.get('項目', 'CMデータの取得')
                condition_text = row.get('条件', '')
                expected_count = row.get('COUNT', 0)
                
                # NaN値の処理
                if pd.isna(test_block):
                    test_block = f'ブロック{test_number}'
                if pd.isna(category_name):
                    category_name = 'CMデータの取得'
                if pd.isna(condition_text):
                    condition_text = f'検証項目{test_number}'
                if pd.isna(expected_count):
                    expected_count = 0
                
                # カテゴリをマッピング
                category = map_category_name(category_name)
                
                # 設備タイプとシナリオを抽出
                equipment_types, scenarios = extract_equipment_and_scenarios(row, df.columns)
                
                # TestItemオブジェクトを作成
                test_item = TestItem(
                    id=str(uuid.uuid4()),
                    test_block=str(test_block),
                    category=category,
                    condition=TestCondition(
                        condition_text=str(condition_text),
                        expected_count=int(expected_count) if isinstance(expected_count, (int, float)) else 0,
                        equipment_types=equipment_types
                    ),
                    scenarios=scenarios
                )
                
                test_items.append(test_item)
                
            except Exception as e:
                logger.warning(f"Failed to parse row {index}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(test_items)} test items")
        return test_items
        
    except Exception as e:
        logger.error(f"Failed to parse Excel file: {e}")
        raise Exception(f"Excelファイルの解析に失敗しました: {str(e)}")

def map_category_name(category_name: str) -> TestCategory:
    """
    カテゴリ名をTestCategoryにマッピング
    
    Args:
        category_name: カテゴリ名
        
    Returns:
        TestCategory: マッピングされたカテゴリ
    """
    category_mapping = {
        'CMデータの取得': TestCategory.CM_DATA_ACQUISITION,
        'インドア対策局のフィルタ': TestCategory.INDOOR_FILTER,
        '対策バンドによるフィルタ': TestCategory.BAND_FILTER,
        'ESG作成': TestCategory.ESG_CREATION,
        'ESG選定': TestCategory.ESG_SELECTION,
        'ホワイトリスト局のフィルタ': TestCategory.WHITELIST_FILTER,
        'ブラックリスト局のフィルタ': TestCategory.BLACKLIST_FILTER,
        '作業データのフィルタ': TestCategory.WORK_DATA_FILTER
    }
    
    # 部分一致でマッピング
    for key, value in category_mapping.items():
        if key in str(category_name):
            return value
    
    # デフォルト
    return TestCategory.CM_DATA_ACQUISITION

def extract_equipment_and_scenarios(row: pd.Series, columns: pd.Index) -> tuple[List[EquipmentType], List[str]]:
    """
    行から設備タイプとシナリオを抽出
    
    Args:
        row: データ行
        columns: 列名のインデックス
        
    Returns:
        tuple: (設備タイプのリスト, シナリオのリスト)
    """
    equipment_types = []
    scenarios = []
    
    # 設備関連の列を検索
    equipment_columns = [col for col in columns if any(eq in str(col) for eq in [
        'Ericsson-MMU', 'Ericsson-RRU', 'Samsung-AU', 'Samsng-AU'
    ])]
    
    for col in equipment_columns:
        col_str = str(col)
        value = row.get(col, None)
        
        # 値が存在し、NaNでない場合
        if pd.notna(value) and str(value).strip():
            # 設備タイプを特定
            equipment_type = None
            if 'Ericsson-MMU' in col_str:
                equipment_type = EquipmentType.ERICSSON_MMU
            elif 'Ericsson-RRU' in col_str:
                equipment_type = EquipmentType.ERICSSON_RRU
            elif 'Samsng-AUv1' in col_str or 'Samsung-AUv1' in col_str:
                equipment_type = EquipmentType.SAMSUNG_AUV1
            elif 'Samsng-AUv2' in col_str or 'Samsung-AUv2' in col_str:
                equipment_type = EquipmentType.SAMSUNG_AUV2
            
            if equipment_type:
                if equipment_type not in equipment_types:
                    equipment_types.append(equipment_type)
                
                # シナリオ名を生成
                scenario_name = extract_scenario_name(col_str)
                if scenario_name and scenario_name not in scenarios:
                    scenarios.append(scenario_name)
    
    # デフォルト値
    if not equipment_types:
        equipment_types = [EquipmentType.ERICSSON_MMU]
    
    if not scenarios:
        scenarios = ['正常動作']
    
    return equipment_types, scenarios

def extract_scenario_name(column_name: str) -> str:
    """
    列名からシナリオ名を抽出
    
    Args:
        column_name: 列名
        
    Returns:
        str: シナリオ名
    """
    col_str = str(column_name)
    
    # シナリオパターンを抽出
    if '正常スリープ' in col_str:
        return '正常スリープ'
    elif '不正なデータ' in col_str:
        return '不正なデータ'
    elif '異常' in col_str:
        return '異常系'
    elif '正常' in col_str:
        return '正常系'
    else:
        # 設備名を除いた部分をシナリオ名として使用
        parts = col_str.split('-')
        if len(parts) > 1:
            return parts[-1]
        return '標準動作'

def create_sample_excel_data() -> pd.DataFrame:
    """
    サンプルのExcelデータを作成（テスト用）
    
    Returns:
        pd.DataFrame: サンプルデータ
    """
    data = {
        '#': [1, 2, 3, 4, 5],
        '試験ブロック': ['ESG選定', None, None, None, None],
        '項目': ['CMデータの取得', 'CMデータの取得', 'CMデータの取得', 'CMデータの取得', 'CMデータの取得'],
        '条件': [
            '取得成功（Ericsson-MMU）',
            '取得成功（Ericsson-RRU）',
            '取得成功（Samsung）',
            '不正なデータあり（Ericsson-MMU）',
            '不正なデータあり（Samsung）'
        ],
        'COUNT': [1, 1, 2, 1, 2],
        'Ericsson-MMU正常スリープ': ['●', None, None, None, None],
        'Ericsson-RRU正常スリープ': [None, '●', None, None, None],
        'Samsung-AUv1正常スリープ': [None, None, '●', None, None],
        'Samsung-AUv2正常スリープ': [None, None, '●', None, None],
        'Ericsson-MMU不正なデータ': [None, None, None, '●', None],
        'Samsung-AUv1不正なデータ': [None, None, None, None, '●'],
        'Samsung-AUv2不正なデータ': [None, None, None, None, '●']
    }
    
    return pd.DataFrame(data)
