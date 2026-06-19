import json
import re


def sse_event(event, data):
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def chunk_text(text, max_chars=28):
    value = str(text or "")
    if not value:
        return []
    parts = [part for part in re.split(r"(?<=[。！？!?；;，,])", value) if part]
    chunks = []
    for part in parts:
        while len(part) > max_chars:
            chunks.append(part[:max_chars])
            part = part[max_chars:]
        if part:
            chunks.append(part)
    return chunks or [value]
