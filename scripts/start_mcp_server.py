#!/usr/bin/env python3
"""
MCP Server Startup Script

Lab Validation MCP Serverを起動するためのスクリプト
"""

import sys
import os
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 環境変数設定
os.environ["PYTHONPATH"] = str(project_root)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """MCPサーバーを起動"""
    try:
        logger.info("Lab Validation MCP Server を起動中...")
        
        # MCPサーバーをインポートして起動
        from app.services.mcp_server import main as mcp_main
        mcp_main()
        
    except KeyboardInterrupt:
        logger.info("MCPサーバーを停止中...")
    except Exception as e:
        logger.error(f"MCPサーバー起動エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
