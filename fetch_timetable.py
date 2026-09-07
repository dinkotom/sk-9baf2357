#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stáhne rozvrhy kluků a uloží očištěná data do _data/timetable.json.

Zdroje:
  * Bakaláři (Ota – Hladnov, Eda – Bezručova): živý rozvrh `timetable/actual`,
    tj. VČETNĚ suplování, odpadlých hodin a změn učeben. Tahá se aktuální
    a příští týden (aby „zítra“ fungovalo i v pátek večer).
  * Čeněk (ScioŠkola): Edookit nemá rodičovské API, rozvrh je statický
    v data/cenek.json a udržuje se ručně.

Prostředí / GitHub Secrets:
    BAKALARI_BASE_URL / BAKALARI_USERNAME / BAKALARI_PASSWORD           (Eda)
    BAKALARI_OTA_BASE_URL / BAKALARI_OTA_USERNAME / BAKALARI_OTA_PASSWORD (Ota)

Chybí-li účet, dítě se do výstupu vloží s příznakem `error` – stránka se
kvůli jednomu nedostupnému rozvrhu nerozbije.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta

from bakalari_client import BakalariClient, BakalariError

OUT = "_data/timetable.json"

# Pořadí zobrazení = od nejstaršího kluka, stejně jako v ranním briefingu.
KIDS = [
    {"key": "ota", "name": "Ota", "school": "Gymnázium Hladnov", "env": "BAKALARI_OTA"},
    {"key": "cenek", "name": "Čeněk", "school": "ScioŠkola FM", "static": "data/cenek.json"},
    {"key": "eda", "name": "Eda", "school": "ZŠ Petra Bezruče", "env": "BAKALARI"},
]

DOW_ABBR = {1: "po", 2: "út", 3: "st", 4: "čt", 5: "pá", 6: "so", 7: "ne"}

# Change.ChangeType → jak to obarvit na stránce
CHANGE_KIND = {
    "Removed": "removed",
    "Canceled": "removed",
    "Substitution": "sub",
    "Added": "added",
    "RoomChanged": "sub",
}


def by_id(items, key="Id"):
    return {i.get(key): i for i in (items or [])}


def day_label(d: date) -> str:
    return f"{DOW_ABBR.get(d.isoweekday(), '')} {d.day}.{d.month}."


def normalize_week(raw: dict) -> list[dict]:
    """Bakalářský týden → seznam dnů s hodinami připravenými k vykreslení."""
    hours = by_id(raw.get("Hours"))
    subjects = by_id(raw.get("Subjects"))
    teachers = by_id(raw.get("Teachers"))
    rooms = by_id(raw.get("Rooms"))
    groups = by_id(raw.get("Groups"))
    # Cycles v odpovědi = cyklus TOHOTO týdne (lichý/sudý). Hodina patřící jen
    # do jiného cyklu se nekoná → vyfiltrovat.
    week_cycles = {c.get("Id") for c in (raw.get("Cycles") or [])}
    class_abbrev = ((raw.get("Classes") or [{}])[0].get("Abbrev") or "").strip()
    cycle_name = ", ".join(c.get("Name") or c.get("Abbrev") or "" for c in (raw.get("Cycles") or []))

    days = []
    for d in raw.get("Days") or []:
        try:
            dt = datetime.fromisoformat(d.get("Date")).date()
        except (TypeError, ValueError):
            continue

        lessons = []
        for a in d.get("Atoms") or []:
            cyc = set(a.get("CycleIds") or [])
            if cyc and week_cycles and not (cyc & week_cycles):
                continue

            h = hours.get(a.get("HourId")) or {}
            ch = a.get("Change") or None
            subj = subjects.get(a.get("SubjectId")) or {}
            teacher = teachers.get(a.get("TeacherId")) or {}
            room = rooms.get(a.get("RoomId")) or {}
            group = groups.get((a.get("GroupIds") or [None])[0]) or {}
            # „1.C“ jako skupina = celá třída → nezobrazovat; „1.C Aj1“ → jen „Aj1“.
            grp = (group.get("Abbrev") or "").strip()
            if class_abbrev and grp == class_abbrev:
                grp = ""
            elif class_abbrev and grp.startswith(class_abbrev):
                grp = grp[len(class_abbrev):].strip()

            kind = CHANGE_KIND.get((ch or {}).get("ChangeType")) if ch else None
            # Atom bez předmětu + změna = hodina vypadla z rozvrhu.
            if not subj and kind is None and ch:
                kind = "removed"

            lessons.append({
                "hour": (h.get("Caption") or "").strip(),
                "from": h.get("BeginTime") or "",
                "to": h.get("EndTime") or "",
                "subject": (subj.get("Name") or "").strip(),
                "abbrev": (subj.get("Abbrev") or "").strip(),
                "teacher": (teacher.get("Name") or "").strip(),
                "room": (room.get("Abbrev") or "").strip(),
                "group": grp,
                "theme": (a.get("Theme") or "").strip(),
                "change": (ch or {}).get("Description") or "",
                "change_kind": kind,
            })

        lessons.sort(key=lambda x: x["from"] and [int(p) for p in x["from"].split(":")] or [0, 0])

        # Odpadlé hodiny na KONCI dne jsou jen šum („škola končí dřív“ je vidět
        # z toho, že tam nic není). Odpadlé na začátku / uvnitř dne se nechávají —
        # to je informace „jde později“ / „má volnou hodinu“.
        while lessons and lessons[-1]["change_kind"] == "removed" and not lessons[-1]["subject"]:
            lessons.pop()

        days.append({
            "date": dt.isoformat(),
            "label": day_label(dt),
            "dow": dt.isoweekday(),
            "cycle": cycle_name,
            "desc": (d.get("DayDescription") or "").strip(),
            "type": d.get("DayType") or "",
            "lessons": lessons,
        })
    return days


def fetch_bakalari(kid: dict) -> dict:
    p = kid["env"]
    base, user, pw = (os.getenv(f"{p}_BASE_URL"), os.getenv(f"{p}_USERNAME"), os.getenv(f"{p}_PASSWORD"))
    if not (base and user and pw):
        return {"error": f"chybí secrets {p}_BASE_URL / _USERNAME / _PASSWORD"}

    c = BakalariClient(base, user, pw)
    today = date.today()
    days, seen = [], set()
    for offset in (0, 7):
        raw = c.timetable_actual((today + timedelta(days=offset)).isoformat())
        for d in normalize_week(raw):
            if d["date"] not in seen:
                seen.add(d["date"])
                days.append(d)

    out = {"days": sorted(days, key=lambda d: d["date"])}
    try:
        who = c.user_info()
        out["student"] = who.get("FullName") or ""
        out["class"] = ((who.get("Class") or {}).get("Abbrev") or "").strip()
    except BakalariError:
        pass
    return out


def load_static(kid: dict) -> dict:
    """Statický týdenní rozvrh (data/*.json) rozbalí na konkrétní dny 2 týdnů."""
    try:
        with open(kid["static"], encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return {"error": f"chybí {kid['static']} – rozvrh není zadaný"}
    except json.JSONDecodeError as e:
        return {"error": f"{kid['static']} není platný JSON: {e}"}

    week = cfg.get("week") or {}
    if not any(week.get(str(i)) for i in range(1, 6)):
        return {"error": "rozvrh není zadaný", "note": cfg.get("note", "")}

    today = date.today()
    monday = today - timedelta(days=today.isoweekday() - 1)
    days = []
    for i in range(14):
        d = monday + timedelta(days=i)
        if d.isoweekday() > 5:
            continue
        lessons = []
        for l in week.get(str(d.isoweekday())) or []:
            lessons.append({
                "hour": str(l.get("hour", "") or ""),
                "from": l.get("from", ""),
                "to": l.get("to", ""),
                "subject": l.get("subject", ""),
                "abbrev": l.get("abbrev", "") or l.get("subject", "")[:6],
                "teacher": l.get("teacher", ""),
                "room": l.get("room", ""),
                "group": "",
                "theme": l.get("note", ""),
                "change": "",
                "change_kind": None,
            })
        days.append({
            "date": d.isoformat(), "label": day_label(d), "dow": d.isoweekday(),
            "cycle": "", "desc": "", "type": "WorkDay", "lessons": lessons,
        })
    return {"days": days, "class": cfg.get("class", ""), "note": cfg.get("note", "")}


def main():
    kids = []
    for kid in KIDS:
        entry = {"key": kid["key"], "name": kid["name"], "school": kid["school"],
                 "source": "static" if kid.get("static") else "bakalari", "days": []}
        try:
            got = load_static(kid) if kid.get("static") else fetch_bakalari(kid)
        except BakalariError as e:
            got = {"error": str(e)}
        entry.update(got)
        if entry.get("error"):
            print(f"VAROVÁNÍ [{kid['name']}]: {entry['error']}", file=sys.stderr)
        else:
            n = sum(len(d["lessons"]) for d in entry["days"])
            print(f"{kid['name']}: {len(entry['days'])} dnů, {n} hodin", file=sys.stderr)
        kids.append(entry)

    data = {
        "ts": datetime.now().strftime("%-d.%-m.%Y %H:%M"),
        "today": date.today().isoformat(),
        "kids": kids,
    }
    os.makedirs("_data", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
