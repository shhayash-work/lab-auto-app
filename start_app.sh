#!/bin/bash
# ラボ検証自動化システム起動スクリプト
# Lab Validation Automation System Startup Script

set -e

echo "ラボ検証自動化システムを起動中..."
echo "Lab Validation Automation System Starting..."

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境をアクティベート
echo "仮想環境をアクティベート中..."
source venv/bin/activate

# 環境変数を設定
export PYTHONPATH="$(pwd)"

# ポート確認
PORT=8503
echo "ポート $PORT で起動します..."

# Streamlitアプリを起動
echo "Streamlitアプリケーションを起動中..."
echo ""
echo "ブラウザで以下のURLにアクセスしてください:"
echo "http://localhost:$PORT"
echo ""
echo "アプリケーションを停止するには Ctrl+C を押してください"
echo ""

streamlit run app/main.py --server.port $PORT --server.address 0.0.0.0
