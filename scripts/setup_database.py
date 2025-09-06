#!/usr/bin/env python3
"""
データベースセットアップスクリプト
Database Setup Script

データベースの初期化とサンプルデータの投入を行います
"""
import sys
import os
from pathlib import Path
import uuid
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.models.database import db_manager, TestItemDB, ValidationBatchDB, LabLocationDB, AccessListDB
from app.models.validation import TestCategory, EquipmentType
import json

def create_sample_test_items():
    """サンプル検証項目を作成"""
    print("Creating sample test items...")
    
    session = db_manager.get_session()
    try:
        # 基地局スリープ機能の検証項目
        test_items = [
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.CM_DATA_ACQUISITION.value,
                "condition_text": "取得成功（Ericsson-MMU）",
                "expected_count": 1,
                "equipment_types": ["Ericsson-MMU"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.CM_DATA_ACQUISITION.value,
                "condition_text": "取得成功（Ericsson-RRU）",
                "expected_count": 1,
                "equipment_types": ["Ericsson-RRU"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.CM_DATA_ACQUISITION.value,
                "condition_text": "取得成功（Samsung）",
                "expected_count": 2,
                "equipment_types": ["Samsung-AUv1", "Samsung-AUv2"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.CM_DATA_ACQUISITION.value,
                "condition_text": "不正なデータあり（Ericsson-MMU）",
                "expected_count": 1,
                "equipment_types": ["Ericsson-MMU"],
                "scenarios": ["不正なデータ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.CM_DATA_ACQUISITION.value,
                "condition_text": "不正なデータあり（Samsung）",
                "expected_count": 2,
                "equipment_types": ["Samsung-AUv1", "Samsung-AUv2"],
                "scenarios": ["不正なデータ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.INDOOR_FILTER.value,
                "condition_text": "インドア対策局フィルタ取得成功",
                "expected_count": 8,
                "equipment_types": ["Ericsson-MMU", "Ericsson-RRU", "Samsung-AUv1", "Samsung-AUv2"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.BAND_FILTER.value,
                "condition_text": "対策バンドのCMデータあり",
                "expected_count": 4,
                "equipment_types": ["Ericsson-MMU", "Ericsson-RRU", "Samsung-AUv1", "Samsung-AUv2"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.ESG_CREATION.value,
                "condition_text": "Samsung mmW AUv1 ESG作成",
                "expected_count": 1,
                "equipment_types": ["Samsung-AUv1"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.ESG_CREATION.value,
                "condition_text": "Samsung mmW AUv2 ESG作成",
                "expected_count": 1,
                "equipment_types": ["Samsung-AUv2"],
                "scenarios": ["正常スリープ"]
            },
            {
                "id": str(uuid.uuid4()),
                "test_block": "ESG選定",
                "category": TestCategory.ESG_CREATION.value,
                "condition_text": "Ericsson mmW ESG作成",
                "expected_count": 2,
                "equipment_types": ["Ericsson-MMU", "Ericsson-RRU"],
                "scenarios": ["正常スリープ"]
            }
        ]
        
        for item_data in test_items:
            test_item = TestItemDB(
                id=item_data["id"],
                test_block=item_data["test_block"],
                category=item_data["category"],
                condition_text=item_data["condition_text"],
                expected_count=item_data["expected_count"]
            )
            test_item.set_equipment_types(item_data["equipment_types"])
            test_item.set_scenarios(item_data["scenarios"])
            
            session.add(test_item)
        
        session.commit()
        print(f"✅ Created {len(test_items)} sample test items")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to create sample test items: {e}")
        raise
    finally:
        session.close()

def create_sample_batches():
    """サンプル検証バッチを作成"""
    print("Creating sample validation batches...")
    
    session = db_manager.get_session()
    try:
        batches = [
            {
                "id": str(uuid.uuid4()),
                "name": "基地局スリープ機能検証_20240115",
                "status": "completed"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "5G設備互換性検証_20240116",
                "status": "running"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "電力効率最適化検証_20240117",
                "status": "pending"
            }
        ]
        
        for batch_data in batches:
            batch = ValidationBatchDB(
                id=batch_data["id"],
                name=batch_data["name"],
                status=batch_data["status"],
                created_at=datetime.now()
            )
            
            if batch_data["status"] == "completed":
                batch.started_at = datetime.now()
                batch.completed_at = datetime.now()
            elif batch_data["status"] == "running":
                batch.started_at = datetime.now()
            
            session.add(batch)
        
        session.commit()
        print(f"✅ Created {len(batches)} sample batches")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to create sample batches: {e}")
        raise
    finally:
        session.close()

def main():
    """メイン処理"""
    print("🔧 Setting up Lab Validation Automation Database...")
    
    try:
        # データベーステーブル作成
        print("Creating database tables...")
        db_manager.create_tables()
        print("✅ Database tables created")
        
        # 初期データ投入
        print("Initializing sample data...")
        db_manager.init_sample_data()
        print("✅ Sample data initialized")
        
        # 追加サンプルデータ作成
        create_sample_test_items()
        create_sample_batches()
        
        print("\n🎉 Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Copy env.example to .env and configure settings")
        print("2. Start the application: streamlit run app/main.py")
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

