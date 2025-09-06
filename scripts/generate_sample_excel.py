#!/usr/bin/env python3
"""
サンプルExcelファイル生成スクリプト
Generate Sample Excel File Script
"""
import pandas as pd
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_sample_excel():
    """サンプルExcelファイルを作成"""
    
    # サンプルデータ（基地局スリープ機能検証）
    data = {
        '#': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
        '試験ブロック': ['ESG選定'] + [None] * 21,
        '項目': [
            'CMデータの取得', 'CMデータの取得', 'CMデータの取得', 'CMデータの取得', 'CMデータの取得', 'CMデータの取得', 'CMデータの取得',
            'インドア対策局のフィルタ', 'インドア対策局のフィルタ', 'インドア対策局のフィルタ',
            '対策バンドによるフィルタ', '対策バンドによるフィルタ',
            'ESG作成', 'ESG作成', 'ESG作成',
            'ホワイトリスト局のフィルタ', 'ホワイトリスト局のフィルタ',
            'ブラックリスト局のフィルタ', 'ブラックリスト局のフィルタ',
            '作業データのフィルタ', '作業データのフィルタ', '作業データのフィルタ'
        ],
        '条件': [
            '取得成功（Ericsson-MMU）', '取得成功（Ericsson-RRU）', '取得成功（Samsung）',
            '不正なデータあり（Ericsson-MMU）', '不正なデータあり（Ericsson-RRU）', '不正なデータあり（Samsung）', '取得失敗',
            '取得成功', '取得成功（オープンデータなし）', '取得失敗',
            '対策バンドのCMデータあり', '対策バンドのCMデータなし',
            'Samsung mmW AUv1', 'Samsung mmW AUv2', 'Ericsson mmW',
            'ホワイトリストなし', 'ホワイトリストあり',
            'ブラックリストなし', 'ブラックリストあり',
            '作業予定局あり', '作業予定局なし', '2時間以内に更新された作業データなし'
        ],
        'COUNT': [1, 1, 2, 1, 1, 2, 0, 8, 0, 0, 4, 0, 1, 1, 2, 4, 0, 4, 0, 0, 4, 0],
        'Ericsson-MMU正常スリープ': ['●', None, None, None, None, None, None, '●', None, None, '●', None, None, None, '●', '●', None, '●', None, None, '●', None],
        'Ericsson-RRU正常スリープ': [None, '●', None, None, None, None, None, '●', None, None, '●', None, None, None, '●', '●', None, '●', None, None, '●', None],
        'Samsung-AUv1正常スリープ': [None, None, '●', None, None, None, None, '●', None, None, '●', None, '●', None, None, '●', None, '●', None, None, '●', None],
        'Samsung-AUv2正常スリープ': [None, None, '●', None, None, None, None, '●', None, None, '●', None, None, '●', None, '●', None, '●', None, None, '●', None],
        'Ericsson-MMU不正なデータ': [None, None, None, '●', None, None, None, '以降の処理中断', None, None, None, None, None, None, None, None, None, None, None, None, None, None],
        'Ericsson-RRU不正なデータ': [None, None, None, None, '●', None, None, '以降の処理中断', None, None, None, None, None, None, None, None, None, None, None, None, None, None],
        'Samsung-AUv1不正なデータ': [None, None, None, None, None, '●', None, '以降の処理中断', None, None, None, None, None, None, None, None, None, None, None, None, None, None],
        'Samsung-AUv2不正なデータ': [None, None, None, None, None, '●', None, '以降の処理中断', None, None, None, None, None, None, None, None, None, None, None, None, None, None]
    }
    
    # DataFrameを作成
    df = pd.DataFrame(data)
    
    # 出力パス
    output_path = project_root / 'data' / 'sample_sleep_function_tests.xlsx'
    
    # Excelファイルとして保存
    df.to_excel(output_path, sheet_name='スリープ機能', index=False)
    
    print(f"✅ Sample Excel file created: {output_path}")
    return output_path

def main():
    """メイン処理"""
    print("📊 Generating sample Excel file...")
    
    try:
        output_path = create_sample_excel()
        
        print("\n🎉 Sample Excel file generation completed!")
        print(f"File location: {output_path}")
        print("\nThis file can be used to test the Excel upload functionality in the application.")
        
    except Exception as e:
        print(f"\n❌ Sample Excel generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

