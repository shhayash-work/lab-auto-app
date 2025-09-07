#!/usr/bin/env python3
"""
Streamlit用LLMテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.llm_service import LLMService

def main():
    print('🔍 Streamlit用LLMテスト')
    
    # Ollama
    print('\n📱 Ollama:')
    try:
        llm = LLMService('ollama')
        items = llm.generate_test_items('基地局スリープ機能', ['ERICSSON_MMU'])
        print(f'✅ 成功: {len(items)}件生成')
        if items:
            print(f'  例: {items[0].get("condition_text", "")}')
    except Exception as e:
        print(f'❌ エラー: {e}')
    
    # AWS Bedrock
    print('\n☁️ AWS Bedrock:')
    try:
        llm = LLMService('bedrock')
        items = llm.generate_test_items('基地局スリープ機能', ['ERICSSON_MMU'])
        print(f'✅ 成功: {len(items)}件生成')
        if items:
            print(f'  例: {items[0].get("condition_text", "")}')
    except Exception as e:
        print(f'❌ エラー: {e}')

if __name__ == "__main__":
    main()

