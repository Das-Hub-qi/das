"""MODÜL 6 — Telifsiz görsel toplama.

Sıra: Pexels (ücretsiz API) -> Pixabay (ücretsiz API) -> otomatik yazı kartı.
Videolar yerine fotoğraf + Ken Burns efekti kullanılır: indirme ve montaj 5-10 kat
daha hızlıdır, GitHub Actions'ın ücretsiz dakikaları korunur.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import requests

from . import gorsel
from .ayarlar import CIKTI, Ayarlar, gizli, json_yaz, log

ONBELLEK = CIKTI / "_onbellek"


def _pexels(sorgu: str, dikey: bool) -> list[dict]:
    anahtar = gizli("PEXELS_API_KEY")
    if not anahtar:
        return []
    try:
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": anahtar}, timeout=15,
                         params={"query": sorgu, "per_page": 15,
                                 "orientation": "portrait" if dikey else "landscape"})
        r.raise_for_status()
        return [{"url": p["src"]["portrait" if dikey else "large2x"], "kaynak": "Pexels",
                 "yazar": p.get("photographer", ""), "sayfa": p.get("url", "")} for p in r.json().get("photos", [])]
    except (requests.RequestException, ValueError, KeyError) as e:
        log.warning("Pexels hatası (%s): %s", sorgu, e)
        return []


def _pixabay(sorgu: str, dikey: bool) -> list[dict]:
    anahtar = gizli("PIXABAY_API_KEY")
    if not anahtar:
        return []
    try:
        r = requests.get("https://pixabay.com/api/", timeout=15, params={
            "key": anahtar, "q": sorgu[:100], "image_type": "photo", "safesearch": "true", "per_page": 20,
            "orientation": "vertical" if dikey else "horizontal"})
        r.raise_for_status()
        return [{"url": h["largeImageURL"], "kaynak": "Pixabay", "yazar": h.get("user", ""),
                 "sayfa": h.get("pageURL", "")} for h in r.json().get("hits", [])]
    except (requests.RequestException, ValueError, KeyError) as e:
        log.warning("Pixabay hatası (%s): %s", sorgu, e)
        return []


def _indir(url: str) -> Path | None:
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    yol = ONBELLEK / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg")
    if yol.exists():
        return yol
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        yol.write_bytes(r.content)
        return yol
    except requests.RequestException as e:
        log.warning("İndirilemedi: %s", e)
        return None


def gorsel_bul(ayar: Ayarlar, sorgu: str, hedef: Path, kullanilan: set[str], nis: str,
               dikey: bool = False, yedek_yazi: str = "") -> dict:
    """Videoda daha önce kullanılmamış bir görsel bulur ve `hedef`e kopyalar."""
    if not ayar.deneme:
        for aday in _pexels(sorgu, dikey) + _pixabay(sorgu, dikey):
            if aday["url"] in kullanilan:
                continue
            dosya = _indir(aday["url"])
            if dosya:
                kullanilan.add(aday["url"])
                hedef.write_bytes(dosya.read_bytes())
                return {**aday, "dosya": str(hedef), "sorgu": sorgu}
    g, y = (1080, 1920) if dikey else (1920, 1080)
    gorsel.yazi_karti(yedek_yazi or sorgu, hedef, g, y, gorsel.renk(nis))
    return {"url": "", "kaynak": "Otomatik kart", "yazar": "", "sayfa": "", "dosya": str(hedef), "sorgu": sorgu}


def topla(ayar: Ayarlar, kod: str, icerik: dict) -> list[dict]:
    klasor = CIKTI / kod / "gorseller"
    klasor.mkdir(parents=True, exist_ok=True)
    nis = icerik["plan"]["nis"]
    kullanilan: set[str] = set()
    liste = []
    for i, s in enumerate(icerik["sahneler"]):
        bilgi = gorsel_bul(ayar, s["gorsel_arama"], klasor / f"sahne_{i:03d}.jpg", kullanilan, nis,
                           yedek_yazi=s.get("bolum") or icerik["baslik"])
        liste.append({"sahne": i, **bilgi})
    for j, sh in enumerate(icerik["shorts"]):
        bilgi = gorsel_bul(ayar, sh["gorsel_arama"], klasor / f"shorts_{j}.jpg", kullanilan, nis, dikey=True,
                           yedek_yazi=sh["baslik"])
        liste.append({"shorts": j, **bilgi})
    json_yaz(CIKTI / kod / "materyal_listesi.json", liste)
    return liste
