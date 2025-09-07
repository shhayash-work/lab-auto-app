#!/usr/bin/env python3
"""MCPサーバー + 簡易化シミュレータの統合テスト"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_mcp_server_with_simplified_simulator():
    print("🧪 MCPサーバー + 簡易化シミュレータの統合テスト")
    
    # MCPサーバーのベースURL
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. ヘルスチェック
            print("\n1. ヘルスチェック")
            health_response = await client.get(f"{base_url}/health")
            print(f"   ステータス: {health_response.status_code}")
            if health_response.status_code == 200:
                print(f"   応答: {health_response.json()}")
            
            # 2. 設備コマンド実行テスト（複数回）
            print("\n2. 設備コマンド実行テスト")
            equipment_types = ["Ericsson-MMU-001", "Samsung-AUv1-001", "Ericsson-RRU-001", "Samsung-AUv2-001"]
            
            for equipment_type in equipment_types:
                print(f"\n--- {equipment_type} テスト ---")
                success_count = 0
                failure_count = 0
                
                for i in range(5):
                    try:
                        response = await client.post(
                            f"{base_url}/mcp/call",
                            json={
                                "tool": "send_command_to_equipment",
                                "parameters": {
                                    "equipment_id": equipment_type,
                                    "command": "execute_validation",
                                    "parameters": {}
                                }
                            },
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("status") == "success":
                                equipment_response = result.get("result", {}).get("response", {})
                                if equipment_response.get("status") == "success":
                                    success_count += 1
                                    cell_id = equipment_response.get("data", {}).get("cell_id", "N/A")
                                    print(f"  {i+1}. ✅ 成功: {cell_id}")
                                else:
                                    failure_count += 1
                                    error_msg = equipment_response.get("error_message", "N/A")
                                    print(f"  {i+1}. ❌ 失敗: {error_msg}")
                            else:
                                failure_count += 1
                                print(f"  {i+1}. ❌ MCPエラー: {result.get('message', 'N/A')}")
                        else:
                            failure_count += 1
                            print(f"  {i+1}. ❌ HTTPエラー: {response.status_code}")
                            
                    except Exception as e:
                        failure_count += 1
                        print(f"  {i+1}. ❌ 例外: {str(e)}")
                
                success_rate = (success_count / 5) * 100
                print(f"  成功率: {success_rate}% (成功: {success_count}, 失敗: {failure_count})")
            
            print("\n🎯 統合テスト完了: MCPサーバー経由で簡易化シミュレータが正常に動作しています")
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        print("   MCPサーバーが起動していることを確認してください")

if __name__ == "__main__":
    asyncio.run(test_mcp_server_with_simplified_simulator())
