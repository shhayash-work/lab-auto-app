#!/usr/bin/env python3
"""
Provider Manager

LLMプロバイダーの管理と接続状態の確認を行うモジュール
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, EMBEDDING_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, BEDROCK_MODEL
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProviderStatus(Enum):
    """プロバイダーの状態"""
    AVAILABLE = "available"          # 利用可能
    UNAVAILABLE = "unavailable"      # 設定なし
    CONNECTION_ERROR = "error"       # 接続エラー

@dataclass
class ProviderInfo:
    """プロバイダー情報"""
    name: str
    display_name: str
    status: ProviderStatus
    is_mcp_supported: bool
    model_name: str
    error_message: Optional[str] = None

class ProviderManager:
    """LLMプロバイダー管理クラス"""
    
    def __init__(self):
        self.providers = {}
        self._check_all_providers()
    
    def _check_all_providers(self):
        """全プロバイダーの状態をチェック"""
        # Ollama
        self.providers["ollama"] = self._check_ollama()
        
        # OpenAI
        self.providers["openai"] = self._check_openai()
        
        # Anthropic
        self.providers["anthropic"] = self._check_anthropic()
        
        # AWS Bedrock
        self.providers["bedrock"] = self._check_bedrock()
    
    def _check_ollama(self) -> ProviderInfo:
        """Ollamaの状態をチェック"""
        try:
            import requests
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                # 指定されたモデルが存在するかチェック
                model_exists = any(model.get("name", "").startswith(OLLAMA_MODEL.split(":")[0]) for model in models)
                
                if model_exists:
                    return ProviderInfo(
                        name="ollama",
                        display_name="Ollama (ローカル)",
                        status=ProviderStatus.AVAILABLE,
                        is_mcp_supported=False,
                        model_name=OLLAMA_MODEL
                    )
                else:
                    return ProviderInfo(
                        name="ollama",
                        display_name="Ollama (ローカル)",
                        status=ProviderStatus.CONNECTION_ERROR,
                        is_mcp_supported=False,
                        model_name=OLLAMA_MODEL,
                        error_message=f"モデル {OLLAMA_MODEL} が見つかりません"
                    )
            else:
                return ProviderInfo(
                    name="ollama",
                    display_name="Ollama (ローカル)",
                    status=ProviderStatus.CONNECTION_ERROR,
                    is_mcp_supported=False,
                    model_name=OLLAMA_MODEL,
                    error_message="Ollamaサーバーに接続できません"
                )
        except Exception as e:
            return ProviderInfo(
                name="ollama",
                display_name="Ollama (ローカル)",
                status=ProviderStatus.CONNECTION_ERROR,
                is_mcp_supported=False,
                model_name=OLLAMA_MODEL,
                error_message=f"接続エラー: {str(e)}"
            )
    
    def _check_openai(self) -> ProviderInfo:
        """OpenAIの状態をチェック"""
        if not OPENAI_API_KEY:
            return ProviderInfo(
                name="openai",
                display_name="OpenAI GPT-4o",
                status=ProviderStatus.UNAVAILABLE,
                is_mcp_supported=True,
                model_name=OPENAI_MODEL,
                error_message="OPENAI_API_KEYが設定されていません"
            )
        
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            # 簡単な接続テスト
            models = client.models.list()
            return ProviderInfo(
                name="openai",
                display_name="OpenAI GPT-4o",
                status=ProviderStatus.AVAILABLE,
                is_mcp_supported=True,
                model_name=OPENAI_MODEL
            )
        except Exception as e:
            return ProviderInfo(
                name="openai",
                display_name="OpenAI GPT-4o",
                status=ProviderStatus.CONNECTION_ERROR,
                is_mcp_supported=True,
                model_name=OPENAI_MODEL,
                error_message=f"接続エラー: {str(e)}"
            )
    
    def _check_anthropic(self) -> ProviderInfo:
        """Anthropicの状態をチェック"""
        if not ANTHROPIC_API_KEY:
            return ProviderInfo(
                name="anthropic",
                display_name="Anthropic Claude",
                status=ProviderStatus.UNAVAILABLE,
                is_mcp_supported=True,
                model_name=ANTHROPIC_MODEL,
                error_message="ANTHROPIC_API_KEYが設定されていません"
            )
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            # 簡単な接続テスト（実際にはAPIコールは行わない）
            return ProviderInfo(
                name="anthropic",
                display_name="Anthropic Claude",
                status=ProviderStatus.AVAILABLE,
                is_mcp_supported=True,
                model_name=ANTHROPIC_MODEL
            )
        except Exception as e:
            return ProviderInfo(
                name="anthropic",
                display_name="Anthropic Claude",
                status=ProviderStatus.CONNECTION_ERROR,
                is_mcp_supported=True,
                model_name=ANTHROPIC_MODEL,
                error_message=f"接続エラー: {str(e)}"
            )
    
    def _check_bedrock(self) -> ProviderInfo:
        """AWS Bedrockの状態をチェック"""
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            return ProviderInfo(
                name="bedrock",
                display_name="AWS Bedrock Claude",
                status=ProviderStatus.UNAVAILABLE,
                is_mcp_supported=True,
                model_name=BEDROCK_MODEL,
                error_message="AWS認証情報が設定されていません"
            )
        
        try:
            import boto3
            client = boto3.client(
                'bedrock-runtime',
                region_name='ap-northeast-1',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                aws_session_token=AWS_SESSION_TOKEN
            )
            # 簡単な接続テスト
            return ProviderInfo(
                name="bedrock",
                display_name="AWS Bedrock Claude",
                status=ProviderStatus.AVAILABLE,
                is_mcp_supported=True,
                model_name=BEDROCK_MODEL
            )
        except Exception as e:
            return ProviderInfo(
                name="bedrock",
                display_name="AWS Bedrock Claude",
                status=ProviderStatus.CONNECTION_ERROR,
                is_mcp_supported=True,
                model_name=BEDROCK_MODEL,
                error_message=f"接続エラー: {str(e)}"
            )
    
    def get_available_providers(self) -> List[ProviderInfo]:
        """利用可能なプロバイダーのリストを取得"""
        return [info for info in self.providers.values() if info.status == ProviderStatus.AVAILABLE]
    
    def get_all_providers(self) -> Dict[str, ProviderInfo]:
        """全プロバイダー情報を取得"""
        return self.providers
    
    def get_provider_info(self, provider_name: str) -> Optional[ProviderInfo]:
        """指定されたプロバイダーの情報を取得"""
        return self.providers.get(provider_name)
    
    def is_provider_available(self, provider_name: str) -> bool:
        """プロバイダーが利用可能かチェック"""
        info = self.get_provider_info(provider_name)
        return info is not None and info.status == ProviderStatus.AVAILABLE
    
    def get_default_provider(self) -> Optional[str]:
        """デフォルトプロバイダーを取得（優先順位順）"""
        # 優先順位: AWS Bedrock > OpenAI > Anthropic > Ollama
        priority_order = ["bedrock", "openai", "anthropic", "ollama"]
        
        for provider_name in priority_order:
            if self.is_provider_available(provider_name):
                return provider_name
        
        return None
    
    def get_embedding_provider(self) -> Tuple[str, str]:
        """Embedding用のプロバイダーとモデルを取得"""
        # 現在の実装では常にOllamaのEmbeddingモデルを使用
        # 将来的には各プロバイダー用のEmbeddingモデルを設定可能にする
        return "ollama", EMBEDDING_MODEL
    
    def refresh_providers(self):
        """プロバイダー状態を再チェック"""
        self._check_all_providers()

# グローバルインスタンス
provider_manager = ProviderManager()

def get_provider_manager() -> ProviderManager:
    """プロバイダーマネージャーのインスタンスを取得"""
    return provider_manager
