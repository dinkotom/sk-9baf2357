#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vytvoří AI digest přes `claude -p` — ale JEN když se zprávy oproti minulu změnily.

Spočítá otisk (podpis) relevantních zpráv (přijaté + nástěnka + seznam vyřízených).
Pokud je shodný s minulým během (stav v _data/digest_state.json, který se přenáší
přes cache GitHub Actions), Claude se NEVOLÁ a použije se uložený digest.
Když nejsou žádné zprávy, Claude se taky nevolá.

Vstup:  _data/items.json (z fetch_messages.py), prompt.md
Výstup: _data/digest.md a aktualizovaný _data/digest_state.json
Env:    CLAUDE_CODE_OAUTH_TOKEN (pro `claude -p`)
"""

import hashlib
import json
import os
import subprocess
import sys

ITEMS = "_data/items.json"
STATE = "_data/digest_state.json"
DIGEST = "_data/digest.md"


def signature(data):
    recv = sorted(str(m.get("id")) for m in data.get("received", []))
    notice = sorted(str(m.get("id")) for m in data.get("noticeboard", []))
    dismissed = sorted(str(x) for x in data.get("dismissed_ids", []))
    blob = json.dumps([recv, notice, dismissed], ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(sig, digest):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"sig": sig, "digest": digest}, f, ensure_ascii=False)


def write_digest(text):
    with open(DIGEST, "w", encoding="utf-8") as f:
        f.write(text or "")


def run_claude(items_text):
    with open("prompt.md", encoding="utf-8") as f:
        prompt = f.read()
    proc = subprocess.run(
        ["claude", "-p", prompt],
        input=items_text, capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        print(f"VAROVÁNÍ: claude selhal (rc={proc.returncode}): {proc.stderr[:300]}", file=sys.stderr)
        return None
    return proc.stdout.strip()


def main():
    with open(ITEMS, encoding="utf-8") as f:
        items_text = f.read()
    data = json.loads(items_text)

    n_recv = len(data.get("received", []))
    n_notice = len(data.get("noticeboard", []))

    # Žádné zprávy → nevoláme Claude vůbec.
    if n_recv == 0 and n_notice == 0:
        print("Žádné zprávy ani nástěnka – Claude se nevolá.", file=sys.stderr)
        write_digest("")
        save_state(signature(data), "")
        return

    sig = signature(data)
    prev = load_state()

    # Nic nového oproti minulu → použijeme uložený digest, Claude se nevolá.
    if prev.get("sig") == sig and prev.get("digest") is not None:
        print("Beze změny od posledního běhu – Claude se nevolá, použit uložený digest.", file=sys.stderr)
        write_digest(prev["digest"])
        return

    # Něco se změnilo → zavoláme Claude.
    if not os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        print("CLAUDE_CODE_OAUTH_TOKEN chybí – stránka bude bez AI digestu.", file=sys.stderr)
        write_digest(prev.get("digest", ""))
        return

    print("Změna ve zprávách – generuji nový digest přes Claude.", file=sys.stderr)
    digest = run_claude(items_text)
    if digest is None:
        # selhání – raději ponecháme předchozí digest, než žádný
        write_digest(prev.get("digest", ""))
        return
    write_digest(digest)
    save_state(sig, digest)


if __name__ == "__main__":
    main()
