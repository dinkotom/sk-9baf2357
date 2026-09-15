/**
 * Cron dispatcher (Cloudflare Worker).
 *
 * Budí GitHub Actions buildy přes workflow_dispatch — spolehlivá náhrada za
 * nespolehlivý GitHub cron. Obsluhuje dva repa: Školu a IDOS spoje.
 *
 * Historicky tenhle worker držel i stav „vyřízených" zpráv v KV; zprávy byly
 * z appky Škola odstraněny 15. 9. 2026, takže HTTP endpointy /state a /dismiss
 * zmizely. KV namespace zůstal v Cloudflare — smaž ho ručně, až bude jisté,
 * že ho nic nepotřebuje.
 *
 * Konfigurace (wrangler.toml + secret):
 *   secret: GH_TOKEN
 *   vars:   GH_REPO, GH_WORKFLOW, IDOS_REPO
 */

// Spustí GitHub build přes workflow_dispatch (spolehlivé, na rozdíl od GH cronu).
async function dispatchBuild(env, repo, wf) {
  if (!env.GH_TOKEN || !repo) return;
  const r = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/${wf || "build.yml"}/dispatches`,
    {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + env.GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "dinkotom-cron",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main" }),
    },
  );
  console.log("dispatch", repo, r.status);
}

export default {
  // Cloudflare Cron Triggers — spolehlivá náhrada za nespolehlivý GitHub cron.
  //   "*/15 * * * *"        -> IDOS spoje (každých 15 min)
  //   "0 4,5,15,16 * * *"   -> Škola (dispatch jen v 6:00 / 17:00 Praha, DST-safe)
  async scheduled(event, env, ctx) {
    if (event.cron === "*/15 * * * *") {
      ctx.waitUntil(dispatchBuild(env, env.IDOS_REPO, "build.yml"));
      return;
    }
    // Škola: cron běží ve 4,5,15,16 UTC; dispatchni jen když je v Praze 6 nebo 17.
    const hour = parseInt(
      new Intl.DateTimeFormat("en-GB", {
        timeZone: "Europe/Prague", hour: "2-digit", hour12: false,
      }).format(new Date()),
      10,
    );
    if (hour !== 6 && hour !== 17) return;
    ctx.waitUntil(dispatchBuild(env, env.GH_REPO, env.GH_WORKFLOW || "build.yml"));
  },
};
