"""
LLMサービス
LLM Service for validation and analysis

複数のLLMプロバイダー対応:
- Ollama (ローカル)
- OpenAI GPT-4o
- Anthropic Claude
- AWS Bedrock
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

try:
    import ollama
except ImportError:
    ollama = None

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import boto3
except ImportError:
    boto3 = None

from app.config.settings import (
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, BEDROCK_MODEL
)

logger = logging.getLogger(__name__)

class LLMService:
    """LLMサービスクラス"""
    
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """クライアントをセットアップ"""
        try:
            if self.provider == "ollama":
                self._setup_ollama()
            elif self.provider == "openai":
                self._setup_openai()
            elif self.provider == "anthropic":
                self._setup_anthropic()
            elif self.provider == "bedrock":
                self._setup_bedrock()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Failed to setup {self.provider}: {e}")
            # フォールバック: Ollamaを試す
            if self.provider != "ollama":
                logger.info("Falling back to Ollama")
                self.provider = "ollama"
                self._setup_ollama()
    
    def _setup_ollama(self):
        """Ollamaクライアントをセットアップ"""
        if ollama is None:
            raise ImportError("ollama package not installed")
        
        self.client = ollama.Client(host=OLLAMA_BASE_URL)
        
        # 接続テスト
        try:
            models = self.client.list()
            available_models = [model['name'] for model in models.get('models', [])]
            if OLLAMA_MODEL not in available_models:
                logger.warning(f"Model {OLLAMA_MODEL} not found. Available: {available_models}")
            logger.info(f"✅ Ollama connected: {OLLAMA_BASE_URL}")
        except Exception as e:
            logger.error(f"❌ Ollama connection failed: {e}")
            raise
    
    def _setup_openai(self):
        """OpenAIクライアントをセットアップ"""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        
        if openai is None:
            raise ImportError("openai package not installed")
        
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI client initialized")
    
    def _setup_anthropic(self):
        """Anthropicクライアントをセットアップ"""
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        if anthropic is None:
            raise ImportError("anthropic package not installed")
        
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("✅ Anthropic client initialized")
    
    def _setup_bedrock(self):
        """AWS Bedrockクライアントをセットアップ"""
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS credentials not set")
        
        if boto3 is None:
            raise ImportError("boto3 package not installed")
        
        self.client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        logger.info("✅ AWS Bedrock client initialized")
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """レスポンスを生成"""
        try:
            if self.provider == "ollama":
                return self._generate_ollama(prompt, system_prompt)
            elif self.provider == "openai":
                return self._generate_openai(prompt, system_prompt)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, system_prompt)
            elif self.provider == "bedrock":
                return self._generate_bedrock(prompt, system_prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"エラー: LLM応答の生成に失敗しました ({str(e)})"
    
    def _generate_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Ollama応答を生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 2048
            }
        )
        return response['message']['content']
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """OpenAI応答を生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message.content
    
    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Anthropic応答を生成"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            temperature=0.7,
            messages=[{"role": "user", "content": full_prompt}]
        )
        return response.content[0].text
    
    def _generate_bedrock(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """AWS Bedrock応答を生成"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "temperature": 0.7,
            "messages": [{"role": "user", "content": full_prompt}]
        })
        
        response = self.client.invoke_model(
            modelId=BEDROCK_MODEL,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def analyze_validation_result(self, test_item: Dict[str, Any], equipment_response: Dict[str, Any]) -> Dict[str, Any]:
        """検証結果を分析"""
        system_prompt = """あなたは通信設備の検証エキスパートです。
基地局設備からの応答データを分析し、テスト項目の合格/不合格を判定してください。

判定基準:
- PASS: 期待される動作が正常に実行され、すべての条件を満たしている
- FAIL: 期待される動作が実行されない、または条件を満たしていない
- WARNING: 動作はするが、パフォーマンスや設定に問題がある可能性

応答は必ずJSON形式で以下の構造にしてください:
{
    "result": "PASS|FAIL|WARNING",
    "confidence": 0.0-1.0,
    "analysis": "詳細な分析内容",
    "issues": ["問題点のリスト"],
    "recommendations": ["推奨事項のリスト"]
}"""
        
        prompt = f"""
テスト項目:
- カテゴリ: {test_item.get('category', 'N/A')}
- 条件: {test_item.get('condition', {}).get('condition_text', 'N/A')}
- 期待件数: {test_item.get('condition', {}).get('expected_count', 0)}

設備応答データ:
{json.dumps(equipment_response, ensure_ascii=False, indent=2)}

この応答データを分析し、テスト項目の合格/不合格を判定してください。
"""
        
        try:
            response = self.generate_response(prompt, system_prompt)
            
            # JSONパースを試行
            try:
                result = json.loads(response)
                
                # 必要なフィールドの検証
                required_fields = ['result', 'confidence', 'analysis']
                for field in required_fields:
                    if field not in result:
                        result[field] = self._get_default_value(field)
                
                # 値の範囲チェック
                if not isinstance(result['confidence'], (int, float)) or not 0 <= result['confidence'] <= 1:
                    result['confidence'] = 0.8
                
                if result['result'] not in ['PASS', 'FAIL', 'WARNING']:
                    result['result'] = 'FAIL'
                
                return result
                
            except json.JSONDecodeError:
                # JSONパースに失敗した場合のフォールバック
                logger.warning("Failed to parse LLM response as JSON, using fallback analysis")
                return self._fallback_analysis(equipment_response)
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_analysis(equipment_response)
    
    def _get_default_value(self, field: str) -> Any:
        """デフォルト値を取得"""
        defaults = {
            'result': 'FAIL',
            'confidence': 0.5,
            'analysis': 'LLM分析でエラーが発生しました',
            'issues': [],
            'recommendations': []
        }
        return defaults.get(field, None)
    
    def _fallback_analysis(self, equipment_response: Dict[str, Any]) -> Dict[str, Any]:
        """フォールバック分析（ルールベース）"""
        status = equipment_response.get('status', 'error')
        
        if status == 'success':
            # 基本的な成功判定
            parsed_data = equipment_response.get('parsed_data', {})
            signal_strength = parsed_data.get('signal_strength_dbm', -999)
            error_rate = parsed_data.get('error_rate_percent', 100)
            
            if signal_strength > -100 and error_rate < 10:
                return {
                    'result': 'PASS',
                    'confidence': 0.8,
                    'analysis': 'ルールベース分析: 基本的な条件を満たしています',
                    'issues': [],
                    'recommendations': []
                }
            else:
                return {
                    'result': 'WARNING',
                    'confidence': 0.6,
                    'analysis': 'ルールベース分析: パフォーマンスに問題がある可能性があります',
                    'issues': [f'信号強度: {signal_strength}dBm', f'エラー率: {error_rate}%'],
                    'recommendations': ['設備の設定を確認してください']
                }
        else:
            return {
                'result': 'FAIL',
                'confidence': 0.9,
                'analysis': 'ルールベース分析: 設備からエラー応答を受信しました',
                'issues': [equipment_response.get('error_message', '不明なエラー')],
                'recommendations': ['設備の接続状態を確認してください']
            }
    
    def generate_test_items(self, feature_name: str, equipment_types: List[str]) -> List[Dict[str, Any]]:
        """検証項目を生成"""
        system_prompt = """あなたは通信設備の検証エキスパートです。
新機能に対する検証項目を生成してください。

以下の観点を含めてください:
1. CMデータの取得
2. 各種フィルタ処理
3. 正常系・準正常系・異常系のシナリオ
4. 設備タイプ別の検証

応答は必ずJSON配列形式で、以下の構造にしてください:
[
    {
        "test_block": "試験ブロック名",
        "category": "検証カテゴリ",
        "condition_text": "検証条件の詳細",
        "expected_count": 期待件数,
        "scenarios": ["シナリオ1", "シナリオ2", ...]
    }
]"""
        
        prompt = f"""
機能名: {feature_name}
対象設備: {', '.join(equipment_types)}

この機能に対する包括的な検証項目を生成してください。
基地局スリープ機能の検証を参考に、以下の観点を含めてください:

1. ESG選定
2. CMデータの取得
3. インドア対策局のフィルタ
4. 対策バンドによるフィルタ
5. ESG作成
6. ホワイトリスト局のフィルタ
7. ブラックリスト局のフィルタ
8. 作業データのフィルタ

各設備タイプ（{', '.join(equipment_types)}）に対応した検証項目を作成してください。
"""
        
        try:
            response = self.generate_response(prompt, system_prompt)
            
            try:
                test_items = json.loads(response)
                if isinstance(test_items, list):
                    return test_items
                else:
                    logger.warning("LLM response is not a list, using fallback")
                    return self._generate_fallback_test_items(feature_name, equipment_types)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON, using fallback")
                return self._generate_fallback_test_items(feature_name, equipment_types)
                
        except Exception as e:
            logger.error(f"Test item generation failed: {e}")
            return self._generate_fallback_test_items(feature_name, equipment_types)
    
    def _generate_fallback_test_items(self, feature_name: str, equipment_types: List[str]) -> List[Dict[str, Any]]:
        """フォールバック検証項目生成"""
        base_items = [
            {
                "test_block": "基本機能検証",
                "category": "CMデータの取得",
                "condition_text": f"{feature_name}機能のCMデータ取得成功",
                "expected_count": len(equipment_types),
                "scenarios": [f"{eq}正常動作" for eq in equipment_types]
            },
            {
                "test_block": "異常系検証",
                "category": "CMデータの取得",
                "condition_text": f"{feature_name}機能の異常時動作確認",
                "expected_count": 0,
                "scenarios": [f"{eq}異常データ" for eq in equipment_types]
            }
        ]
        return base_items

# グローバルLLMサービスインスタンス
def get_llm_service(provider: str = "ollama") -> LLMService:
    """LLMサービスインスタンスを取得"""
    return LLMService(provider=provider)
