"""Dinamik optimizasyon motoru — laboratuvarın beyni (saf Python, ek kütüphane yok).

1. THOMPSON ÖRNEKLEMESİ (Bayesçi çok kollu haydut)
   Her seçenek ("kol") için başarı dağılımı Beta(α, β) tutulur. Her karar anında her koldan
   rastgele bir örnek çekilir, en yükseği seçilir. Veri azken dağılımlar geniştir -> doğal keşif;
   veri biriktikçe kazanan kola yoğunlaşır. Sabit "%20 keşif" kuralından daha verimlidir.
2. ZAMAN AŞINMASI
   Her gözlemin ağırlığı yaşıyla üstel azalır (yarı ömür). İzleyici zevki değişirse sistem uyum sağlar.
3. YAŞA GÖRE DÜZELTİLMİŞ PERFORMANS
   Kanalın kendi verisiyle log(izlenme) = a + b·log(yaş) eğrisi kurulur; videonun bu eğriye göre
   ne kadar üstte/altta olduğu (artık) ölçülür. 3 günlük video ile 60 günlük video adil karşılaştırılır.
4. TREND MOMENTUMU
   Arama önerileri haftadan haftaya karşılaştırılır; yeni çıkan veya sırası yükselen konular öne alınır.
5. ÇEŞİTLİLİK
   Kelime kümesi benzerliği (Jaccard) ile yayınlanmışa çok benzeyen konular elenir.
"""
from __future__ import annotations

import math
import random
import re
from collections import defaultdict
from datetime import date, datetime

from .ayarlar import kisa_ad

# ------------------------------------------------------------------ Thompson


def agirlik(yas_gun: float, yari_omur: float) -> float:
    return 0.5 ** (max(0.0, yas_gun) / max(1.0, yari_omur))


def posterior(gozlemler: list[tuple[str, float, float]], kollar: list, yari_omur: float) -> dict:
    """gozlemler: [(kol, başarı 0-1, yaş_gün)] -> {kol: (α, β, etkin_gözlem)}. Önsel: Beta(1, 1)."""
    sonuc = {str(k): [1.0, 1.0, 0.0] for k in kollar}
    for kol, basari, yas in gozlemler:
        if str(kol) not in sonuc:
            continue
        w = agirlik(yas, yari_omur)
        b = min(1.0, max(0.0, basari))
        sonuc[str(kol)][0] += w * b
        sonuc[str(kol)][1] += w * (1 - b)
        sonuc[str(kol)][2] += w
    return {k: tuple(v) for k, v in sonuc.items()}


def thompson_sec(post: dict, rng: random.Random) -> str:
    return max(post, key=lambda k: rng.betavariate(post[k][0], post[k][1]))


def kazanma_olasiligi(post: dict, ornek: int = 2000, tohum: int = 7) -> dict[str, float]:
    """Monte Carlo ile her kolun 'en iyi olma' olasılığı (DURUM.md'de gösterilir)."""
    rng = random.Random(tohum)
    sayac: dict[str, int] = defaultdict(int)
    for _ in range(ornek):
        sayac[thompson_sec(post, rng)] += 1
    return {k: round(sayac[k] / ornek, 3) for k in post}


# --------------------------------------------------------- yaşa göre puan


def yas_duzeltilmis(videolar: list[dict]) -> list[float]:
    """log(izlenme+1) ~ a + b·log(yaş+1) en küçük kareler; döner: her videonun artığı (eğriden sapma)."""
    xs = [math.log(v["yas_gun"] + 1) for v in videolar]
    ys = [math.log(v["goruntulenme"] + 1) for v in videolar]
    n = len(videolar)
    if n < 3 or max(xs) - min(xs) < 1e-9:  # eğri kurulamaz: günlük hız kullan
        return [math.log(v["goruntulenme"] / max(1, v["yas_gun"]) + 1) for v in videolar]
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    b = min(1.5, max(0.1, b))  # aşırı uç eğimleri sınırla (az veride kararlılık)
    a = my - b * mx
    return [y - (a + b * x) for x, y in zip(xs, ys)]


# --------------------------------------------------------------- trend

def trend_bonusu(simdiki: dict[str, float], onceki: dict[str, float]) -> dict[str, float]:
    """Yeni çıkan konuya +0,15; talebi artana artış oranında (en fazla +0,15) bonus."""
    if not onceki:
        return {}
    onceki_ad = {kisa_ad(k, 80): v for k, v in onceki.items()}
    bonus = {}
    for konu, talep in simdiki.items():
        eski = onceki_ad.get(kisa_ad(konu, 80))
        if eski is None:
            bonus[konu] = 0.15
        elif talep > eski:
            bonus[konu] = round(min(0.15, 0.15 * (talep - eski) / max(eski, 0.1)), 3)
    return bonus


# ----------------------------------------------------------- çeşitlilik

_DOLGU = {"ve", "ile", "icin", "bir", "bu", "mi", "mu", "nasil", "nedir", "neden", "en", "iyi", "da", "de",
          "the", "a", "of", "to", "how", "ne", "ki", "gibi", "kadar", "olan", "yapilir", "yapmali"}


def kelimeler(metin: str) -> set[str]:
    """Kaba Türkçe kök: çift harfler teke indirilir (arttırmak = artırmak), ilk 6 harf alınır."""
    return {re.sub(r"(.)\1", r"\1", k)[:6] for k in kisa_ad(metin, 200).split("-")
            if k and k not in _DOLGU and len(k) > 1}


def benzerlik(a: str, b: str) -> float:
    ka, kb = kelimeler(a), kelimeler(b)
    return len(ka & kb) / len(ka | kb) if ka and kb else 0.0


def cesitlendir(adaylar: list[dict], gecmis: list[str], esik: float = 0.6, alan: str = "konu") -> list[dict]:
    """Geçmişe veya listede daha önceki bir adaya çok benzeyen konuları çıkarır (sırayı korur)."""
    secilen: list[dict] = []
    for a in adaylar:
        if any(benzerlik(a[alan], g) >= esik for g in gecmis):
            continue
        if any(benzerlik(a[alan], s[alan]) >= esik for s in secilen):
            continue
        secilen.append(a)
    return secilen


# ------------------------------------------------------------- deneyler

BASLIK_STILLERI = {
    "soru": "Başlık bir soru olsun (ör. 'Neden ... ?').",
    "sayili_liste": "Başlıkta bir sayı olsun (ör. '5 Basit Yöntem').",
    "nasil": "Başlık 'Nasıl' ile başlayan bir rehber olsun.",
    "carpici_gercek": "Başlık şaşırtıcı ama doğru bir gerçeği vurgulasın (abartısız).",
}


def deney_secimleri(deneyler: dict[str, list], istatistik: dict, rng: random.Random, yari_omur: float) -> dict:
    """Her deney için Thompson ile bir kol seçer. istatistik: {deney: [(kol, başarı, yaş)]}"""
    secim = {}
    for ad, kollar in deneyler.items():
        if kollar:
            secim[ad] = thompson_sec(posterior(istatistik.get(ad, []), kollar, yari_omur), rng)
    return secim


def gozlemleri_topla(olgun_videolar: list[dict], icerik_oku) -> dict[str, list]:
    """Değerlendirilmiş videolardan deney gözlemleri: {deney: [[kol, skor/100, yayın_tarihi]]} (JSON'a uygun)."""
    sonuc: dict[str, list] = defaultdict(list)
    for v in olgun_videolar:
        if v.get("tur") != "uzun" or "skor" not in v:
            continue
        tarih, basari = v["tarih"][:10], round(v["skor"] / 100, 4)
        sonuc["nis"].append([v["nis"], basari, tarih])
        for ad, kol in ((icerik_oku(v["kod"]) or {}).get("plan", {}).get("deney") or {}).items():
            sonuc[ad].append([str(kol), basari, tarih])
    return dict(sonuc)


def yasli(gozlemler: list, bugun: date) -> list[tuple[str, float, float]]:
    """Kaydedilmiş gözlemleri bugünkü yaşlarıyla Thompson girdisine çevirir (aşınma her gün güncel)."""
    return [(str(k), float(b), (bugun - datetime.fromisoformat(t).date()).days) for k, b, t in gozlemler]
