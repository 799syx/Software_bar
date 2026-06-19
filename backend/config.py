import os


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
            if key and key not in os.environ:
                os.environ[key] = value


def env_bool(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def first_env(names):
    for name in names:
        value = os.getenv(name)
        if value:
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
