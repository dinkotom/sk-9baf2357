#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stáhne přijaté Komens zprávy + nástěnku a uloží očištěná data do _data/items.json.

Prostředí / GitHub Secrets:
    BAKALARI_BASE_URL   např. https://1zsfm.bakalari.cz/bakaweb
    BAKALARI_USERNAME
    BAKALARI_PASSWORD
"""

import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from bakalari_client import BakalariClient, BakalariError

DAYS_BACK = 30
OUT = "_data/items.json"


def strip_html(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def parse_dt(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def normalize(raw, kind: str, cutoff):
    msgs = raw.get("Messages", raw if isinstance(raw, list) else [])
    out = []
    for m in msgs:
        dt = parse_dt(m.get("SentDate"))
        if cutoff and dt and dt < cutoff:
            continue
        out.append({
            "id": m.get("Id"),
            "kind": kind,
            "sent": m.get("SentDate"),
            "sent_label": dt.strftime("%-d.%-m. %H:%M") if dt else (m.get("SentDate") or ""),
            "sender": (m.get("Sender") or {}).get("Name"),
            "title": (m.get("Title") or "").strip(),
            "text": strip_html(m.get("Text") or ""),
            "read": bool(m.get("Read")),
            "attachments": [a.get("Name") for a in (m.get("Attachments") or []) if a.get("Name")],
        })
    return out


def get_dismissed_ids():
    """Načte seznam „vyřízených" ID ze stavového Workeru (pokud je nakonfigurován)."""
    api_url = os.getenv("STATE_API_URL")
    api_secret = os.getenv("STATE_API_SECRET")
    if not (api_url and api_secret):
        return []
    try:
        req = urllib.request.Request(
            api_url.rstrip("/") + "/state",
            headers={"Authorization": f"Bearer {api_secret}"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return [str(x) for x in (json.loads(r.read().decode()).get("dismissed") or [])]
    except Exception as e:
        print(f"VAROVÁNÍ: nepodařilo se načíst vyřízené ze stavu: {e}", file=sys.stderr)
        return []


def main():
    base = os.getenv("BAKALARI_BASE_URL")
    user = os.getenv("BAKALARI_USERNAME")
    pw = os.getenv("BAKALARI_PASSWORD")
    if not (base and user and pw):
        sys.exit("Chybí BAKALARI_BASE_URL / BAKALARI_USERNAME / BAKALARI_PASSWORD.")

    cutoff = datetime.now(timezone.utc).astimezone() - timedelta(days=DAYS_BACK)
    c = BakalariClient(base, user, pw)

    try:
        who = c.user_info()
        student = who.get("FullName") or who.get("UserName") or ""
    except BakalariError as e:
        sys.exit(f"Přihlášení/uživatel selhalo: {e}")

    received = normalize(c.received_messages(), "message", cutoff)
    noticeboard = normalize(c.noticeboard(), "noticeboard", None)

    # nejnovější nahoře
    received.sort(key=lambda x: x["sent"] or "", reverse=True)
    noticeboard.sort(key=lambda x: x["sent"] or "", reverse=True)

    dismissed_ids = get_dismissed_ids()

    ts = datetime.now().strftime("%-d.%-m.%Y %H:%M")
    data = {
        "ts": ts,
        "student": student,
        "unread_count": sum(1 for m in received if not m["read"]),
        "dismissed_ids": dismissed_ids,
        "received": received,
        "noticeboard": noticeboard,
    }
    os.makedirs("_data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Staženo: {len(received)} zpráv ({data['unread_count']} nepřečtených), "
          f"{len(noticeboard)} na nástěnce, {len(dismissed_ids)} vyřízených. "
          f"Žák: {student}", file=sys.stderr)


if __name__ == "__main__":
    main()
