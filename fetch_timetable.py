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
    {"key": "ota", "name": "Ota", "school": "Gymnázium Hladnov", "env": "BAKALARI_OTA",
     "snapshot": "data/ota_zaloha.json"},
    {"key": "cenek", "name": "Čeněk", "school": "ScioŠkola FM", "static": "data/cenek.json"},
    {"key": "eda", "name": "Eda", "school": "ZŠ Petra Bezruče", "env": "BAKALARI",
     "snapshot": "data/eda_zaloha.json"},
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


def _slot_key(l):
    return (l.get("from") or "", l.get("subject") or "")


def save_snapshot(kid: dict, got: dict) -> None:
    """Udržuje zálohu rozvrhu z posledních úspěšných stažení.

    Ukládají se jen STABILNÍ hodiny (bez suplování / přesunu) — jednorázové
    změny nejsou rozvrh. Protože týden plný suplování by dal děravou zálohu,
    data se KUMULUJÍ: slot, který se tentokrát nestáhl čistě, si podrží dřívější
    hodnotu. Drží se zvlášť pro každý cyklus (sudý/lichý týden).
    """
    path = kid.get("snapshot")
    if not path:
        return

    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
    except (OSError, json.JSONDecodeError):
        snap = {}
    by_cycle = snap.get("by_cycle") or {}

    for d in got.get("days") or []:
        cycle = d.get("cycle") or "-"
        stable = [
            {k: l.get(k, "") for k in ("hour", "from", "to", "subject", "abbrev", "teacher", "room")}
            for l in d["lessons"] if not l.get("change_kind") and l.get("subject")
        ]
        if not stable:
            continue
        bucket = by_cycle.setdefault(cycle, {"week": {}, "captured": {}})
        dow = str(d["dow"])
        merged = {_slot_key(l): l for l in bucket["week"].get(dow, [])}
        merged.update({_slot_key(l): l for l in stable})
        bucket["week"][dow] = sorted(
            merged.values(),
            key=lambda l: [int(x) for x in (l["from"] or "0:0").split(":")],
        )
        bucket["captured"][dow] = d["date"]

    if not by_cycle:
        return
    payload = {
        "_generated": "Automatická záloha z úspěšných stažení Bakalářů. Needituj ručně.",
        "class": got.get("class", "") or snap.get("class", ""),
        "by_cycle": by_cycle,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def load_snapshot(kid: dict, reason: str) -> dict:
    """Bakaláři nejedou → vykreslí zálohu místo hlášky o chybě.

    Který cyklus zrovna běží, offline nevíme; odvodí se z parity týdnů od
    posledního zachycení daného cyklu (cykly se střídají po týdnu).
    """
    path = kid.get("snapshot")
    if not path or not os.path.exists(path):
        return {"error": reason}
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"error": reason}

    by_cycle = snap.get("by_cycle") or {}
    if not by_cycle:
        return {"error": reason}

    today = date.today()
    monday = today - timedelta(days=today.isoweekday() - 1)

    def last_seen(bucket):
        got = [v for v in (bucket.get("captured") or {}).values() if v]
        return max(got) if got else ""

    # Cyklus s nejnovějším záznamem je referenční; ostatní se dopočítají paritou.
    ref_name, ref_bucket = max(by_cycle.items(), key=lambda kv: last_seen(kv[1]))
    ref_date = last_seen(ref_bucket)
    pick_name, pick_bucket = ref_name, ref_bucket
    if ref_date and len(by_cycle) == 2:
        ref_monday = date.fromisoformat(ref_date)
        ref_monday -= timedelta(days=ref_monday.isoweekday() - 1)
        if ((monday - ref_monday).days // 7) % 2:
            other = [kv for kv in by_cycle.items() if kv[0] != ref_name]
            if other:
                pick_name, pick_bucket = other[0]

    days = []
    for i in range(14):
        d = monday + timedelta(days=i)
        if d.isoweekday() > 5:
            continue
        lessons = [{
            "hour": str(l.get("hour", "") or ""), "from": l.get("from", ""), "to": l.get("to", ""),
            "subject": l.get("subject", ""), "abbrev": l.get("abbrev", "") or l.get("subject", "")[:6],
            "teacher": l.get("teacher", ""), "room": l.get("room", ""), "group": "",
            "theme": "", "change": "", "change_kind": None,
        } for l in (pick_bucket.get("week") or {}).get(str(d.isoweekday())) or []]
        days.append({
            "date": d.isoformat(), "label": day_label(d), "dow": d.isoweekday(),
            "cycle": "", "desc": "", "type": "WorkDay", "lessons": lessons,
        })

    note = f"Bakaláři nedostupní ({reason}) – záloha"
    if pick_name and pick_name != "-":
        note += f" ({pick_name})"
    if ref_date:
        note += f" z {ref_date}"
    return {"days": days, "class": snap.get("class", ""),
            "fallback": note + ". Bez suplování a odpadlých hodin."}


def main():
    kids = []
    for kid in KIDS:
        entry = {"key": kid["key"], "name": kid["name"], "school": kid["school"],
                 "source": "static" if kid.get("static") else "bakalari", "days": []}
        try:
            got = load_static(kid) if kid.get("static") else fetch_bakalari(kid)
        except BakalariError as e:
            got = {"error": str(e)}
        if kid.get("snapshot"):
            if got.get("error"):
                got = load_snapshot(kid, got["error"])
            else:
                save_snapshot(kid, got)
        if got.get("fallback"):
            entry["source"] = "snapshot"
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
