# env_file: reads API keys from a .env file (KEY=value lines) into the environment, so the
# AI libraries can find them. Keys already set in the environment are left alone.
import os


def load_env(path):
    # returns the names that were loaded (never the values); a missing file is fine
    loaded = []
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return loaded
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = (part.strip() for part in line.split('=', 1))
        value = value.strip('"').strip("'")
        if value and name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded
