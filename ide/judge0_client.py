import requests
from django.conf import settings

# Slug → Judge0 CE language id. Slugs match Monaco editor language IDs so the
# editor highlights correctly without any translation layer.
LANGUAGE_IDS = {
    "python": 71,        # Python 3.8.1
    "javascript": 63,    # JavaScript (Node.js 12.14)
    "typescript": 74,    # TypeScript 3.7.4
    "java": 62,          # Java (OpenJDK 13.0.1)
    "c": 50,             # C (GCC 9.2)
    "cpp": 54,           # C++ (GCC 9.2)
    "csharp": 51,        # C# (Mono 6.6)
    "go": 60,            # Go 1.13.5
    "rust": 73,          # Rust 1.40
    "ruby": 72,          # Ruby 2.7
    "php": 68,           # PHP 7.4
    "kotlin": 78,        # Kotlin 1.3
    "swift": 83,         # Swift 5.2.3
    "shell": 46,         # Bash 5.0
    "sql": 82,           # SQL (SQLite 3.27)
    "r": 80,             # R 4.0
    "lua": 64,           # Lua 5.3
}


class Judge0Error(Exception):
    pass


def submit_code(source_code, language, stdin="", time_limit=5, memory_limit=256000):
    api_url = settings.JUDGE0_API_URL
    api_key = getattr(settings, "JUDGE0_API_KEY", "")
    language_id = LANGUAGE_IDS.get(language)
    if not language_id:
        raise Judge0Error(f"Unsupported language: {language}")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Auth-Token"] = api_key
    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
        "cpu_time_limit": time_limit,
        "memory_limit": memory_limit,
        "wall_time_limit": time_limit * 2,
    }
    try:
        resp = requests.post(
            f"{api_url}/submissions/?base64_encoded=false&wait=true",
            json=payload,
            headers=headers,
            timeout=time_limit * 3 + 10,
        )
        resp.raise_for_status()
    except Exception as e:
        raise Judge0Error(f"Judge0 request failed: {e}")
    return resp.json()
