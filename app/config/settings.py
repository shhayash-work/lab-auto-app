"""
アプリケーション設定
Application Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent

# アプリケーション基本設定
APP_NAME = os.getenv("APP_NAME", "ラボ検証自動化システム")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# データベース設定
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/lab_validation.db")

# LLM設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://0.0.0.0:6081")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3:latest")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large:latest")

# オプショナルLLM設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")

# モック設備設定
MOCK_EQUIPMENT_HOST = os.getenv("MOCK_EQUIPMENT_HOST", "localhost")
MOCK_EQUIPMENT_PORT = int(os.getenv("MOCK_EQUIPMENT_PORT", "8001"))

# 検証設定
DEFAULT_VALIDATION_TIMEOUT = int(os.getenv("DEFAULT_VALIDATION_TIMEOUT", "300"))
MAX_CONCURRENT_VALIDATIONS = int(os.getenv("MAX_CONCURRENT_VALIDATIONS", "5"))

# ディレクトリパス
DATA_DIR = PROJECT_ROOT / "data"
TEST_ITEMS_DIR = DATA_DIR / "test_items"
RESULTS_DIR = DATA_DIR / "results"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"

# ディレクトリを作成
for dir_path in [DATA_DIR, TEST_ITEMS_DIR, RESULTS_DIR, KNOWLEDGE_DIR, VECTOR_STORE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Streamlit設定
STREAMLIT_CONFIG = {
    "page_title": APP_NAME,
    "page_icon": "🔬",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}


