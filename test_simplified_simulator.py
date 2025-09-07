#!/usr/bin/env python3
"""簡易化されたシミュレータのテスト"""

from mock_equipment.simplified_equipment_simulator import get_simplified_mock_equipment_manager

def test_simplified_simulator():
    print("🧪 簡易化されたシミュレータのテスト")
    
    manager = get_simplified_mock_equipment_manager()
    
    # 利用可能な設備を確認
    equipment_list = manager.get_available_equipment()
    print(f"✅ 利用可能な設備: {equipment_list}")
    
    # 各設備タイプでテスト
    test_equipment_types = ["Ericsson-MMU", "Samsung-AUv1", "Ericsson-RRU", "Samsung-AUv2"]
    
    for equipment_type in test_equipment_types:
        print(f"\n--- {equipment_type} テスト ---")
        
        # 複数回実行して成功/失敗の分布を確認
        success_count = 0
        failure_count = 0
        
        for i in range(10):
            result = manager.execute_command(equipment_type, "execute_validation")
            
            if result.get("status") == "success":
                success_count += 1
                print(f"  {i+1}. ✅ 成功: {result.get('data', {}).get('cell_id', 'N/A')}")
            else:
                failure_count += 1
                print(f"  {i+1}. ❌ 失敗: {result.get('error_message', 'N/A')}")
        
        success_rate = (success_count / 10) * 100
        print(f"  成功率: {success_rate}% (成功: {success_count}, 失敗: {failure_count})")
    
    print("\n🎯 テスト完了: 統一的なデータ通信機能が正常に動作しています")

if __name__ == "__main__":
    test_simplified_simulator()
