import os


PLACEHOLDER_VALUE_MARKERS = (
    "your-",
    "sk-your",
    "placeholder",
    "example",
    "changeme",
    "change-me",
)


def is_placeholder_value(value):
    normalized = str(value or "").strip().strip('"').strip("'").lower()
    if not normalized:
        return False
    return any(marker in normalized for marker in PLACEHOLDER_VALUE_MARKERS)


def load_dotenv_files(base_dir):
    for env_path in (base_dir / ".env", base_dir / "backend" / ".env"):
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            current = os.environ.get(key)
            if current is None or (not current.strip() and value.strip()) or (is_placeholder_value(current) and value.strip()):
                os.environ[key] = value


def env_bool(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def first_env(names):
    for name in names:
        value = os.getenv(name)
        if value and not is_placeholder_value(value):
            return value.strip()
    return ""


def env_float(names, default):
    if isinstance(names, str):
        names = [names]
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        try:
            return float(value)
        except ValueError:
            continue
    return default


def env_int(names, default):
    if isinstance(names, str):
        names = [names]
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        try:
            return int(value)
        except ValueError:
            continue
    return default
