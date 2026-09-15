# Škola — šifrované rozvrhy kluků

Statická stránka pro GitHub Pages: rozvrhy všech tří kluků (Ota, Čeněk, Eda)
pod sebou, ve dvou pohledech — **Den** a **Týden** (klasická mřížka po–pá).
U Oty a Edy jde o **živý** rozvrh z Bakalářů, tedy včetně suplování, odpadlých
hodin a změn učeben (barevně odlišené); Čeněk je statický, ScioŠkola jede na
Edookitu bez rodičovského API. Součástí jsou i kroužky.

Staví se **dvakrát denně** (6:00 a 17:00 Praha), vše se **zašifruje** a až pak
publikuje. Obsah se dešifruje v prohlížeči po zadání rodinného hesla — na Pages
se nikdy nepublikuje čistý text.

Součást rodinného rozcestníku [„Doma"](https://dinkotom.github.io/domov-60de93c6/).

## Jak to funguje

```
GitHub Actions (cron 04:00 a 15:00 UTC)
  fetch_timetable.py  → _data/timetable.json  (rozvrhy: Ota + Eda živě, Čeněk staticky)
  build_page.py       → public/index.html     (AES-GCM, klíč z hesla přes PBKDF2)
  deploy-pages
```

## GitHub Secrets

| Secret | Popis |
|---|---|
| `BAKALARI_BASE_URL` | Eda — `https://1zsfm.bakalari.cz/bakaweb` |
| `BAKALARI_USERNAME` | Eda — přihlašovací jméno |
| `BAKALARI_PASSWORD` | Eda — heslo |
| `BAKALARI_OTA_BASE_URL` | Ota — `https://bakalar.hladnov.cz` (**bez** `/bakaweb`!) |
| `BAKALARI_OTA_USERNAME` | Ota — přihlašovací jméno |
| `BAKALARI_OTA_PASSWORD` | Ota — heslo |
| `APP_PASSWORD` | rodinné heslo pro odemčení stránky (stejné jako Účty) |

## Kroužky

Ruční evidence v `data/krouzky.json` (klíč = dítě, `dow` 1=po … 5=pá). Zobrazují
se jako oddělený pruh pod výukou v obou pohledech. Po sezóně je potřeba je
aktualizovat — zdrojové dokumenty jsou odkázané přímo v souboru.

## Záloha rozvrhů

Když Bakaláři nejedou, Ota a Eda se vykreslí ze zálohy `data/<kluk>_zaloha.json`
místo hlášky o chybě (s varovným bannerem). Do zálohy jdou jen hodiny **bez**
suplování a kumulují se po cyklech (sudý/lichý týden), takže jeden týden plný
změn neudělá děravý rozvrh. CI zálohu po každém úspěšném běhu commitne zpátky.

## Rozvrhy

Konfigurace kluků je v `KIDS` v [fetch_timetable.py](fetch_timetable.py).
Tahá se **aktuální i příští týden**, aby „Zítra" fungovalo i v pátek večer.

Ošetřené vychytávky Bakalářů:

- `Atoms[].Change` = suplování / odpadlá hodina / změna učebny → na stránce
  barevně (červeně přeškrtnuté = odpadá, zlatě = suplování, zeleně = přidáno).
- `Cycles` = lichý/sudý týden; hodiny cizího cyklu se filtrují.
- Odpadlé hodiny **na konci** dne se zahazují (šum), na začátku a uvnitř se
  nechávají — to je informace „jde později" / „má volnou hodinu".
- Skupina se zobrazuje jen když není celá třída (`1.C Aj1` → `Aj1`).

### Čeněk (ScioŠkola)

Edookit **nemá rodičovské API** a škola má jen SSO přes Plus4U, takže se
scrapovat rozumně nedá. Čeňkův rozvrh se proto udržuje **ručně** v
[data/cenek.json](data/cenek.json) — klíč `week`, kde `1` = pondělí … `5` = pátek:

```json
"week": { "1": [{"hour": "1", "from": "8:00", "to": "9:30",
                 "subject": "Matematika", "room": "", "note": ""}] }
```

Dokud je `week` prázdné, ukáže se u Čeňka „rozvrh není zadaný". Aktualizuje se
podle Edookitu (Rozvrh) — po změně stačí commitnout, push spustí build.

## Lokální test

```bash
pip install -r requirements.txt
export BAKALARI_BASE_URL=... BAKALARI_USERNAME=... BAKALARI_PASSWORD=...
python fetch_messages.py
export BAKALARI_OTA_BASE_URL=... BAKALARI_OTA_USERNAME=... BAKALARI_OTA_PASSWORD=...
python fetch_timetable.py
APP_PASSWORD=heslo python build_page.py
open public/index.html
```

## Bezpečnost

- Rozvrhová data ani heslo se nikdy necommitují v čitelné podobě (viz `.gitignore`).
- Payload je šifrovaný AES-GCM, klíč odvozen z hesla (PBKDF2-SHA256, 200k iterací).
- `noindex, nofollow`; repo je sice veřejné, ale obsah bez hesla nečitelný.
