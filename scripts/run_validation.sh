#!/bin/bash
# 検証実行スクリプト
# Validation Execution Script

set -e

# プロジェクトルートに移動
cd "$(dirname "$0")/.."

# 仮想環境をアクティベート
source venv/bin/activate

# 引数チェック
if [ $# -eq 0 ]; then
    echo "Usage: $0 <batch_name> [llm_provider]"
    echo "Example: $0 'Sleep Function Test' ollama"
    exit 1
fi

BATCH_NAME="$1"
LLM_PROVIDER="${2:-ollama}"

echo "🚀 Starting validation execution..."
echo "Batch Name: $BATCH_NAME"
echo "LLM Provider: $LLM_PROVIDER"
echo "Timestamp: $(date)"

# Python検証スクリプトを実行
python -c "
import sys
sys.path.append('.')

from app.services.validation_engine import get_validation_engine
from app.services.llm_service import get_llm_service
from app.models.validation import TestItem, TestCondition, TestCategory, EquipmentType
import uuid
from datetime import datetime

def create_sample_test_items():
    '''サンプル検証項目を作成'''
    items = []
    
    # 基地局スリープ機能の基本検証
    item1 = TestItem(
        id=str(uuid.uuid4()),
        test_block='ESG選定',
        category=TestCategory.CM_DATA_ACQUISITION,
        condition=TestCondition(
            condition_text='CMデータ取得成功（全設備）',
            expected_count=4,
            equipment_types=[
                EquipmentType.ERICSSON_MMU,
                EquipmentType.ERICSSON_RRU,
                EquipmentType.SAMSUNG_AUV1,
                EquipmentType.SAMSUNG_AUV2
            ]
        ),
        scenarios=['正常スリープ', '不正なデータ']
    )
    items.append(item1)
    
    return items

def main():
    print('Initializing validation engine...')
    engine = get_validation_engine('$LLM_PROVIDER')
    
    print('Creating test items...')
    test_items = create_sample_test_items()
    
    print('Creating validation batch...')
    batch = engine.create_batch_from_test_items(test_items, '$BATCH_NAME')
    
    print('Executing validation batch...')
    def progress_callback(progress, result):
        print(f'Progress: {progress:.1%} - Latest: {result.equipment_type.value} -> {result.result.value}')
    
    completed_batch = engine.execute_batch(batch, progress_callback)
    
    print('\\n📊 Validation Results:')
    summary = engine.get_batch_summary(completed_batch)
    print(f'Total Tests: {summary[\"total_tests\"]}')
    print(f'Success Rate: {summary[\"success_rate\"]:.1%}')
    print(f'Average Execution Time: {summary[\"average_execution_time\"]:.2f}s')
    print(f'Status: {summary[\"status\"]}')
    
    print('\\n🎉 Validation completed successfully!')

if __name__ == '__main__':
    main()
"

echo "✅ Validation execution completed!"
echo "Check the results in the Streamlit dashboard."



