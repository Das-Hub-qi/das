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
    yukleme: bool = True      # False = videolar üretilir ama YouTube'a yüklenmez (beta)
    mod: str = "normal"       # bütçe modu: normal | azaltilmis | hafif (butce.py belirler)
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


# Ayar dosyasında eksik/silinmiş bir satır sistemi durdurmasın diye her ayarın varsayılanı burada.
VARSAYILAN: dict[str, Any] = {
    "saat_dilimi": "Europe/Istanbul",
    "llm": {"saglayici": "otomatik", "yerel_model": "unsloth/gemma-4-E2B-it-GGUF",
            "yerel_dosya": "gemma-4-E2B-it-Q4_K_M.gguf", "yerel_baglam": 10240, "yerel_sicaklik": 0.7,
            "model": "claude-haiku-5-5", "toplu_islem": True, "senaryo_efor": "medium", "kisa_is_efor": "low"},
    "youtube": {"haftalik_uzun_video": 3, "video_basina_shorts": 2, "hedef_kelime": 1100, "kategori_id": "27",
                "gizlilik": "private", "yayin_gunleri": ["sali", "persembe", "cumartesi"], "yayin_saati": "18:00",
                "altyazi_yukle": True, "sentetik_medya_beyani": False},
    "ses": {"ses_adi": "tr-TR-AhmetNeural", "hiz": "+5%", "muzik_seviyesi_db": -20},
    "video": {"genislik": 1920, "yukseklik": 1080, "fps": 24, "ken_burns": True, "crf": 23,
              "intro_saniye": 0, "outro_saniye": 5},
    "butce": {"github_dakika_limiti": 2000},
    "laboratuvar": {"viral_esik": 10000, "min_veri_gunu": 7},
    "optimizasyon": {"yari_omur_gun": 45, "benzerlik_esigi": 0.6,
                     "deneyler": {"baslik_stili": ["soru", "sayili_liste", "nasil", "carpici_gercek"],
                                  "hedef_kelime": [800, 1100, 1400],
                                  "yayin_saati": ["12:00", "18:00", "20:30"]}},
    "cloudflare": {"web_analytics_token": "", "adsense_yayinci_id": ""},
    "teklifler": {"otomatik_yanit": False},
}
SECENEKLER = {
    ("llm", "saglayici"): {"otomatik", "yerel", "claude"},
    ("youtube", "gizlilik"): {"private", "zamanla"},
}


class AyarHatasi(SystemExit):
    pass


def _birlestir(taban: dict, ust: dict) -> dict:
    sonuc = dict(taban)
    for k, v in (ust or {}).items():
        sonuc[k] = _birlestir(taban[k], v) if isinstance(v, dict) and isinstance(taban.get(k), dict) else v
    return sonuc


def _yaml_oku(dosya: Path) -> dict:
    try:
        veri = yaml.safe_load(dosya.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        isaret = getattr(e, "problem_mark", None)
        yer = f"{isaret.line + 1}. satır" if isaret else "bilinmeyen satır"
        raise AyarHatasi(
            f"\n❌ {dosya.name} dosyasında yazım hatası ({yer}).\n"
            "İpuçları: girintiler boşlukla yapılmalı (TAB değil), ':' işaretinden sonra bir boşluk olmalı,\n"
            "içinde ':' veya '#' geçen metinler tırnak içine alınmalı. Ayrıntı: " + str(e).splitlines()[0]) from None
    if not isinstance(veri, dict):
        raise AyarHatasi(f"\n❌ {dosya.name} beklenen biçimde değil (anahtar: değer satırları olmalı).")
    return veri


def yukle(deneme: bool = False) -> Ayarlar:
    genel = _birlestir(VARSAYILAN, _yaml_oku(CONFIG / "ayarlar.yaml"))
    varliklar = _yaml_oku(CONFIG / "varliklar.yaml")
    for (bolum, anahtar), gecerli in SECENEKLER.items():
        if genel[bolum][anahtar] not in gecerli:
            raise AyarHatasi(f"\n❌ ayarlar.yaml > {bolum}.{anahtar} = '{genel[bolum][anahtar]}' geçersiz. "
                             f"Seçenekler: {', '.join(sorted(gecerli))}")
    for n in varliklar.get("nisler") or []:
        if not isinstance(n, dict) or not n.get("kod") or not n.get("tohum_kelimeler"):
            raise AyarHatasi("\n❌ varliklar.yaml > nisler: her nişin 'kod' ve 'tohum_kelimeler' alanı olmalı.")
        n.setdefault("ad", n["kod"])
        n.setdefault("hedef_kitle", "Genel izleyici")
        n.setdefault("alan_adi", "")
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


def uyari_ekle(kategori: str, metin: str) -> None:
    """Sınıra takılma/yedeğe geçme gibi olayları kaydeder; DURUM.md panelinde gösterilir."""
    log.warning("[%s] %s", kategori, metin)
    yol = VERI / "uyarilar.json"
    liste = json_oku(yol, [])
    zaman = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M")
    if liste and liste[-1].get("metin") == metin:   # aynı uyarıyı üst üste yazma
        liste[-1]["zaman"] = zaman
    else:
        liste.append({"zaman": zaman, "kategori": kategori, "metin": metin})
    json_yaz(yol, liste[-40:])


def ozet_yaz(metin: str) -> None:
    """GitHub Actions iş özetine (Summary sekmesi) Markdown yazar; yerelde ekrana basar."""
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(metin + "\n")
    else:
        print(metin)
