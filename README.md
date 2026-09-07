# Škola — rozvrhy kluků + šifrovaný digest školních zpráv

Statická stránka pro GitHub Pages se dvěma záložkami:

- **Rozvrh** — rozvrhy všech tří kluků (Ota, Čeněk, Eda) v pohledech
  *Dnes / Zítra / Týden*. U Oty a Edy jde o **živý** rozvrh z Bakalářů, tedy
  včetně suplování, odpadlých hodin a změn učeben (barevně odlišené).
- **Zprávy** — přijaté zprávy a nástěnka z Bakalářů (Eda) + AI digest.

Staví se **dvakrát denně** (6:00 a 17:00 Praha), vše se **zašifruje** a až pak
publikuje. Obsah se dešifruje v prohlížeči po zadání rodinného hesla — na Pages
se nikdy nepublikuje čistý text.

Součást rodinného rozcestníku [„Doma"](https://dinkotom.github.io/domov-60de93c6/).

## Jak to funguje

```
GitHub Actions (cron 04:00 a 15:00 UTC)
  fetch_messages.py   → _data/items.json      (Komens zprávy + nástěnka, Eda)
  fetch_timetable.py  → _data/timetable.json  (rozvrhy: Ota + Eda živě, Čeněk staticky)
  claude -p           → _data/digest.md       (AI shrnutí, přes předplatné)
  build_page.py       → public/index.html     (AES-GCM, klíč z hesla přes PBKDF2)
  deploy-pages
```

AI digest běží přes **Claude Code s OAuth tokenem** (`claude setup-token`),
takže se účtuje z předplatného, ne z placeného API.

## GitHub Secrets

| Secret | Popis |
|---|---|
| `BAKALARI_BASE_URL` | Eda — `https://1zsfm.bakalari.cz/bakaweb` |
| `BAKALARI_USERNAME` | Eda — přihlašovací jméno |
| `BAKALARI_PASSWORD` | Eda — heslo |
| `BAKALARI_OTA_BASE_URL` | Ota — `https://bakalar.hladnov.cz` (**bez** `/bakaweb`!) |
| `BAKALARI_OTA_USERNAME` | Ota — přihlašovací jméno |
| `BAKALARI_OTA_PASSWORD` | Ota — heslo |
| `CLAUDE_CODE_OAUTH_TOKEN` | z `claude setup-token` (sk-ant-oat01-…) |
| `APP_PASSWORD` | rodinné heslo pro odemčení stránky (stejné jako Účty) |
| `STATE_API_URL` | URL Cloudflare Workeru (odškrtávání), volitelné |
| `STATE_API_SECRET` | sdílené tajemství k Workeru, volitelné |

## Odškrtávání vyřízených zpráv

Volitelná funkce: u každé zprávy je zaškrtávátko „vyřízeno". Odškrtnuté zprávy
se skryjí (synchronizovaně na všech zařízeních) a AI digest je přestane
zmiňovat. Stav drží malý **Cloudflare Worker + KV** — viz [worker/README.md](worker/README.md).
Bez nastavených `STATE_API_*` secrets se stránka chová jako dřív (bez zaškrtávátek).

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
cat _data/items.json | claude -p "$(cat prompt.md)" > _data/digest.md   # volitelné
APP_PASSWORD=heslo python build_page.py
open public/index.html
```

## Bezpečnost

- Čistý text zpráv ani heslo se nikdy necommitují (viz `.gitignore`).
- Payload je šifrovaný AES-GCM, klíč odvozen z hesla (PBKDF2-SHA256, 200k iterací).
- `noindex, nofollow`; repo je sice veřejné, ale obsah bez hesla nečitelný.
