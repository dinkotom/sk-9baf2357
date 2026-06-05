/**
 * Škola — stav „vyřízených" zpráv (Cloudflare Worker + KV).
 *
 * Drží jeden klíč v KV: seznam ID odškrtnutých (vyřízených) zpráv.
 * Chráněno sdíleným tajemstvím (Authorization: Bearer <API_SECRET>), které
 * stránka zná až po odemčení rodinným heslem (je v šifrovaném payloadu).
 *
 * Endpointy:
 *   GET  /state           -> { dismissed: ["id1","id2",...] }
 *   POST /dismiss  {id, dismissed:true|false} -> { dismissed: [...] }
 *
 * Konfigurace (wrangler.toml + secret):
 *   KV binding: KV
 *   secret:     API_SECRET
 *   var:        ALLOW_ORIGIN (např. https://dinkotom.github.io)
 */

const KEY = "skola:dismissed";

function cors(env) {
  return {
    "Access-Control-Allow-Origin": env.ALLOW_ORIGIN || "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function json(obj, env, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors(env) },
  });
}

async function readSet(env) {
  const v = await env.KV.get(KEY);
  return new Set(v ? JSON.parse(v) : []);
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: cors(env) });

    if (req.headers.get("Authorization") !== "Bearer " + env.API_SECRET) {
      return json({ error: "unauthorized" }, env, 401);
    }

    const url = new URL(req.url);

    if (req.method === "GET" && url.pathname === "/state") {
      return json({ dismissed: [...(await readSet(env))] }, env);
    }

    if (req.method === "POST" && url.pathname === "/dismiss") {
      let body;
      try {
        body = await req.json();
      } catch {
        return json({ error: "bad json" }, env, 400);
      }
      if (body.id === undefined || body.id === null) {
        return json({ error: "missing id" }, env, 400);
      }
      const set = await readSet(env);
      if (body.dismissed) set.add(String(body.id));
      else set.delete(String(body.id));
      await env.KV.put(KEY, JSON.stringify([...set]));
      return json({ dismissed: [...set] }, env);
    }

    return json({ error: "not found" }, env, 404);
  },

  // Cloudflare Cron Trigger — spolehlivě spustí GitHub build v 6:00 a 17:00 Praha.
  // (náhrada za nespolehlivý/zpožděný GitHub Actions schedule)
  async scheduled(event, env, ctx) {
    const hour = parseInt(
      new Intl.DateTimeFormat("en-GB", {
        timeZone: "Europe/Prague", hour: "2-digit", hour12: false,
      }).format(new Date()),
      10,
    );
    // DST-safe: cron běží ve 4,5,15,16 UTC; dispatchni jen když je v Praze 6 nebo 17.
    if (hour !== 6 && hour !== 17) return;
    if (!env.GH_TOKEN) return;
    const repo = env.GH_REPO;
    const wf = env.GH_WORKFLOW || "build.yml";
    const r = await fetch(
      `https://api.github.com/repos/${repo}/actions/workflows/${wf}/dispatches`,
      {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + env.GH_TOKEN,
          "Accept": "application/vnd.github+json",
          "User-Agent": "skola-state-cron",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "main" }),
      },
    );
    console.log("dispatch build:", r.status);
  },
};
