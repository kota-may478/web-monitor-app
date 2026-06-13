#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# .env の存在確認
if [ ! -f "$ROOT_DIR/.env" ]; then
    echo "⚠️  .env が見つかりません。.env.example からコピーします..."
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo "✅ .env を作成しました。値を入力してから再実行してください。"
    echo "   編集: code $ROOT_DIR/.env"
    exit 1
fi

# バックエンド起動（バックグラウンド）
echo "🚀 バックエンドを起動中 (port 8000)..."
cd "$ROOT_DIR/backend"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# フロントエンド起動（フォアグラウンド）
echo "🚀 フロントエンドを起動中 (port 5173)..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Ctrl+C で両方終了
trap "echo '⏹ 停止中...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

echo ""
echo "✅ 開発サーバーが起動しました"
echo "   フロントエンド: http://localhost:5173"
echo "   バックエンドAPI: http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Ctrl+C で停止"

wait
