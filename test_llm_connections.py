#!/usr/bin/env python3
"""
LLM接続テスト - 実際の接続と生成をテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_ollama_connection():
    """Ollama接続と生成テスト"""
    try:
        from app.services.llm_service import LLMService
        
        print("🔍 Ollama接続テスト")
        
        # LLMサービス初期化
        llm_service = LLMService(provider="ollama")
        print('✅ Ollama LLMサービス初期化成功')
        
        # 簡単な生成テスト
        print('🤖 Ollama生成テスト中...')
        test_items = llm_service.generate_test_items(
            feature_name="テスト機能", 
            equipment_types=["ERICSSON_MMU"]
        )
        print(f'✅ Ollama生成成功: {len(test_items)}件生成')
        
        # 生成内容確認
        for i, item in enumerate(test_items[:2], 1):
            print(f'  {i}. {item.get("test_block", "")}: {item.get("condition_text", "")}')
        
        return True
        
    except Exception as e:
        print(f'❌ Ollamaエラー: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_bedrock_connection():
    """AWS Bedrock接続と生成テスト"""
    try:
        from app.services.llm_service import LLMService
        
        print("\n🔍 AWS Bedrock接続テスト")
        
        # LLMサービス初期化
        llm_service = LLMService(provider="bedrock")
        print('✅ Bedrock LLMサービス初期化成功')
        
        # 簡単な生成テスト
        print('🤖 Bedrock生成テスト中...')
        test_items = llm_service.generate_test_items(
            feature_name="テスト機能", 
            equipment_types=["ERICSSON_MMU"]
        )
        print(f'✅ Bedrock生成成功: {len(test_items)}件生成')
        
        # 生成内容確認
        for i, item in enumerate(test_items[:2], 1):
            print(f'  {i}. {item.get("test_block", "")}: {item.get("condition_text", "")}')
        
        return True
        
    except Exception as e:
        print(f'❌ Bedrockエラー: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_openai_connection():
    """OpenAI接続と生成テスト"""
    try:
        from app.services.llm_service import LLMService
        
        print("\n🔍 OpenAI接続テスト")
        
        # LLMサービス初期化
        llm_service = LLMService(provider="openai")
        print('✅ OpenAI LLMサービス初期化成功')
        
        # 簡単な生成テスト
        print('🤖 OpenAI生成テスト中...')
        test_items = llm_service.generate_test_items(
            feature_name="テスト機能", 
            equipment_types=["ERICSSON_MMU"]
        )
        print(f'✅ OpenAI生成成功: {len(test_items)}件生成')
        
        # 生成内容確認
        for i, item in enumerate(test_items[:2], 1):
            print(f'  {i}. {item.get("test_block", "")}: {item.get("condition_text", "")}')
        
        return True
        
    except Exception as e:
        print(f'❌ OpenAIエラー: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_anthropic_connection():
    """Anthropic接続と生成テスト"""
    try:
        from app.services.llm_service import LLMService
        
        print("\n🔍 Anthropic接続テスト")
        
        # LLMサービス初期化
        llm_service = LLMService(provider="anthropic")
        print('✅ Anthropic LLMサービス初期化成功')
        
        # 簡単な生成テスト
        print('🤖 Anthropic生成テスト中...')
        test_items = llm_service.generate_test_items(
            feature_name="テスト機能", 
            equipment_types=["ERICSSON_MMU"]
        )
        print(f'✅ Anthropic生成成功: {len(test_items)}件生成')
        
        # 生成内容確認
        for i, item in enumerate(test_items[:2], 1):
            print(f'  {i}. {item.get("test_block", "")}: {item.get("condition_text", "")}')
        
        return True
        
    except Exception as e:
        print(f'❌ Anthropicエラー: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """LLM接続テスト実行"""
    print("🚀 LLM接続・生成テスト開始")
    print("=" * 60)
    
    tests = [
        ("Ollama", test_ollama_connection),
        ("AWS Bedrock", test_bedrock_connection),
        ("OpenAI", test_openai_connection),
        ("Anthropic", test_anthropic_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}: 例外 - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 LLM接続テスト結果サマリー")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 接続・生成成功" if result else "❌ 接続・生成失敗"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 成功: {passed}/{total}")
    
    if passed > 0:
        print("🎉 少なくとも1つのLLMプロバイダーが動作中")
    else:
        print("⚠️ 全LLMプロバイダーで問題発生 - 設定確認が必要")
    
    return passed > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

