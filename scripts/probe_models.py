import json
import os
import sys
import time
import urllib.error
import urllib.request


def get_text(url: str, headers: dict[str, str], timeout: int = 30) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def post_json(
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout: int = 60,
) -> tuple[int | None, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def parse_models(body: str) -> list[str]:
    data = json.loads(body)
    models = []
    for item in data.get("data", []):
        model_id = item.get("id")
        if isinstance(model_id, str) and model_id:
            models.append(model_id)
    return models


def supports_messages_api(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    status, body = post_json(
        f"{base_url}/v1/messages",
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        {
            "model": model,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Reply with OK only."}],
        },
    )
    if status == 200:
        return True, "ok"
    compact = " ".join(body.strip().split())
    return False, f"{status}: {compact[:180]}"


def main() -> int:
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "http://127.0.0.1:8045").rstrip("/")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    limit = int(os.environ.get("PROBE_LIMIT", "0") or "0")
    delay = float(os.environ.get("PROBE_DELAY", "0.2") or "0.2")
    name_filter = os.environ.get("PROBE_FILTER", "").strip().lower()

    if not api_key:
        print("Missing ANTHROPIC_API_KEY")
        return 1

    status, body = get_text(
        f"{base_url}/v1/models",
        {"Authorization": f"Bearer {api_key}"},
    )
    if status != 200:
        print(f"Failed to fetch /v1/models: {status}")
        print(body)
        return 1

    models = parse_models(body)
    if name_filter:
        models = [m for m in models if name_filter in m.lower()]
    if limit > 0:
        models = models[:limit]

    print(f"Base URL: {base_url}")
    print(f"Total models to probe: {len(models)}")
    print("Protocol: Anthropic /v1/messages")
    print()

    supported: list[str] = []
    failed: list[tuple[str, str]] = []

    for index, model in enumerate(models, start=1):
        ok, detail = supports_messages_api(base_url, api_key, model)
        label = "OK" if ok else "FAIL"
        print(f"[{index}/{len(models)}] {label:<4} {model}  {detail}")
        if ok:
            supported.append(model)
        else:
            failed.append((model, detail))
        if delay > 0 and index < len(models):
            time.sleep(delay)

    print()
    print("=== Supported Models ===")
    for model in supported:
        print(model)

    print()
    print(f"Supported: {len(supported)} / {len(models)}")
    if failed:
        print("Failed sample:")
        for model, detail in failed[:10]:
            print(f"- {model}: {detail}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
