"""MODÜL 2 — Niş ve pazar analizi.

Ücretsiz veri kaynakları:
  * YouTube otomatik tamamlama önerileri (anahtarsız): insanların gerçekten ne aradığını gösterir.
  * YouTube Data API (ücretsiz kota, isteğe bağlı): ilk sıradaki videoların izlenmesi ve
    kanal büyüklüğü -> rekabet. Küçük kanalların çok izlendiği konular = fırsat.
Uydurma "arama hacmi" sayısı üretilmez; tüm puanlar ölçülen sinyallerden gelir.
"""
from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict

import requests

from .ayarlar import VERI, Ayarlar, gizli, json_yaz, kisa_ad, log

EKLER = ["", " nasıl", " nedir", " için", " neden", " en iyi"]
ONERI_URL = "https://suggestqueries.google.com/complete/search"
YT_API = "https://www.googleapis.com/youtube/v3"


def oneriler(sorgu: str) -> list[str]:
    try:
        r = requests.get(
            ONERI_URL, params={"client": "firefox", "ds": "yt", "hl": "tr", "gl": "tr", "q": sorgu}, timeout=10
        )
        r.raise_for_status()
        return [s for s in r.json()[1] if isinstance(s, str)]
    except (requests.RequestException, ValueError, IndexError) as e:
        log.warning("Öneri alınamadı (%s): %s", sorgu, e)
        return []


def talep_puanlari(tohumlar: list[str], bekle: float = 0.25) -> dict[str, float]:
    """Her öneriye sırasına göre puan verir; birden çok sorguda çıkan konu daha değerlidir."""
    puan: dict[str, float] = defaultdict(float)
    gorunen: dict[str, str] = {}
    for tohum in tohumlar:
        for ek in EKLER:
            for sira, oneri in enumerate(oneriler(tohum + ek)):
                anahtar = kisa_ad(oneri, 80)
                gorunen.setdefault(anahtar, oneri)
                puan[anahtar] += (10 - min(sira, 9)) / 10
            time.sleep(bekle)
    return {gorunen[k]: v for k, v in puan.items()}


def _rekabet(konu: str, anahtar: str) -> dict:
    """~102 kota birimi. Döner: medyan izlenme, medyan abone, küçük kanal başarı oranı."""
    try:
        ara = requests.get(f"{YT_API}/search", params={
            "part": "snippet", "q": konu, "type": "video", "maxResults": 10,
            "regionCode": "TR", "relevanceLanguage": "tr", "key": anahtar}, timeout=15).json()
        vid = [i["id"]["videoId"] for i in ara.get("items", [])]
        kan = list({i["snippet"]["channelId"] for i in ara.get("items", [])})
        if not vid:
            return {}
        v = requests.get(f"{YT_API}/videos", params={
            "part": "statistics,snippet", "id": ",".join(vid), "key": anahtar}, timeout=15).json()
        c = requests.get(f"{YT_API}/channels", params={
            "part": "statistics", "id": ",".join(kan), "key": anahtar}, timeout=15).json()
        abone = {i["id"]: int(i["statistics"].get("subscriberCount", 0)) for i in c.get("items", [])}
        izl, abo, kucuk_basari = [], [], 0
        for i in v.get("items", []):
            g = int(i["statistics"].get("viewCount", 0))
            a = abone.get(i["snippet"]["channelId"], 0)
            izl.append(g)
            abo.append(a)
            if a < 20_000 and g > 5_000:
                kucuk_basari += 1
        return {
            "medyan_izlenme": int(statistics.median(izl)) if izl else 0,
            "medyan_abone": int(statistics.median(abo)) if abo else 0,
            "kucuk_kanal_orani": round(kucuk_basari / max(1, len(izl)), 2),
        }
    except (requests.RequestException, ValueError, KeyError) as e:
        log.warning("Rekabet ölçülemedi (%s): %s", konu, e)
        return {}


def firsat_puani(talep_norm: float, rekabet: dict) -> tuple[float, str]:
    if not rekabet:
        return round(talep_norm, 3), "bilinmiyor"
    rek = min(1.0, math.log10(rekabet["medyan_abone"] + 1) / 7)   # 10M abone ≈ 1.0
    etiket = "düşük" if rek < 0.5 else "orta" if rek < 0.72 else "yüksek"
    puan = 0.5 * talep_norm + 0.3 * (1 - rek) + 0.2 * rekabet["kucuk_kanal_orani"]
    return round(puan, 3), etiket


def _sahte(nis: dict) -> dict[str, float]:
    return {f"{t} {e}".strip(): 5.0 - i * 0.3 for i, t in enumerate(nis["tohum_kelimeler"]) for e in ("nedir", "ipuçları")}


def calistir(ayar: Ayarlar, konu_basina_rekabet: int = 5) -> dict[str, list[dict]]:
    anahtar = "" if ayar.deneme else gizli("YOUTUBE_API_KEY")
    sonuc: dict[str, list[dict]] = {}
    for nis in ayar.nisler:
        ham = _sahte(nis) if ayar.deneme else talep_puanlari(nis["tohum_kelimeler"])
        if not ham:
            continue
        en_yuksek = max(ham.values())
        adaylar = sorted(ham.items(), key=lambda x: -x[1])[:20]
        liste = []
        for sira, (konu, p) in enumerate(adaylar):
            rek = _rekabet(konu, anahtar) if (anahtar and sira < konu_basina_rekabet) else {}
            firsat, etiket = firsat_puani(p / en_yuksek, rek)
            liste.append({"konu": konu, "talep": round(p / en_yuksek, 3), "rekabet": etiket,
                          "firsat": firsat, **rek})
        liste.sort(key=lambda x: -x["firsat"])
        sonuc[nis["kod"]] = liste
        log.info("Niş %s: %d aday konu", nis["kod"], len(liste))
    json_yaz(VERI / "nis_analizi.json", sonuc)
    return sonuc
