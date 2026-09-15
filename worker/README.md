# Cron dispatcher (Cloudflare Worker)

Drobná služba na free tieru, která budí GitHub Actions buildy přes
`workflow_dispatch`. Nahrazuje nespolehlivý GitHub cron (zpoždění i 2,5 h,
občas výpadky). Obsluhuje **dvě** repa:

| Cron (UTC) | Co |
|---|---|
| `0 4,5,15,16 * * *` | **Škola** — worker dispatchne jen když je v Praze 6:00 nebo 17:00 (DST-safe) |
| `*/15 * * * *` | **IDOS spoje** (`dinkotom/jr-45d291ec`) — každých 15 min |

> ⚠️ Worker se jmenuje `skola-state` z historických důvodů — dřív držel i stav
> „vyřízených" zpráv. Zprávy byly z appky odstraněny 15. 9. 2026 a HTTP
> endpointy `/state` a `/dismiss` s nimi. **Nepřejmenovávej ho** — vznikl by
> nový worker a osiřely by cron triggery pro obě repa.
>
> KV namespace `87395cbadd1d4b3b9abaa4a5840daf93` zůstal v Cloudflare
> nevyužitý. Smazat ho jde přes `wrangler kv namespace delete`, až bude jisté,
> že ho nic nepotřebuje. Stejně tak secret `API_SECRET` už kód nečte.

## Nasazení

```bash
cd worker
npm install -g wrangler
wrangler login
wrangler secret put GH_TOKEN   # fine-grained PAT, Actions:write na obou repech
wrangler deploy
```

Po odstranění zpráv **není nasazení nutné hned** — běžící worker jen dál
obsluhuje dvojici endpointů, které už nikdo nevolá. Nasaď při nejbližší
příležitosti, ať kód v repu odpovídá tomu, co běží.
