#!/bin/bash
# ラボ検証自動化システム起動スクリプト
# Lab Validation Automation System Startup Script

set -e

# 初期化オプションの処理
if [ "$1" = "--reset-user-data" ]; then
    echo "ユーザー作成データを初期化中..."
    echo "Initializing user-created data..."
    
    # プロジェクトディレクトリに移動
    cd "$(dirname "$0")"
    
    # 仮想環境をアクティベート
    source venv/bin/activate
    
    # 環境変数を設定
    export PYTHONPATH="$(pwd)"
    
    # ユーザーデータ削除スクリプトを実行
    python -c "
from app.services.batch_storage import get_batch_storage
from app.config.dummy_data import initialize_dummy_data

print('ユーザー作成データを削除中...')
batch_storage = get_batch_storage()
batch_storage.delete_user_data()

print('ダミーデータを再初期化中...')
initialize_dummy_data()

print('✅ ユーザーデータの初期化が完了しました')
print('✅ ダミーデータは保持されています')
"
    echo ""
    echo "初期化完了！アプリケーションを起動してください："
    echo "  ./start_app.sh"
    exit 0
fi

echo "ラボ検証自動化システムを起動中..."
echo "Lab Validation Automation System Starting..."

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境をアクティベート
echo "仮想環境をアクティベート中..."
source venv/bin/activate

# 環境変数を設定
export PYTHONPATH="$(pwd)"

# ダミーデータ初期化（初回起動時）
echo "ダミーデータを確認中..."
python -c "
from app.config.dummy_data import initialize_dummy_data
initialize_dummy_data()
"

# ポート確認
PORT=8503
echo "ポート $PORT で起動します..."

# Streamlitアプリを起動
echo "Streamlitアプリケーションを起動中..."
echo ""
echo "ブラウザで以下のURLにアクセスしてください:"
echo "http://localhost:$PORT"
echo ""
echo "📝 使用方法:"
echo "  - ユーザーデータを初期化: ./start_app.sh --reset-user-data"
echo "  - 通常起動: ./start_app.sh"
echo ""
echo "アプリケーションを停止するには Ctrl+C を押してください"
echo ""

streamlit run app/main.py --server.port $PORT --server.address 0.0.0.0
