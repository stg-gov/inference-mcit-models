#!/usr/bin/env python3
"""Let existing virtual keys call every model in the gateway config."""

import json
import os
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT, ".env")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")


def load_env(path):
    values = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    return values


def models_from_config(path):
    names = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("model_name:"):
                names.append(stripped.split(":", 1)[1].strip())
    return names


def request(method, path, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:4000" + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise SystemExit(f"{method} {path} failed ({error.code}): {detail}") from error


def main():
    env = load_env(ENV_PATH)
    master = env["LITELLM_MASTER_KEY"]
    models = models_from_config(CONFIG_PATH)
    listed = request("GET", "/key/list", master)
    updated = 0
    for token in listed.get("keys", []):
        if not isinstance(token, str):
            continue
        request("POST", "/key/update", master, {"key": token, "models": models})
        updated += 1
    print(f"Updated {updated} key(s) for: {', '.join(models)}")


if __name__ == "__main__":
    main()
