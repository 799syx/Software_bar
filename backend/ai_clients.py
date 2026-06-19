import json
import socket
import time
import urllib.error
import urllib.request


def chat_completions_url(base_url):
    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url.rstrip('/')}/chat/completions"


def call_openai_compatible_llm(messages, config, retry_count=2):
    if not config["available"]:
        return None
    retry_count = max(1, int(retry_count or 1))
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": config["temperature"],
        "max_tokens": config["maxTokens"],
        "stream": False,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if config["apiKey"]:
        headers["Authorization"] = f"Bearer {config['apiKey']}"
    request = urllib.request.Request(chat_completions_url(config["baseUrl"]), data=body, headers=headers, method="POST")
    last_error = None
    for attempt in range(retry_count):
        try:
            with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            last_error = RuntimeError(f"大模型接口返回 {exc.code}: {detail[:220]}")
            if exc.code < 500 and exc.code != 429:
                raise last_error from exc
        except (urllib.error.URLError, TimeoutError, OSError, socket.timeout) as exc:
            last_error = RuntimeError(f"大模型服务不可用或超时：{exc}")
        if attempt < retry_count - 1:
            time.sleep(0.5 * (attempt + 1))
    else:
        raise last_error or RuntimeError("大模型服务调用失败")
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    content = str(content).strip()
    if not content:
        raise RuntimeError("大模型未返回有效内容")
    return {
        "content": content,
        "provider": config["provider"],
        "model": config["model"],
        "usage": data.get("usage") or {},
        "finishReason": choice.get("finish_reason", ""),
    }
