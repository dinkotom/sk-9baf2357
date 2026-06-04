# Škola — šifrovaný digest školních zpráv (Bakaláři)

Statická stránka pro GitHub Pages, která **dvakrát denně** (6:00 a 17:00 Praha)
stáhne přijaté zprávy a nástěnku z Bakalářů, nechá Claude vytvořit stručný
český digest důležitých informací, vše **zašifruje** a publikuje. Obsah se
dešifruje až v prohlížeči po zadání rodinného hesla — na Pages se nikdy
nepublikuje čistý text zpráv.

Součást rodinného rozcestníku [„Doma"](https://dinkotom.github.io/domov-60de93c6/).

## Jak to funguje

```
GitHub Actions (cron 04:00 a 15:00 UTC)
  fetch_messages.py  → _data/items.json   (Bakaláři REST API v3)
  claude -p          → _data/digest.md     (AI shrnutí, přes předplatné)
  build_page.py      → public/index.html   (AES-GCM, klíč z hesla přes PBKDF2)
  deploy-pages
```

AI digest běží přes **Claude Code s OAuth tokenem** (`claude setup-token`),
takže se účtuje z předplatného, ne z placeného API.

## GitHub Secrets

| Secret | Popis |
|---|---|
| `BAKALARI_BASE_URL` | `https://1zsfm.bakalari.cz/bakaweb` |
| `BAKALARI_USERNAME` | přihlašovací jméno žáka |
| `BAKALARI_PASSWORD` | heslo žáka |
| `CLAUDE_CODE_OAUTH_TOKEN` | z `claude setup-token` (sk-ant-oat01-…) |
| `APP_PASSWORD` | rodinné heslo pro odemčení stránky (stejné jako Účty) |
| `STATE_API_URL` | URL Cloudflare Workeru (odškrtávání), volitelné |
| `STATE_API_SECRET` | sdílené tajemství k Workeru, volitelné |

## Odškrtávání vyřízených zpráv

Volitelná funkce: u každé zprávy je zaškrtávátko „vyřízeno". Odškrtnuté zprávy
se skryjí (synchronizovaně na všech zařízeních) a AI digest je přestane
zmiňovat. Stav drží malý **Cloudflare Worker + KV** — viz [worker/README.md](worker/README.md).
Bez nastavených `STATE_API_*` secrets se stránka chová jako dřív (bez zaškrtávátek).

## Lokální test

```bash
pip install -r requirements.txt
export BAKALARI_BASE_URL=... BAKALARI_USERNAME=... BAKALARI_PASSWORD=...
python fetch_messages.py
cat _data/items.json | claude -p "$(cat prompt.md)" > _data/digest.md   # volitelné
APP_PASSWORD=heslo python build_page.py
open public/index.html
```

## Bezpečnost

- Čistý text zpráv ani heslo se nikdy necommitují (viz `.gitignore`).
- Payload je šifrovaný AES-GCM, klíč odvozen z hesla (PBKDF2-SHA256, 200k iterací).
- `noindex, nofollow`; repo je sice veřejné, ale obsah bez hesla nečitelný.
