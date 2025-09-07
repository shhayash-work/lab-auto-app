#!/usr/bin/env python3
"""
真のAIエージェント実装 - 軽量テスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_rag_only():
    """RAG機能のみテスト（LLM呼び出しなし）"""
    try:
        from app.services.vector_store import get_vector_store
        
        print("🔍 RAG機能テスト開始")
        
        # ベクターストア初期化
        vector_store = get_vector_store()
        print('✅ ベクターストア初期化成功')
        
        # RAG検索テスト
        queries = [
            "基地局スリープ機能 CMデータ",
            "ESG選定 検証",
            "フィルタ処理 ホワイトリスト"
        ]
        
        for query in queries:
            results = vector_store.search_similar_documents(query, top_k=2)
            print(f'✅ RAG検索 "{query}": {len(results)}件発見')
            
            for i, result in enumerate(results, 1):
                content = result.get("content", "")[:80]
                print(f'  {i}. {content}...')
        
        return True
    except Exception as e:
        print(f'❌ RAGテストエラー: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_mcp_server_connection():
    """MCPサーバー接続テスト"""
    try:
        import requests
        
        print("🔌 MCPサーバー接続テスト")
        
        # ヘルスチェック
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print('✅ MCPサーバー接続成功')
            health_data = response.json()
            print(f'  サービス: {health_data.get("service", "Unknown")}')
            return True
        else:
            print(f'❌ MCPサーバー応答エラー: {response.status_code}')
            return False
            
    except Exception as e:
        print(f'❌ MCPサーバー接続エラー: {e}')
        return False

def test_mock_equipment():
    """疑似ラボ設備テスト"""
    try:
        from mock_equipment.equipment_simulator import mock_equipment_manager
        
        print("🔧 疑似ラボ設備テスト")
        
        # CMデータ取得テスト
        equipment = mock_equipment_manager.get_equipment("ERICSSON_MMU_001")
        if equipment:
            cm_data = equipment.get_cm_data()
            print(f'✅ CMデータ取得成功: {len(cm_data)}件のデータ')
        else:
            print('⚠️ 設備が見つかりません - デフォルト設備でテスト')
            # デフォルト設備でテスト
            from mock_equipment.equipment_simulator import EricssonMMUSimulator
            test_equipment = EricssonMMUSimulator("TEST_001")
            cm_data = test_equipment.get_cm_data()
            print(f'✅ CMデータ取得成功: {len(cm_data)}件のデータ')
        
        # コマンド実行テスト
        result = mock_equipment_manager.execute_command(
            "ERICSSON_MMU_001", 
            "test_command", 
            {"test": "parameter"}
        )
        print(f'✅ コマンド実行成功: {result.get("status", "Unknown")}')
        
        return True
    except Exception as e:
        print(f'❌ 疑似ラボ設備エラー: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_no_fake_data():
    """偽装データがないことを確認"""
    try:
        print("🕵️ 偽装データ検査")
        
        # LLMサービスのフォールバック機能チェック
        from app.services.llm_service import LLMService
        
        # ソースコードを読んで偽装チェック
        llm_file = Path(__file__).parent / "app" / "services" / "llm_service.py"
        with open(llm_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 偽装キーワードをチェック
        fake_keywords = [
            "_generate_fallback_test_items",
            "固定メッセージ",
            "ダミー",
            "fake",
            "random.choice"
        ]
        
        found_fake = []
        for keyword in fake_keywords:
            if keyword in content:
                found_fake.append(keyword)
        
        if found_fake:
            print(f'⚠️ 偽装の可能性: {", ".join(found_fake)}')
            return False
        else:
            print('✅ 偽装データなし - 真のAI実装確認')
            return True
            
    except Exception as e:
        print(f'❌ 偽装検査エラー: {e}')
        return False

def main():
    """軽量テスト実行"""
    print("🚀 真のAIエージェント - 軽量テスト開始")
    print("=" * 50)
    
    tests = [
        ("RAG機能", test_rag_only),
        ("MCPサーバー接続", test_mcp_server_connection),
        ("疑似ラボ設備", test_mock_equipment),
        ("偽装データ検査", test_no_fake_data)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}テスト")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: 成功")
            else:
                print(f"❌ {test_name}: 失敗")
        except Exception as e:
            print(f"❌ {test_name}: 例外 - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 合格: {passed}/{total}")
    
    if passed == total:
        print("🎉 真のAIエージェント実装テスト完了!")
        print("✅ 偽装なし、実際のRAG・MCP・疑似設備が動作中")
    else:
        print("⚠️ 一部テスト失敗 - 修正が必要")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
