#!/usr/bin/env python3
"""
Downloads your contribution calendar (last 12 months) into data/contributions.json.

Local run (PowerShell):
    $env:GH_TOKEN = "your_token_here"
    python scripts/fetch_contributions.py

Never paste the token into a chat or commit it. In GitHub Actions it comes from secrets.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "ShabnamKSoni1502")
TOKEN = os.environ.get("GH_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

if not TOKEN:
    sys.exit("GH_TOKEN is not set. See the comment at the top of this file.")

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
    headers={
        "Authorization": f"bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "profile-cards",
    },
)

with urllib.request.urlopen(req, timeout=30) as resp:
    payload = json.load(resp)

user = (payload.get("data") or {}).get("user")
if payload.get("errors") or not user:
    sys.exit(f"GitHub API error: {json.dumps(payload)[:500]}")

cal = user["contributionsCollection"]["contributionCalendar"]
days = [
    {"date": d["date"], "count": d["contributionCount"]}
    for week in cal["weeks"]
    for d in week["contributionDays"]
]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps({"username": USER, "total": cal["totalContributions"], "days": days}),
    encoding="utf-8",
)
print(f"Saved {len(days)} days, {cal['totalContributions']} contributions -> {OUT}")
