"""Enregistre la vidéo de démonstration de la maquette (livrable 5.3, ≤ 3 min).

Le script lance la maquette, la pilote dans Microsoft Edge (mode headless,
protocole DevTools), capture l'écran en continu, ajoute des sous-titres et des
cartons de titre, puis encode un MP4.

Usage (depuis la racine du projet) :
    python maquette/demo/record_demo.py

Dépendances : websockets, pillow, imageio-ffmpeg.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import itertools
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import imageio_ffmpeg
import websockets
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "maquette" / "demo" / "demo_maquette.mp4"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PORT_APP, PORT_CDP = 8611, 9341
WIDTH, HEIGHT, FPS = 1280, 720, 12
FONT_REGULAR = r"C:\Windows\Fonts\segoeui.ttf"
FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Charge une police système.

    Args:
        size: Taille en pixels.
        bold: Graisse grasse.

    Returns:
        Police PIL.
    """
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def title_card(title: str, lines: list[str]) -> Image.Image:
    """Dessine un carton de titre au style « ciel nocturne ».

    Args:
        title: Titre principal.
        lines: Lignes secondaires.

    Returns:
        Image RGB aux dimensions de la vidéo.
    """
    image = Image.new("RGB", (WIDTH, HEIGHT), (7, 7, 24))
    glow = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse([-200, -300, 700, 400], fill=(90, 40, 170))
    draw.ellipse([800, -200, 1500, 350], fill=(150, 40, 110))
    draw.ellipse([300, 500, 1100, 1100], fill=(20, 110, 130))
    image = Image.blend(image, glow.filter(ImageFilter.GaussianBlur(160)), 0.55)
    draw = ImageDraw.Draw(image)
    for x, y in itertools.islice(zip(range(37, 10**6, 97), range(53, 10**6, 61), strict=False), 120):
        draw.point((x % WIDTH, y % HEIGHT), fill=(230, 230, 255))
    draw.ellipse([WIDTH // 2 - 34, 150, WIDTH // 2 + 34, 218], fill=(250, 240, 205))
    draw.text((WIDTH // 2, 300), title, font=font(54, bold=True), fill=(255, 255, 255), anchor="mm")
    for index, line in enumerate(lines):
        draw.text((WIDTH // 2, 380 + index * 44), line, font=font(26), fill=(200, 195, 240), anchor="mm")
    return image


def with_caption(frame: Image.Image, caption: str) -> Image.Image:
    """Ajoute un bandeau de sous-titre en bas de l'image.

    Args:
        frame: Capture d'écran.
        caption: Texte du sous-titre (vide : aucun bandeau).

    Returns:
        Image annotée.
    """
    if not caption:
        return frame
    frame = frame.convert("RGBA")
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text_font = font(26, bold=True)
    width = draw.textlength(caption, font=text_font)
    x0, y0 = (WIDTH - width) / 2 - 26, HEIGHT - 86
    draw.rounded_rectangle(
        [x0, y0, x0 + width + 52, y0 + 56], radius=28, fill=(12, 10, 40, 215), outline=(196, 181, 253, 160), width=2
    )
    draw.text((WIDTH / 2, y0 + 28), caption, font=text_font, fill=(255, 255, 255, 255), anchor="mm")
    return Image.alpha_composite(frame, overlay).convert("RGB")


@dataclass
class Recorder:
    """Pilote Edge et accumule les captures horodatées.

    Attributes:
        ws: Connexion DevTools.
        frames: Captures (instant, JPEG, sous-titre).
        caption: Sous-titre courant.
    """

    ws: websockets.ClientConnection
    frames: list[tuple[float, bytes, str]] = field(default_factory=list)
    caption: str = ""
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))
    _pending: dict[int, asyncio.Future] = field(default_factory=dict)

    async def reader(self) -> None:
        """Distribue les réponses DevTools aux appels en attente."""
        async for raw in self.ws:
            message = json.loads(raw)
            if message.get("method") == "Page.screencastFrame":
                params = message["params"]
                self.frames.append((time.perf_counter(), base64.b64decode(params["data"]), self.caption))
                ack = {
                    "id": next(self._ids),
                    "method": "Page.screencastFrameAck",
                    "params": {"sessionId": params["sessionId"]},
                }
                await self.ws.send(json.dumps(ack))
                continue
            future = self._pending.pop(message.get("id", -1), None)
            if future and not future.done():
                future.set_result(message.get("result", {}))

    async def cmd(self, method: str, **params: object) -> dict:
        """Envoie une commande DevTools et attend sa réponse.

        Args:
            method: Méthode DevTools.
            **params: Paramètres de la méthode.

        Returns:
            Résultat de la commande.
        """
        ident = next(self._ids)
        future = asyncio.get_running_loop().create_future()
        self._pending[ident] = future
        await self.ws.send(json.dumps({"id": ident, "method": method, "params": params}))
        return await asyncio.wait_for(future, 30)

    async def js(self, expression: str) -> object:
        """Évalue du JavaScript dans la page.

        Args:
            expression: Code à évaluer.

        Returns:
            Valeur renvoyée.
        """
        result = await self.cmd("Runtime.evaluate", expression=expression, awaitPromise=True)
        return result.get("result", {}).get("value")

    async def start_capture(self) -> None:
        """Démarre le flux d'images du navigateur (une image à chaque rendu)."""
        await self.cmd("Page.startScreencast", format="jpeg", quality=85, maxWidth=WIDTH, maxHeight=HEIGHT)

    async def stop_capture(self) -> None:
        """Arrête le flux d'images et fige la dernière image."""
        await self.cmd("Page.stopScreencast")
        if self.frames:
            last = self.frames[-1]
            self.frames.append((time.perf_counter(), last[1], ""))

    async def click_button(self, text: str) -> bool:
        """Clique sur le premier bouton dont le libellé contient ``text``.

        Args:
            text: Fragment du libellé.

        Returns:
            Vrai si un bouton a été trouvé.
        """
        return bool(
            await self.js(
                "(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.includes("
                + json.dumps(text)
                + "));if(b){b.scrollIntoView({block:'center'});b.click();return true}return false})()"
            )
        )

    async def click_label(self, text: str) -> bool:
        """Clique sur l'interrupteur dont le libellé contient ``text``.

        Args:
            text: Fragment du libellé.

        Returns:
            Vrai si l'élément a été trouvé.
        """
        return bool(
            await self.js(
                "(()=>{const l=[...document.querySelectorAll('label')].find(l=>l.innerText.includes("
                + json.dumps(text)
                + "));const i=l&&l.querySelector('input');if(i){i.click();return true}return false})()"
            )
        )

    async def scroll_to(self, target: str, duration: float = 2.0) -> None:
        """Fait défiler la page en douceur.

        Args:
            target: Expression JS donnant la position verticale visée.
            duration: Durée du défilement en secondes.
        """
        container = "(document.querySelector('[data-testid=\"stMain\"]')||document.scrollingElement)"
        start = await self.js(f"{container}.scrollTop") or 0
        end = await self.js(f"(()=>{{const c={container};return {target};}})()") or 0
        steps = max(1, int(duration * 20))
        for i in range(1, steps + 1):
            k = i / steps
            eased = k * k * (3 - 2 * k)
            await self.js(f"{container}.scrollTop={start + (end - start) * eased}")
            await asyncio.sleep(duration / steps)

    async def wait_for(self, expression: str, timeout: float = 30) -> None:
        """Attend qu'une condition JavaScript soit vraie.

        Args:
            expression: Condition à évaluer.
            timeout: Délai maximal en secondes.
        """
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            if await self.js(expression):
                return
            await asyncio.sleep(0.25)
        raise TimeoutError(expression)


async def scenario(rec: Recorder) -> None:
    """Déroule le scénario de démonstration.

    Args:
        rec: Enregistreur connecté à la page.
    """
    has = "[...document.querySelectorAll('button')].some(b=>b.innerText.includes({}))".format
    await rec.cmd("Page.enable")
    await rec.cmd("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT, deviceScaleFactor=1, mobile=False)
    await rec.cmd("Page.navigate", url=f"http://localhost:{PORT_APP}")
    await rec.wait_for(has(json.dumps("Rêve d'exemple")), 60)
    await asyncio.sleep(3)

    await rec.start_capture()

    rec.caption = "Racontez votre rêve au réveil : micro du navigateur ou fichier .wav / .mp3"
    await asyncio.sleep(5)
    rec.caption = "Démo sans micro : un rêve d'exemple traverse tout le traitement"
    await rec.click_button("Rêve d'exemple")
    await asyncio.sleep(1.2)
    rec.caption = "Étapes en direct : transcription, ambiance, puis image"
    await rec.wait_for("document.body.textContent.includes('Garder ce rêve')", 40)
    await asyncio.sleep(1)
    rec.caption = "Émotion détectée et probabilités : la correction reste possible"
    await rec.scroll_to("c.querySelector('[class*=\"st-key-card-result\"]').offsetTop - 40", 2.5)
    await asyncio.sleep(4)
    rec.caption = "Texte modifiable, durée et coût API estimé du rêve"
    await asyncio.sleep(4)
    await rec.click_button("Garder ce rêve")
    rec.caption = "Le rêve rejoint l'historique personnel"
    await asyncio.sleep(3)

    await rec.scroll_to("0", 1.5)
    rec.caption = "Gestion d'erreurs : on simule une panne de l'API de transcription"
    await rec.click_label("panne de transcription")
    await asyncio.sleep(2)
    await rec.click_button("Rêve d'exemple")
    await rec.wait_for("document.body.textContent.includes('La transcription a échoué')", 30)
    rec.caption = "Message clair, rien n'est perdu : l'application répond toujours"
    await asyncio.sleep(4.5)
    await rec.click_label("panne de transcription")
    await rec.click_label("panne du service d'images")
    await asyncio.sleep(1.5)
    rec.caption = "Service d'images en panne : une image de secours prend le relais"
    await rec.click_button("Rêve d'exemple")
    await rec.wait_for("document.body.textContent.includes('image de secours est affichée')", 40)
    await rec.scroll_to("c.querySelector('[class*=\"st-key-card-image\"]').offsetTop - 40", 2)
    await asyncio.sleep(4)
    await rec.click_label("panne du service d'images")

    rec.caption = "Tableau de bord : on charge deux semaines de rêves d'exemple"
    await rec.click_button("Charger des rêves")
    await rec.wait_for("document.body.textContent.includes('Rêves racontés')", 30)
    await asyncio.sleep(2)
    await rec.scroll_to("c.querySelector('[class*=\"st-key-card-dashboard\"]').offsetTop - 70", 3)
    rec.caption = "Ambiance dominante, émotions et évolution dans le temps"
    await asyncio.sleep(6)
    rec.caption = "Filtre par ambiance et galerie des rêves"
    await rec.click_button("Stressant")
    await asyncio.sleep(2.5)
    pills = 'c.querySelector(\'[data-testid="stPills"], [class*="stPills"]\')'
    await rec.scroll_to(f"{pills}?.getBoundingClientRect().top + c.scrollTop - 90 || c.scrollTop + 500", 2.5)
    await asyncio.sleep(5)
    rec.caption = ""
    await rec.stop_capture()


def encode(frames: list[tuple[float, bytes, str]]) -> None:
    """Assemble les cartons et les captures en MP4 à cadence fixe.

    Args:
        frames: Captures horodatées.
    """
    intro = title_card(
        "Synthétiseur de rêves", ["Démo de la maquette Streamlit · pré-production", "Bruno Tsogbe · novembre 2026"]
    )
    outro = title_card(
        "Merci !",
        [
            "APIs simulées : aucune clé, aucun coût",
            "44 tests pytest · couverture 99 % · lint ruff sans erreur",
            "streamlit run maquette/app.py",
        ],
    )
    writer = imageio_ffmpeg.write_frames(
        str(OUTPUT), (WIDTH, HEIGHT), fps=FPS, codec="libx264", pix_fmt_out="yuv420p", quality=8, macro_block_size=8
    )
    writer.send(None)

    def emit(image: Image.Image, seconds: float) -> None:
        data = image.convert("RGB").tobytes()
        for _ in range(int(seconds * FPS)):
            writer.send(data)

    emit(intro, 4)
    start, end = frames[0][0], frames[-1][0]
    index = 0
    tick = start
    while tick <= end:
        while index + 1 < len(frames) and frames[index + 1][0] <= tick:
            index += 1
        _, jpeg, caption = frames[index]
        image = Image.open(io.BytesIO(jpeg)).convert("RGB").resize((WIDTH, HEIGHT))
        writer.send(with_caption(image, caption).tobytes())
        tick += 1 / FPS
    emit(outro, 5)
    writer.close()


def main() -> None:
    """Point d'entrée : lance l'application et le navigateur, enregistre, encode."""
    app = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "maquette/app.py",
            "--server.headless",
            "true",
            "--server.port",
            str(PORT_APP),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    profile = Path(tempfile.mkdtemp(prefix="demo-edge-"))
    browser = subprocess.Popen(
        [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            f"--remote-debugging-port={PORT_CDP}",
            f"--user-data-dir={profile}",
            f"--window-size={WIDTH},{HEIGHT}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        page = None
        for _ in range(60):
            with contextlib.suppress(OSError, ValueError, StopIteration):
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT_CDP}/json", timeout=2))
                page = next(t for t in targets if t["type"] == "page")
                break
            time.sleep(0.5)
        if page is None:
            raise SystemExit("Edge n'a pas démarré.")

        async def run() -> list[tuple[float, bytes, str]]:
            async with websockets.connect(page["webSocketDebuggerUrl"], max_size=2**27) as ws:
                rec = Recorder(ws)
                reader = asyncio.create_task(rec.reader())
                await scenario(rec)
                reader.cancel()
                return rec.frames

        frames = asyncio.run(run())
        encode(frames)
        total = 4 + (frames[-1][0] - frames[0][0]) + 5
        print(f"{OUTPUT.relative_to(ROOT)} : {total:.0f} s, {len(frames)} captures")
    finally:
        browser.terminate()
        app.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            browser.wait(5)
            app.wait(5)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
