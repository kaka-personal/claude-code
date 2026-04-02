import json
import os
import sys
import urllib.error
import urllib.request


def post_json(url: str, headers: dict[str, str], body: dict) -> tuple[int | None, str]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def get_text(url: str, headers: dict[str, str]) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def shorten(text: str, limit: int = 800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...<truncated>..."


def main() -> int:
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "http://127.0.0.1:8045").rstrip("/")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    model = os.environ.get("TEST_MODEL", "claude-sonnet-4-6")

    if not api_key:
        print("Missing ANTHROPIC_API_KEY")
        return 1

    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print()

    common_headers = {
        "Authorization": f"Bearer {api_key}",
    }

    print("== 1. GET /v1/models ==")
    status, body = get_text(f"{base_url}/v1/models", common_headers)
    print(f"status: {status}")
    print(shorten(body))
    print()

    print("== 2. POST /v1/chat/completions (OpenAI compatible) ==")
    status, body = post_json(
        f"{base_url}/v1/chat/completions",
        {
            **common_headers,
            "Content-Type": "application/json",
        },
        {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, reply with OK only."}],
        },
    )
    print(f"status: {status}")
    print(shorten(body))
    print()

    print("== 3. POST /v1/messages (Anthropic native) ==")
    status, body = post_json(
        f"{base_url}/v1/messages",
        {
            **common_headers,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        {
            "model": model,
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "Hello, reply with OK only."}],
        },
    )
    print(f"status: {status}")
    print(shorten(body))
    print()

    print("== 4. Conclusion ==")
    if status == 200:
        print("Anthropic native API works. This proxy is likely compatible enough for this repo.")
    else:
        print("Anthropic native API failed or is incompatible. This repo is unlikely to work reliably with this proxy.")
        print("If OpenAI chat.completions works but /v1/messages fails, the proxy is mainly OpenAI-compatible.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
