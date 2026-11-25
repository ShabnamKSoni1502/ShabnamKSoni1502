#!/usr/bin/env python3
"""
Pulls live info from GitHub so the cards update themselves:
  - public repo count, stars, and each listed repo's description + topics -> data/repos.json
  - optional tile numbers read from a JSON file in a repo ("metric" in config.json) -> data/metrics.json

Local run (PowerShell):  $env:GH_TOKEN="..."; python scripts/fetch_repos.py
Works without a token for public data (just rate-limited).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
USER = os.environ.get("GH_USER", CONFIG.get("username", "ShabnamKSoni1502"))
TOKEN = os.environ.get("GH_TOKEN")


def get_json(url, auth=True):
    headers = {"User-Agent": "profile-cards", "Accept": "application/vnd.github+json"}
    if TOKEN and auth:
        headers["Authorization"] = f"bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def repos():
    found = []
    for page in (1, 2, 3):
        batch = get_json(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}")
        found += batch
        if len(batch) < 100:
            break
    mine = [r for r in found if not r["fork"] and r["name"].lower() != USER.lower()]
    out = {
        "public_repos": len(mine),
        "stars": sum(r["stargazers_count"] for r in mine),
        "repos": {
            r["full_name"].lower(): {
                "description": r.get("description") or "",
                "topics": r.get("topics") or [],
                "language": r.get("language") or "",
            }
            for r in found
        },
    }
    (DATA / "repos.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"repos.json: {out['public_repos']} public repos, {out['stars']} stars")


def metrics():
    f = DATA / "metrics.json"
    saved = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    for t in CONFIG["tiles"]:
        m = t.get("metric")
        if not m:
            continue
        try:
            value = get_json(m["url"], auth=False)
            for key in m["key"].split("/"):
                value = value[key]
            saved[t["file"]] = m.get("format", "{}").format(value)
            print(f"metric {t['file']}: {saved[t['file']]}")
        except Exception as e:            # keep the last good value
            print(f"metric {t['file']} skipped: {e}")
    f.write_text(json.dumps(saved), encoding="utf-8")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    try:
        repos()
    except Exception as e:
        sys.exit(f"Could not fetch repos: {e}")
    metrics()
