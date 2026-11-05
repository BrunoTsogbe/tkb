// Enregistreur de rêves (KAN-17) : MediaRecorder → envoi multipart → page de suivi.
(() => {
  "use strict";
  const root = document.querySelector("[data-recorder]");
  if (!root) return;

  const mic = root.querySelector("[data-mic]");
  const timer = root.querySelector("[data-timer]");
  const errorBox = root.querySelector("[data-recorder-error]");
  const help = root.querySelector("[data-mic-help]");
  const csrf = document.querySelector("input[name=csrfmiddlewaretoken]")?.value || "";
  const MAX_SECONDS = 10 * 60;
  let recorder = null;
  let chunks = [];
  let started = 0;
  let tick = null;

  const showError = (message) => { errorBox.textContent = message; errorBox.hidden = false; };
  const format = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    mic.disabled = true;
    help.hidden = false;
    return;
  }

  async function start() {
    errorBox.hidden = true;
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      help.hidden = false;
      return;
    }
    const type = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
    recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    chunks = [];
    recorder.ondataavailable = (event) => event.data.size && chunks.push(event.data);
    recorder.onstop = () => { stream.getTracks().forEach((t) => t.stop()); upload(); };
    recorder.start();
    started = Date.now();
    mic.setAttribute("aria-pressed", "true");
    mic.setAttribute("aria-label", "Terminer l'enregistrement");
    tick = setInterval(() => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      timer.textContent = `${format(seconds)} · appuyez pour terminer`;
      if (seconds >= MAX_SECONDS) stop();
    }, 250);
  }

  function stop() {
    clearInterval(tick);
    mic.setAttribute("aria-pressed", "false");
    mic.disabled = true;
    timer.textContent = "Envoi en cours…";
    recorder?.state === "recording" && recorder.stop();
  }

  async function upload() {
    const body = new FormData();
    body.append("audio", new Blob(chunks, { type: "audio/webm" }), "enregistrement.webm");
    try {
      const response = await fetch(root.dataset.uploadUrl, {
        method: "POST", body, headers: { "X-CSRFToken": csrf, Accept: "application/json" }, credentials: "same-origin",
      });
      const data = await response.json();
      if (response.ok && data.redirect) { window.location.assign(data.redirect); return; }
      showError(data.error || "L'envoi a échoué. Réessayez.");
    } catch {
      showError("Connexion perdue : votre enregistrement n'a pas pu être envoyé. Réessayez.");
    }
    mic.disabled = false;
    timer.textContent = "Appuyez pour recommencer";
  }

  mic.addEventListener("click", () => (recorder?.state === "recording" ? stop() : start()));
})();
