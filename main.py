# main.py
# クリーンアーキテクチャに準拠した統合アプリケーションのエントリーポイント。
# すべての実装ロジックは app/ 配下にリファクタリングされました。

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
