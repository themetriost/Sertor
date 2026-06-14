"""Connectivity check per i provider di embedding (Ollama + Azure OpenAI v1).

Legge i valori da `.env` nella root del progetto. Stampa solo esito e dimensione
del vettore: NON stampa mai la API key. Usa solo la stdlib (eseguibile con `python -S`).
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
SAMPLE = "def add(a, b): return a + b"


def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def post_json(url: str, headers: dict, payload: dict, timeout: int = 30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def check_ollama(env: dict) -> None:
    host = env.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = env.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    try:
        _, body = post_json(f"{host}/api/embed", {}, {"model": model, "input": SAMPLE})
        dim = len(body.get("embeddings", [[]])[0])
        print(f"[Ollama/{model}] OK  dim={dim}")
    except Exception as e:  # noqa: BLE001
        print(f"[Ollama/{model}] FAIL  {type(e).__name__}: {e}")


def check_azure(env: dict, deployment: str, label: str) -> None:
    endpoint = env.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    key = env.get("AZURE_OPENAI_API_KEY", "")
    if not (endpoint and key and deployment):
        print(f"[Azure/{label}] SKIP  (endpoint/key/deployment mancante)")
        return
    url = f"{endpoint}/embeddings"
    payload = {"model": deployment, "input": SAMPLE}
    for auth in ({"api-key": key}, {"Authorization": f"Bearer {key}"}):
        scheme = "api-key" if "api-key" in auth else "bearer"
        try:
            _, body = post_json(url, auth, payload)
            dim = len(body["data"][0]["embedding"])
            print(f"[Azure/{label}:{deployment}] OK  dim={dim}  (auth={scheme})")
            return
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                continue  # prova lo schema di auth successivo
            msg = e.read().decode("utf-8", "ignore")[:200]
            print(f"[Azure/{label}:{deployment}] FAIL  HTTP {e.code}  {msg}")
            return
        except Exception as e:  # noqa: BLE001
            print(f"[Azure/{label}:{deployment}] FAIL  {type(e).__name__}: {e}")
            return
    print(f"[Azure/{label}:{deployment}] FAIL  401/403 con api-key e Bearer")


def main() -> None:
    env = load_env(ENV)
    check_ollama(env)
    check_azure(env, env.get("AZURE_OPENAI_EMBED_SMALL_DEPLOYMENT", ""), "small")
    check_azure(env, env.get("AZURE_OPENAI_EMBED_LARGE_DEPLOYMENT", ""), "large")


if __name__ == "__main__":
    main()
