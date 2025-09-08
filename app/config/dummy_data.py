"""
ダミーデータ管理
Demo Data Management

デモ用のダミー検証バッチとその結果データを管理
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from app.models.validation import (
    ValidationBatch, ValidationResult, TestItem, TestCondition, 
    TestCategory, EquipmentType, ValidationStatus, TestResult
)

# ダミーデータファイルパス
DUMMY_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "dummy"
DUMMY_DATA_DIR.mkdir(parents=True, exist_ok=True)

DUMMY_BATCHES_FILE = DUMMY_DATA_DIR / "dummy_batches.json"
DUMMY_RESULTS_FILE = DUMMY_DATA_DIR / "dummy_results.json"

def create_dummy_test_items() -> List[TestItem]:
    """ダミー検証項目を作成"""
    return [
        TestItem(
            id=str(uuid.uuid4()),
            test_block="基地局スリープ機能",
            category=TestCategory.CM_DATA_ACQUISITION,
            condition=TestCondition(
                condition_text="CMデータの取得成功",
                equipment_types=[EquipmentType.TAKANAWA_ERICSSON]
            )
        ),
        TestItem(
            id=str(uuid.uuid4()),
            test_block="基地局スリープ機能",
            category=TestCategory.ESG_SELECTION,
            condition=TestCondition(
                condition_text="スリープモード移行確認",
                equipment_types=[EquipmentType.TAKANAWA_SAMSUNG]
            )
        ),
        TestItem(
            id=str(uuid.uuid4()),
            test_block="アクセス制御",
            category=TestCategory.ESG_CREATION,
            condition=TestCondition(
                condition_text="アクセス制御性能測定",
                equipment_types=[EquipmentType.OOKAYAMA_NOKIA]
            )
        )
    ]

def create_dummy_validation_results(test_items: List[TestItem]) -> List[ValidationResult]:
    """ダミー検証結果を作成"""
    results = []
    
    for item in test_items:
        for equipment_type in item.condition.equipment_types:
            result = ValidationResult(
                id=str(uuid.uuid4()),
                test_item_id=item.id,
                equipment_type=equipment_type,
                result=TestResult.PASS if len(results) % 3 != 2 else TestResult.FAIL,
                details=f"AIエージェントによる自動検証完了: {item.condition.condition_text}",
                confidence=0.85 + (len(results) % 3) * 0.05,
                execution_time=1.2 + (len(results) % 5) * 0.3,
                created_at=datetime.now() - timedelta(hours=len(results))
            )
            results.append(result)
    
    return results

def create_dummy_batches() -> List[Dict[str, Any]]:
    """ダミー検証バッチを作成"""
    batches = []
    
    # 過去1週間のダミーバッチを作成
    for i in range(15):
        date = datetime.now() - timedelta(days=i // 2, hours=i % 24)
        test_items = create_dummy_test_items()
        results = create_dummy_validation_results(test_items)
        
        status = ValidationStatus.COMPLETED
        if i == 0:  # 最新は実行中
            status = ValidationStatus.RUNNING
        elif i % 7 == 6:  # 7件に1件は失敗
            status = ValidationStatus.FAILED
        
        batch = {
            'id': f"batch_{date.strftime('%Y%m%d_%H%M%S')}_{i}",
            'name': f"検証バッチ_基地局スリープ機能_{date.strftime('%Y%m%d')}_{date.strftime('%H%M%S')}",
            'created_at': date.strftime('%Y/%m/%d %H:%M:%S'),
            'completed_at': date.strftime('%Y/%m/%d %H:%M:%S') if status != ValidationStatus.RUNNING else None,
            'status': status.value,
            'test_items': [item.to_dict() for item in test_items],
            'results': [result.to_dict() for result in results] if status == ValidationStatus.COMPLETED else [],
            'test_count': len(test_items),
            'success_rate': f"{len([r for r in results if r.result == TestResult.PASS]) / len(results) * 100:.1f}%" if results else "0%"
        }
        batches.append(batch)
    
    return batches

def save_dummy_data():
    """ダミーデータをファイルに保存"""
    batches = create_dummy_batches()
    
    with open(DUMMY_BATCHES_FILE, 'w', encoding='utf-8') as f:
        json.dump(batches, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"ダミーデータを保存しました: {DUMMY_BATCHES_FILE}")

def load_dummy_batches() -> List[Dict[str, Any]]:
    """ダミー検証バッチを読み込み"""
    if not DUMMY_BATCHES_FILE.exists():
        save_dummy_data()
    
    with open(DUMMY_BATCHES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_dashboard_metrics() -> Dict[str, int]:
    """ダッシュボード用メトリクスを取得"""
    batches = load_dummy_batches()
    today = datetime.now().strftime('%Y/%m/%d')
    
    today_batches = len([b for b in batches if b.get('completed_at', '').startswith(today)])
    success_batches = len([b for b in batches if b.get('status') == 'COMPLETED'])
    fail_batches = len([b for b in batches if b.get('status') == 'FAILED'])
    running_batches = len([b for b in batches if b.get('status') == 'RUNNING'])
    
    return {
        'today_batches': today_batches,
        'success_batches': success_batches,
        'fail_batches': fail_batches,
        'running_batches': running_batches
    }

def initialize_dummy_data():
    """ダミーデータを初期化"""
    save_dummy_data()
    print("ダミーデータを初期化しました")

if __name__ == "__main__":
    initialize_dummy_data()
