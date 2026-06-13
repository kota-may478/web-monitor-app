FROM python:3.11-slim

WORKDIR /app

# 依存関係を先にコピー（キャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート8000でuvicornを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
