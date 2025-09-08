#!/usr/bin/env python3
"""リアルな通信設備検証データ30件作成"""

import json
import uuid
from datetime import datetime, timedelta
from app.models.validation import (
    TestItem, ValidationBatch, ValidationResult, TestCondition,
    TestCategory, EquipmentType, ValidationStatus, TestResult
)
from app.config.dummy_data import initialize_dummy_data

def create_realistic_validation_data():
    """リアルな通信設備検証データを作成"""
    
    # 実際の通信設備検証の試験ブロック
    test_blocks = [
        "基地局スリープ機能",
        "5G NR接続性能",
        "LTE-5G連携機能", 
        "ビームフォーミング制御",
        "キャリアアグリゲーション",
        "VoLTE音声品質",
        "ハンドオーバー性能",
        "電力制御機能",
        "干渉制御機能",
        "セル選択・再選択",
        "RRC接続管理",
        "QoS制御機能",
        "セキュリティ機能",
        "O&M機能",
        "アラーム監視機能"
    ]
    
    # 設備タイプと実行日のバリエーション
    equipment_combinations = [
        [EquipmentType.ERICSSON_MMU],
        [EquipmentType.SAMSUNG_AUV1], 
        [EquipmentType.ERICSSON_RRU],
        [EquipmentType.SAMSUNG_AUV2],
        [EquipmentType.ERICSSON_MMU, EquipmentType.ERICSSON_RRU],
        [EquipmentType.SAMSUNG_AUV1, EquipmentType.SAMSUNG_AUV2]
    ]
    
    batches = []
    all_test_items = []
    
    # 30件のバッチを作成
    for i in range(30):
        test_block = test_blocks[i % len(test_blocks)]
        equipment_types = equipment_combinations[i % len(equipment_combinations)]
        
        # 日付をランダムに設定（過去30日以内）
        days_ago = i % 30
        execution_date = datetime.now() - timedelta(days=days_ago)
        date_str = execution_date.strftime('%Y%m%d')
        time_str = execution_date.strftime('%H%M%S')
        
        batch_name = f"検証バッチ_{test_block}_{date_str}_{time_str}"
        
        # 各バッチに2-4個の検証項目を作成
        test_items = []
        item_count = 2 + (i % 3)  # 2-4個
        
        for j in range(item_count):
            test_item = create_test_item_for_block(test_block, equipment_types, j)
            test_items.append(test_item)
            all_test_items.append(test_item)
        
        # バッチ作成
        batch = ValidationBatch(
            id=str(uuid.uuid4()),
            name=batch_name,
            test_items=test_items,
            created_at=execution_date
        )
        
        # 本日実行分の結果を設定（6件のうち4成功、1失敗、1実行中）
        if days_ago == 0 and len(batches) < 6:
            if len(batches) < 4:
                # 成功
                batch.status = ValidationStatus.COMPLETED
                batch.started_at = execution_date
                batch.completed_at = execution_date + timedelta(minutes=5 + i)
                batch.results = create_success_results(test_items, equipment_types)
            elif len(batches) == 4:
                # 失敗
                batch.status = ValidationStatus.FAILED
                batch.started_at = execution_date
                batch.completed_at = execution_date + timedelta(minutes=3)
                batch.results = create_failure_results(test_items, equipment_types)
            else:
                # 実行中
                batch.status = ValidationStatus.RUNNING
                batch.started_at = execution_date
                batch.results = []
        else:
            # 過去の実行済み
            if i % 5 == 0:
                batch.status = ValidationStatus.FAILED
                batch.results = create_failure_results(test_items, equipment_types)
            else:
                batch.status = ValidationStatus.COMPLETED
                batch.results = create_success_results(test_items, equipment_types)
            
            batch.started_at = execution_date
            batch.completed_at = execution_date + timedelta(minutes=2 + (i % 8))
        
        batches.append(batch)
    
    return batches, all_test_items

def create_test_item_for_block(test_block: str, equipment_types: list, index: int) -> TestItem:
    """試験ブロックに応じた検証項目を作成"""
    
    test_conditions = {
        "基地局スリープ機能": [
            ("ESG選定", "スリープ対象基地局のESGが正しく選定されること", TestCategory.ESG_SELECTION),
            ("CMデータ取得", "基地局のCMデータが正常に取得できること", TestCategory.CM_DATA_ACQUISITION),
            ("スリープ制御", "基地局のスリープ/ウェイクアップが正常動作すること", TestCategory.ESG_CREATION),
            ("電力削減効果", "スリープ時の消費電力が期待値以下になること", TestCategory.WORK_DATA_FILTER)
        ],
        "5G NR接続性能": [
            ("初期接続", "5G NRセルへの初期接続が正常に完了すること", TestCategory.CM_DATA_ACQUISITION),
            ("スループット", "下り/上りスループットが仕様値を満たすこと", TestCategory.BAND_FILTER),
            ("レイテンシ", "エンドツーエンドレイテンシが要求値以下であること", TestCategory.ESG_SELECTION),
            ("接続維持", "5G NR接続が安定して維持されること", TestCategory.ESG_CREATION)
        ],
        "LTE-5G連携機能": [
            ("デュアル接続", "LTE-5G同時接続が正常に確立されること", TestCategory.CM_DATA_ACQUISITION),
            ("ベアラ分離", "LTE/5Gベアラの適切な分離制御が動作すること", TestCategory.BAND_FILTER),
            ("負荷分散", "トラフィック負荷が適切に分散されること", TestCategory.WORK_DATA_FILTER),
            ("切替制御", "LTE-5G間の切替が正常に動作すること", TestCategory.ESG_SELECTION)
        ],
        "ビームフォーミング制御": [
            ("ビーム生成", "適切なビームパターンが生成されること", TestCategory.ESG_CREATION),
            ("追従制御", "端末移動に対するビーム追従が正常動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("干渉抑制", "他セルへの干渉が適切に抑制されること", TestCategory.BAND_FILTER),
            ("SINR改善", "ビームフォーミングによりSINRが改善されること", TestCategory.WORK_DATA_FILTER)
        ],
        "キャリアアグリゲーション": [
            ("CA設定", "複数キャリアの集約設定が正常に動作すること", TestCategory.ESG_SELECTION),
            ("スケジューリング", "CA環境でのスケジューリングが適切に動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("品質制御", "各キャリアの品質が適切に制御されること", TestCategory.BAND_FILTER),
            ("スループット向上", "CAによりスループットが向上すること", TestCategory.WORK_DATA_FILTER)
        ],
        "VoLTE音声品質": [
            ("音声接続", "VoLTE音声接続が正常に確立されること", TestCategory.CM_DATA_ACQUISITION),
            ("音質評価", "音声品質が基準値を満たすこと", TestCategory.ESG_SELECTION),
            ("ハンドオーバー", "通話中ハンドオーバーが正常動作すること", TestCategory.ESG_CREATION),
            ("緊急通話", "緊急通話機能が正常に動作すること", TestCategory.WORK_DATA_FILTER)
        ],
        "ハンドオーバー性能": [
            ("セル間HO", "セル間ハンドオーバーが正常に完了すること", TestCategory.ESG_SELECTION),
            ("周波数間HO", "周波数間ハンドオーバーが正常動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("システム間HO", "LTE-5G間ハンドオーバーが正常動作すること", TestCategory.BAND_FILTER),
            ("HO失敗率", "ハンドオーバー失敗率が基準値以下であること", TestCategory.WORK_DATA_FILTER)
        ],
        "電力制御機能": [
            ("上り電力制御", "端末上り送信電力が適切に制御されること", TestCategory.CM_DATA_ACQUISITION),
            ("下り電力制御", "基地局下り送信電力が適切に制御されること", TestCategory.ESG_SELECTION),
            ("省電力制御", "低トラフィック時の省電力制御が動作すること", TestCategory.ESG_CREATION),
            ("電力効率", "電力効率が目標値を達成すること", TestCategory.WORK_DATA_FILTER)
        ],
        "干渉制御機能": [
            ("セル間干渉制御", "隣接セル間の干渉が適切に制御されること", TestCategory.BAND_FILTER),
            ("上り干渉制御", "上り干渉が適切に抑制されること", TestCategory.CM_DATA_ACQUISITION),
            ("下り干渉制御", "下り干渉が適切に抑制されること", TestCategory.ESG_SELECTION),
            ("SINR維持", "干渉制御によりSINRが維持されること", TestCategory.WORK_DATA_FILTER)
        ],
        "セル選択・再選択": [
            ("初期セル選択", "電源投入時の初期セル選択が正常動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("セル再選択", "移動時のセル再選択が適切に動作すること", TestCategory.ESG_SELECTION),
            ("優先度制御", "セル優先度に基づく選択が正常動作すること", TestCategory.ESG_CREATION),
            ("品質基準", "セル選択品質基準が適切に適用されること", TestCategory.BAND_FILTER)
        ],
        "RRC接続管理": [
            ("RRC接続確立", "RRC接続確立が正常に完了すること", TestCategory.CM_DATA_ACQUISITION),
            ("RRC再設定", "RRC接続再設定が正常に動作すること", TestCategory.ESG_SELECTION),
            ("RRC解放", "RRC接続解放が適切に実行されること", TestCategory.ESG_CREATION),
            ("状態遷移", "RRC状態遷移が正常に動作すること", TestCategory.WORK_DATA_FILTER)
        ],
        "QoS制御機能": [
            ("QoSフロー制御", "QoSフローの制御が正常に動作すること", TestCategory.ESG_SELECTION),
            ("優先度制御", "トラフィック優先度制御が適切に動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("帯域制御", "帯域制御が仕様通りに動作すること", TestCategory.BAND_FILTER),
            ("遅延制御", "遅延制御が要求仕様を満たすこと", TestCategory.WORK_DATA_FILTER)
        ],
        "セキュリティ機能": [
            ("認証機能", "端末認証が正常に動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("暗号化機能", "通信データの暗号化が正常に動作すること", TestCategory.ESG_SELECTION),
            ("完全性保護", "データ完全性保護が正常に動作すること", TestCategory.ESG_CREATION),
            ("鍵管理", "暗号鍵管理が適切に動作すること", TestCategory.WORK_DATA_FILTER)
        ],
        "O&M機能": [
            ("設定管理", "基地局設定管理が正常に動作すること", TestCategory.ESG_SELECTION),
            ("性能監視", "性能データ収集・監視が正常動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("ログ管理", "ログ収集・管理機能が正常動作すること", TestCategory.WORK_DATA_FILTER),
            ("リモート制御", "リモート制御機能が正常に動作すること", TestCategory.ESG_CREATION)
        ],
        "アラーム監視機能": [
            ("アラーム検出", "異常状態のアラーム検出が正常動作すること", TestCategory.CM_DATA_ACQUISITION),
            ("アラーム通知", "アラーム通知機能が正常に動作すること", TestCategory.ESG_SELECTION),
            ("アラーム分析", "アラーム原因分析機能が正常動作すること", TestCategory.ESG_CREATION),
            ("復旧制御", "自動復旧制御が適切に動作すること", TestCategory.WORK_DATA_FILTER)
        ]
    }
    
    conditions = test_conditions.get(test_block, [
        ("基本機能", f"{test_block}の基本機能が正常に動作すること", TestCategory.CM_DATA_ACQUISITION)
    ])
    
    condition_data = conditions[index % len(conditions)]
    
    return TestItem(
        id=str(uuid.uuid4()),
        test_block=condition_data[0],
        category=condition_data[2],
        condition=TestCondition(
            condition_text=condition_data[1],
            expected_count=1 + (index % 3),
            equipment_types=equipment_types
        )
    )

def create_success_results(test_items: list, equipment_types: list) -> list:
    """成功結果を作成"""
    results = []
    for test_item in test_items:
        for equipment_type in equipment_types:
            result = ValidationResult(
                id=str(uuid.uuid4()),
                test_item_id=test_item.id,
                equipment_type=equipment_type,
                result=TestResult.PASS,
                details=f"{test_item.test_block}が正常に動作し、すべての条件を満たしています。",
                execution_time=2.5 + (hash(test_item.id) % 100) / 100,
                confidence=0.85 + (hash(test_item.id) % 15) / 100
            )
            results.append(result)
    return results

def create_failure_results(test_items: list, equipment_types: list) -> list:
    """失敗結果を作成"""
    results = []
    for test_item in test_items:
        for equipment_type in equipment_types:
            result = ValidationResult(
                id=str(uuid.uuid4()),
                test_item_id=test_item.id,
                equipment_type=equipment_type,
                result=TestResult.FAIL,
                details=f"{test_item.test_block}で異常が検出されました。設定値が期待値と異なります。",
                execution_time=1.8 + (hash(test_item.id) % 80) / 100,
                error_message="設定値不整合エラー",
                confidence=0.75 + (hash(test_item.id) % 20) / 100
            )
            results.append(result)
    return results

if __name__ == "__main__":
    print("🏗️ リアルな通信設備検証データを作成中...")
    
    batches, test_items = create_realistic_validation_data()
    
    print(f"✅ 作成完了:")
    print(f"  - 検証バッチ: {len(batches)}件")
    print(f"  - 検証項目: {len(test_items)}件")
    
    # データをJSONで保存
    batch_data = []
    for batch in batches:
        batch_dict = {
            'id': batch.id,
            'name': batch.name,
            'status': batch.status.value,
            'test_items': [item.to_dict() for item in batch.test_items],
            'results': [result.to_dict() for result in batch.results] if batch.results else [],
            'created_at': batch.created_at.isoformat(),
            'started_at': batch.started_at.isoformat() if batch.started_at else None,
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None
        }
        batch_data.append(batch_dict)
    
    # ファイルに保存
    import os
    os.makedirs('data/realistic', exist_ok=True)
    
    with open('data/realistic/realistic_batches.json', 'w', encoding='utf-8') as f:
        json.dump(batch_data, f, ensure_ascii=False, indent=2)
    
    print(f"📁 データを保存しました: data/realistic/realistic_batches.json")

