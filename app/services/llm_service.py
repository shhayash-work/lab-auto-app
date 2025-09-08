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
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_REGION, BEDROCK_MODEL
)
# knowledge_serviceは遅延ロードで使用

logger = logging.getLogger(__name__)

class LLMService:
    """LLMサービスクラス"""
    
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self.client = None
        
        # knowledge_service（遅延ロード）
        self._knowledge_service = None
        self._setup_client()
    
    def _get_knowledge_service(self):
        """knowledge_serviceを遅延ロード"""
        if self._knowledge_service is None:
            try:
                from app.services.knowledge_service import get_knowledge_service
                self._knowledge_service = get_knowledge_service()
            except Exception as e:
                logger.warning(f"Knowledge service initialization failed: {e}")
                self._knowledge_service = None
        return self._knowledge_service
    
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
            if hasattr(models, 'models'):
                # Pydanticモデルの場合
                available_models = []
                for model in models.models:
                    if hasattr(model, 'name'):
                        available_models.append(model.name)
                    elif hasattr(model, 'model'):
                        available_models.append(model.model)
                    elif isinstance(model, dict):
                        available_models.append(model.get('name', model.get('model', '')))
            elif isinstance(models, dict):
                available_models = [model.get('name', '') for model in models.get('models', [])]
            else:
                available_models = []
            
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
        
        # AWS_SESSION_TOKENが設定されている場合は一時的な認証情報を使用
        client_kwargs = {
            'service_name': 'bedrock-runtime',
            'aws_access_key_id': AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
            'region_name': AWS_REGION
        }
        
        # AWS_SESSION_TOKENが設定されている場合（AssumeRole使用時）
        if AWS_SESSION_TOKEN:
            client_kwargs['aws_session_token'] = AWS_SESSION_TOKEN
            logger.info("🔐 Using temporary credentials with session token")
        
        self.client = boto3.client(**client_kwargs)
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
                "num_predict": 2048,  # 元に戻す
                "num_ctx": 10240     # コンテキスト長を拡張
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
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": full_prompt}]
            })
            
            logger.info(f"Bedrock request body: {body[:200]}...")
            
            response = self.client.invoke_model(
                modelId=BEDROCK_MODEL,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            logger.info(f"Bedrock response: {response_body}")
            
            # レスポンス構造を確認
            if 'content' in response_body and response_body['content']:
                return response_body['content'][0]['text']
            elif 'completion' in response_body:
                return response_body['completion']
            else:
                logger.error(f"Unexpected Bedrock response structure: {response_body}")
                raise ValueError(f"Unexpected response structure: {response_body}")
                
        except Exception as e:
            logger.error(f"Bedrock generation error: {e}")
            raise
    
    def _generate_bedrock_streaming(self, prompt: str, system_prompt: Optional[str] = None, progress_callback=None) -> str:
        """AWS Bedrock応答を生成（ストリーミング対応）"""
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": full_prompt}]
            })
            
            logger.info(f"Bedrock streaming request body: {body[:200]}...")
            
            # ストリーミングレスポンスを使用
            response = self.client.invoke_model_with_response_stream(
                modelId=BEDROCK_MODEL,
                body=body
            )
            
            # ストリーミングレスポンスを処理
            full_response = ""
            chunk_count = 0
            total_chunks_estimate = 20  # 推定チャンク数
            
            for event in response['body']:
                if 'chunk' in event:
                    chunk = json.loads(event['chunk']['bytes'].decode())
                    
                    if chunk['type'] == 'content_block_delta':
                        if 'delta' in chunk and 'text' in chunk['delta']:
                            text_chunk = chunk['delta']['text']
                            full_response += text_chunk
                            chunk_count += 1
                            
                            # 進捗とストリーミングテキストを報告
                            progress = min(chunk_count / total_chunks_estimate, 0.95)
                            if progress_callback:
                                progress_callback(progress, text_chunk)
                    
                    elif chunk['type'] == 'message_stop':
                        # 完了
                        if progress_callback:
                            progress_callback(1.0, "応答完了")
                        break
            
            logger.info(f"Bedrock streaming response completed: {len(full_response)} chars")
            return full_response
            
        except Exception as e:
            logger.error(f"Bedrock streaming generation error: {e}")
            # フォールバック: 通常のAPI呼び出し
            logger.info("Falling back to non-streaming Bedrock API")
            return self._generate_bedrock(prompt, system_prompt)
    
    def analyze_validation_result(self, test_item: Dict[str, Any], equipment_response: Dict[str, Any]) -> Dict[str, Any]:
        """検証結果を分析"""
        system_prompt = """あなたは通信設備の検証エキスパートです。
基地局設備からの応答データを分析し、テスト項目の判定を行ってください。

判定基準:
- PASS: 期待される動作が正常に実行され、すべての条件を満たしている
- FAIL: 期待される動作が実行されない、または明確に条件を満たしていない
- NEEDS_CHECK: 結果が曖昧、予期しない値、または判断に迷う場合

応答は必ずJSON形式で以下の構造にしてください:
{
    "result": "PASS|FAIL|NEEDS_CHECK",
    "confidence": 0.0-1.0,
    "analysis": "詳細な分析内容",
    "issues": ["問題点のリスト"],
    "recommendations": ["推奨事項のリスト"]
}"""
        
        prompt = f"""
テスト項目:
- カテゴリ: {test_item.get('category', 'N/A')}
- 条件: {test_item.get('condition', {}).get('condition_text', 'N/A')}

設備応答データ:
{json.dumps(equipment_response, ensure_ascii=False, indent=2)}

この応答データを分析し、テスト項目の合格/不合格を判定してください。
"""
        
        try:
            response = self.generate_response(prompt, system_prompt)
            
            # JSONパースを試行（レスポンスからJSONを抽出）
            try:
                # まず直接JSONパースを試行
                result = json.loads(response)
            except json.JSONDecodeError:
                # 失敗した場合、レスポンスからJSONを抽出
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse extracted JSON: {e}")
                        logger.error(f"Extracted JSON: {json_str}")
                        raise ValueError(f"LLM returned invalid JSON: {str(e)}")
                else:
                    logger.error(f"No JSON found in response: {response}")
                    raise ValueError("No JSON found in LLM response")
            
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
                
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            raise
    
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
    
    
    def generate_test_items(self, feature_name: str, equipment_types: List[str], progress_callback=None) -> List[Dict[str, Any]]:
        """検証項目を生成（知見学習機能付き）"""
        
        # 知見学習によるプロンプト強化
        base_system_prompt = """あなたは通信設備の検証エキスパートです。
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
        "condition_text": "検証条件の詳細"
    }
]

検証条件は対象設備での成功・失敗を判定するための具体的な条件を記述してください。"""
        
        # 知見学習機能による強化
        enhanced_system_prompt = base_system_prompt
        knowledge_service = self._get_knowledge_service()
        if knowledge_service:
            try:
                enhanced_system_prompt = knowledge_service.enhance_item_generation_prompt(
                    base_system_prompt, feature_name, equipment_types
                )
            except Exception as e:
                logger.warning(f"Knowledge enhancement failed: {e}")
        
        system_prompt = enhanced_system_prompt
        
        # RAGベクターDBから関連する過去の検証項目を検索
        if progress_callback:
            progress_callback(0.5, "RAGベクターDBから類似検証項目を検索中...")
        rag_context = self._search_similar_test_items(feature_name, equipment_types)
        
        prompt = f"""
機能名: {feature_name}
対象設備: {', '.join(equipment_types)}

【過去の類似検証項目（RAG検索結果）】
{rag_context}

上記の過去の検証項目を参考に、新しい機能「{feature_name}」について包括的な検証項目を生成してください。
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
            if progress_callback:
                progress_callback(0.7, f"{self.provider.upper()} AIエージェントが検証項目を生成中...")
            
            # Bedrockの場合はストリーミング対応
            if self.provider == "bedrock":
                response = self._generate_bedrock_streaming(prompt, system_prompt, progress_callback)
            else:
                response = self.generate_response(prompt, system_prompt)
                if progress_callback:
                    progress_callback(0.9, "生成された検証項目を解析中...")
            
            try:
                test_items = json.loads(response)
                if isinstance(test_items, list):
                    logger.info(f"Generated {len(test_items)} test items using RAG")
                    
                    if progress_callback:
                        progress_callback(1.0, f"検証項目生成完了: {len(test_items)}件")
                    
                    return test_items
                else:
                    logger.error("LLM response is not a list")
                    raise ValueError("LLM returned invalid format (not a list)")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                raise ValueError(f"LLM returned invalid JSON: {str(e)}")
                
        except Exception as e:
            logger.error(f"Test item generation failed: {e}")
            if progress_callback:
                progress_callback(1.0, f"生成エラー: {str(e)}")
            raise
    
    def _search_similar_test_items(self, feature_name: str, equipment_types: List[str]) -> str:
        """RAGベクターDBから類似する検証項目を検索"""
        try:
            from app.services.vector_store import get_vector_store
            
            # 検索クエリを作成
            query = f"{feature_name} {' '.join(equipment_types)} 検証項目"
            
            # ベクターDBから類似項目を検索
            vector_store = get_vector_store()
            similar_items = vector_store.search_similar_documents(query, top_k=5)
            
            if similar_items:
                context = "過去の類似検証項目:\n"
                for i, item in enumerate(similar_items, 1):
                    context += f"{i}. {item.get('content', '')}\n"
                logger.info(f"Found {len(similar_items)} similar test items from RAG")
                return context
            else:
                logger.info("No similar test items found in RAG")
                return "過去の類似検証項目は見つかりませんでした。"
                
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")
            return "RAG検索でエラーが発生しました。基本的な検証項目を生成します。"
    

# グローバルLLMサービスインスタンス
def get_llm_service(provider: str = "ollama") -> LLMService:
    """LLMサービスインスタンスを取得"""
    return LLMService(provider=provider)
