"""Validazione offline della config GraphRAG (Tappa 3C): nessuna chiamata di rete.

Carica `grag/settings.yaml` col loader di GraphRAG, verifica l'interpolazione
delle env (`${...}` da `grag/.env`) e che i ModelConfig azure siano validi.
"""
from pathlib import Path

from graphrag.config.load_config import load_config

cfg = load_config(Path("03-graphrag/grag"))
cm = cfg.completion_models["default_completion_model"]
em = cfg.embedding_models["default_embedding_model"]

for tag, m in [("CHAT", cm), ("EMBED", em)]:
    k = m.api_key or ""
    base = m.api_base or ""
    print(f"{tag}: provider={m.model_provider} model={m.model} deployment={m.azure_deployment_name}")
    print(f"   api_base_interpolated={base.startswith('https://')} api_version={m.api_version}")
    print(f"   key_interpolated={not k.startswith('$')} key_len={len(k)}")
    print(f"   metrics.writer={m.metrics.writer} base_dir={m.metrics.base_dir}")

print(f"INPUT: type={cfg.input.type} file_pattern={cfg.input.file_pattern!r}")
print("CONFIG OK")
