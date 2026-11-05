"""Ayarlar, yollar ve ortak yardımcılar.

Gizli bilgiler yalnızca ortam değişkenlerinden okunur (GitHub Secrets / .env).
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

KOK = Path(__file__).resolve().parent.parent
CONFIG = KOK / "config"
CLOUDFLARE_SABLON = KOK / "cloudflare"
# Deneme modunda gerçek verilere dokunmamak için çalışma klasörü değiştirilebilir.
_CALISMA = Path(os.environ["OTONOM_CALISMA"]) if os.environ.get("OTONOM_CALISMA") else KOK
VERI = _CALISMA / "veri"     # git'e işlenen kalıcı veriler (küçük dosyalar)
CIKTI = _CALISMA / "cikti"   # büyük üretim dosyaları (git'e işlenmez)
SITE = _CALISMA / "site"     # üretilen statik siteler (Cloudflare Pages'e yüklenir)

log = logging.getLogger("otonom")


def _env_dosyasi_yukle() -> None:
    """Yerel çalıştırmada .env dosyasını okur (GitHub Actions'ta gerekmez)."""
    env = KOK / ".env"
    if not env.exists():
        return
    for satir in env.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        anahtar, deger = satir.split("=", 1)
        os.environ.setdefault(anahtar.strip(), deger.strip().strip('"').strip("'"))


_env_dosyasi_yukle()


def gizli(ad: str) -> str:
    """Ortam değişkeninden gizli bilgi okur; yoksa boş döner."""
    return os.environ.get(ad, "").strip()


@dataclass
class Ayarlar:
    genel: dict[str, Any]
    varliklar: dict[str, Any]
    deneme: bool = False      # True = dış servis çağrısı yok, sahte veriyle uçtan uca test
    simdi: datetime = field(default_factory=lambda: datetime.now(ZoneInfo("Europe/Istanbul")))

    def __getitem__(self, anahtar: str) -> Any:
        return self.genel[anahtar]

    @property
    def nisler(self) -> list[dict[str, Any]]:
        return [n for n in self.varliklar.get("nisler", []) if n]

    def nis(self, kod: str) -> dict[str, Any]:
        for n in self.nisler:
            if n["kod"] == kod:
                return n
        raise KeyError(f"Niş bulunamadı: {kod}")

    @property
    def alan_adlari(self) -> list[dict[str, Any]]:
        return [a for a in self.varliklar.get("alan_adlari", []) if a and a.get("aktif", True)]


def yukle(deneme: bool = False) -> Ayarlar:
    genel = yaml.safe_load((CONFIG / "ayarlar.yaml").read_text(encoding="utf-8")) or {}
    varliklar = yaml.safe_load((CONFIG / "varliklar.yaml").read_text(encoding="utf-8")) or {}
    for k in (VERI, CIKTI):
        k.mkdir(parents=True, exist_ok=True)
    return Ayarlar(genel=genel, varliklar=varliklar, deneme=deneme)


# ---------------------------------------------------------------- yardımcılar

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def kisa_ad(metin: str, uzunluk: int = 60) -> str:
    """'Beyin Sağlığı İçin 5 İpucu' -> 'beyin-sagligi-icin-5-ipucu'"""
    metin = unicodedata.normalize("NFKC", metin).translate(_TR).lower()
    metin = re.sub(r"[^a-z0-9]+", "-", metin).strip("-")
    return metin[:uzunluk].rstrip("-") or "icerik"


def json_oku(yol: Path, varsayilan: Any = None) -> Any:
    if not yol.exists():
        return varsayilan
    return json.loads(yol.read_text(encoding="utf-8"))


def json_yaz(yol: Path, veri: Any) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_oku(yol: Path) -> list[dict[str, str]]:
    if not yol.exists():
        return []
    with yol.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def csv_ekle(yol: Path, satirlar: list[dict[str, Any]], alanlar: list[str]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yeni = not yol.exists()
    with yol.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
        if yeni:
            w.writeheader()
        w.writerows(satirlar)


def ozet_yaz(metin: str) -> None:
    """GitHub Actions iş özetine (Summary sekmesi) Markdown yazar; yerelde ekrana basar."""
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(metin + "\n")
    else:
        print(metin)
