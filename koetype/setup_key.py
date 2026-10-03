"""Groq APIキーを登録する（入力は画面に表示されません）。"""
import getpass

import requests

from .config import ENV_PATH, save_api_key


def main():
    print("Groq APIキーを貼り付けて Enter（https://console.groq.com/keys で無料発行）")
    key = getpass.getpass("GROQ_API_KEY: ").strip()
    if not key:
        print("中止しました")
        return
    r = requests.get("https://api.groq.com/openai/v1/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    if r.status_code != 200:
        print(f"キーの確認に失敗しました（{r.status_code}）。キーをもう一度確認してください。")
        return
    save_api_key(key)
    print(f"OK: キーを確認し、{ENV_PATH} に保存しました。")


if __name__ == "__main__":
    main()
