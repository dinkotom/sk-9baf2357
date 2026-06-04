# Backend pro „vyřízené" zprávy (Cloudflare Worker)

Drobná služba (free tier), která ukládá seznam ID odškrtnutých zpráv do KV,
takže se stav synchronizuje mezi všemi zařízeními a build ho umí přečíst.

## Nasazení (jednorázově)

Předpoklad: účet na Cloudflare (zdarma) a Node.js.

```bash
cd worker
npm install -g wrangler          # CLI Cloudflare
wrangler login                    # přihlášení do tvého CF účtu (otevře prohlížeč)

# 1) vytvoř KV namespace a vlož vypsané id do wrangler.toml (pole id = "...")
wrangler kv namespace create STATE

# 2) nastav sdílené tajemství (stejnou hodnotu pak dáme do GitHub secretu STATE_API_SECRET)
wrangler secret put API_SECRET    # vloží se hodnota z ../secrets_worker.txt

# 3) nasaď
wrangler deploy
```

`wrangler deploy` vypíše veřejnou URL Workeru, např.
`https://skola-state.<tvuj-subdomain>.workers.dev`. Tu pak nastavíme do GitHub
secretu `STATE_API_URL`.

## Endpointy

| Metoda | Cesta | Tělo | Vrací |
|---|---|---|---|
| GET | `/state` | — | `{ "dismissed": ["id", …] }` |
| POST | `/dismiss` | `{ "id": "…", "dismissed": true\|false }` | aktualizovaný seznam |

Vše vyžaduje hlavičku `Authorization: Bearer <API_SECRET>`. CORS je povolen jen
pro `https://dinkotom.github.io`.
