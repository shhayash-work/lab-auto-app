#!/usr/bin/env python3
"""
ラボ検証自動化システム起動スクリプト
Lab Validation Automation System Launcher
"""
import sys
import os
from pathlib import Path

# プロジェクトルートを設定
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ['PYTHONPATH'] = str(project_root)

# Streamlitアプリを起動
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    # Streamlitアプリのパス
    app_path = project_root / "app" / "main.py"
    
    # Streamlit実行
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ]
    
    stcli.main()


