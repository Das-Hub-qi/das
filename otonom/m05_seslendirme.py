"""MODÜL 5 — Seslendirme (Microsoft Edge TTS, ücretsiz) + otomatik altyazı zamanlaması."""
from __future__ import annotations

import asyncio
import os
import ssl
import subprocess
from pathlib import Path

from .ayarlar import Ayarlar, log

TIK = 10_000_000  # edge-tts zaman birimi: 100 ns


def sure(yol: Path) -> float:
    cikti = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(yol)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(cikti)


async def _seslendir(metin: str, yol: Path, ses: str, hiz: str) -> list[tuple[float, float, str]]:
    import aiohttp
    import edge_tts

    ek: dict = {}
    # Kurumsal proxy / özel sertifika ortamları için (GitHub Actions'ta gerekmez)
    if os.environ.get("SSL_CERT_FILE"):
        ek["connector"] = aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"]))
    if os.environ.get("HTTPS_PROXY"):
        ek["proxy"] = os.environ["HTTPS_PROXY"]
    iletisim = edge_tts.Communicate(metin, ses, rate=hiz, boundary="WordBoundary", **ek)
    kelimeler = []
    with yol.open("wb") as f:
        async for parca in iletisim.stream():
            if parca["type"] == "audio":
                f.write(parca["data"])
            elif parca["type"] == "WordBoundary":
                bas = parca["offset"] / TIK
                kelimeler.append((bas, bas + parca["duration"] / TIK, parca["text"]))
    return kelimeler


def _sessiz(yol: Path, saniye: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{saniye:.2f}", "-q:a", "9", str(yol)], check=True)


def seslendir(ayar: Ayarlar, metin: str, yol: Path) -> dict:
    """Döner: {"ses": yol, "sure": saniye, "kelimeler": [(baş, son, kelime), ...]}"""
    yol.parent.mkdir(parents=True, exist_ok=True)
    if ayar.deneme:
        kelime = metin.split()
        s = max(1.5, len(kelime) / 2.6)
        _sessiz(yol, s)
        adim = s / max(1, len(kelime))
        return {"ses": yol, "sure": s, "kelimeler": [(i * adim, (i + 1) * adim, k) for i, k in enumerate(kelime)]}
    for deneme in range(3):
        try:
            kel = asyncio.run(_seslendir(metin, yol, ayar["ses"]["ses_adi"], ayar["ses"]["hiz"]))
            return {"ses": yol, "sure": sure(yol), "kelimeler": kel}
        except Exception as e:  # ağ kesintisi vb. — tekrar dene
            log.warning("Seslendirme denemesi %d başarısız: %s", deneme + 1, e)
    raise RuntimeError("Seslendirme 3 denemede başarısız.")


# ------------------------------------------------------------------ altyazı

def _zaman(s: float) -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def gruplar(kelimeler: list[tuple[float, float, str]], en_fazla: int = 7) -> list[tuple[float, float, str]]:
    """Kelimeleri okunabilir altyazı satırlarına böler.

    Bölme noktaları: noktalama, seslendirmedeki duraklama (>0,3 sn) veya en_fazla kelime.
    """
    satirlar, grup = [], []
    for i, k in enumerate(kelimeler):
        grup.append(k)
        sonraki = kelimeler[i + 1] if i + 1 < len(kelimeler) else None
        duraklama = sonraki is not None and sonraki[0] - k[1] > 0.3
        if len(grup) >= en_fazla or duraklama or k[2].endswith((".", "!", "?", ",", ":", ";")):
            satirlar.append((grup[0][0], grup[-1][1], " ".join(x[2] for x in grup)))
            grup = []
    if grup:
        satirlar.append((grup[0][0], grup[-1][1], " ".join(x[2] for x in grup)))
    return satirlar


def srt(satirlar: list[tuple[float, float, str]]) -> str:
    return "\n".join(f"{i}\n{_zaman(b)} --> {_zaman(s)}\n{m}\n" for i, (b, s, m) in enumerate(satirlar, 1))
