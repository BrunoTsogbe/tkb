// Suivi en direct d'un rêve (KAN-22) : interroge le fragment de statut toutes les 2 s.
(() => {
  "use strict";
  const INTERVAL_MS = 2000;
  const MAX_POLLS = 300; // 10 minutes : au-delà, l'utilisateur recharge la page

  let polls = 0;
  async function poll() {
    const live = document.getElementById("dream-live");
    if (!live || live.dataset.finished === "1" || polls++ > MAX_POLLS) return;
    try {
      const response = await fetch(live.dataset.statusUrl, { credentials: "same-origin", cache: "no-store" });
      if (response.ok) {
        const html = await response.text();
        const next = new DOMParser().parseFromString(html, "text/html").getElementById("dream-live");
        if (next) {
          live.replaceWith(next);
          if (next.dataset.finished === "1") { window.location.reload(); return; }
        }
      }
    } catch {
      // réseau momentanément indisponible : on réessaie au prochain tour
    }
    setTimeout(poll, INTERVAL_MS);
  }
  setTimeout(poll, INTERVAL_MS);
})();
