"""MODÜL 3 — YouTube içerik planı.

Verimlilik: 4 haftalık sabit takvim yerine HER HAFTA güncel veriyle yenilenen plan.
Laboratuvarın (Modül 11) ölçtüğü niş başarısına göre videolar nişlere dağıtılır;
bir kısmı (keşif oranı) yeni şeyler denemeye ayrılır. Viral videoların devamı önceliklidir.
"""
from __future__ import annotations

import random

from . import llm
from .ayarlar import VERI, Ayarlar, csv_oku, json_oku, json_yaz, kisa_ad, log

PLAN_SEMASI = {
    "type": "object",
    "properties": {
        "videolar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nis": {"type": "string", "description": "niş kodu"},
                    "konu": {"type": "string"},
                    "anahtar_kelime": {"type": "string", "description": "insanların aradığı ana ifade"},
                    "aci": {"type": "string", "description": "bu videoyu rakiplerden ayıran özgün bakış açısı"},
                    "hedef_kitle": {"type": "string"},
                    "basliklar": {"type": "array", "items": {"type": "string"},
                                  "description": "3 alternatif başlık, en fazla 70 karakter, anahtar kelime başta"},
                },
                "required": ["nis", "konu", "anahtar_kelime", "aci", "hedef_kitle", "basliklar"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["videolar"],
    "additionalProperties": False,
}

SISTEM = """Sen Türkçe YouTube kanalları için içerik stratejistisin.
Kurallar:
- Yalnızca verilen aday konulardan (gerçek arama önerilerinden) seç; gerekirse birleştir/daralt.
- Her video için gerçekten faydalı, özgün bir bakış açısı bul (liste/özet tekrarı değil).
- Başlıklar merak uyandırsın ama yanıltıcı olmasın; vaat edilen şey videoda verilsin.
- Sağlık konularında teşhis/tedavi vaadi yok; bilimsel ve sorumlu dil.
- Daha önce yayınlanan başlıkları tekrar etme."""


def dagit(nis_kodlari: list[str], agirliklar: dict[str, float], adet: int, kesif: float, rng: random.Random) -> list[str]:
    """Çok kollu haydut (epsilon-greedy) mantığı: kazananlara daha çok, ama keşfi bırakmadan."""
    if not nis_kodlari:
        return []
    w = [max(0.01, agirliklar.get(k, 1.0)) for k in nis_kodlari]
    secim = []
    for _ in range(adet):
        if rng.random() < kesif:
            secim.append(rng.choice(nis_kodlari))
        else:
            secim.append(rng.choices(nis_kodlari, weights=w, k=1)[0])
    return secim


def calistir(ayar: Ayarlar, nis_analizi: dict[str, list[dict]] | None = None) -> list[dict]:
    yil, hafta, _ = ayar.simdi.isocalendar()
    adet = int(ayar["youtube"]["haftalik_uzun_video"])
    nis_analizi = nis_analizi if nis_analizi is not None else json_oku(VERI / "nis_analizi.json", {})
    agirlik = json_oku(VERI / "nis_agirliklari.json", {})
    oncelikli = json_oku(VERI / "oncelikli_konular.json", [])

    kodlar = [n["kod"] for n in ayar.nisler if nis_analizi.get(n["kod"])]
    rng = random.Random(yil * 100 + hafta)
    oncelik = oncelikli[:adet]
    dagilim = dagit(kodlar, agirlik, adet - len(oncelik), float(ayar["laboratuvar"]["kesif_orani"]), rng)
    if not dagilim and not oncelik:
        log.warning("Plan yapılamadı: niş analizi boş.")
        return []

    yayinlanan = [s["baslik"] for s in csv_oku(VERI / "yayinlananlar.csv")][-60:]
    istek = ["Bu hafta üretilecek videolar:"]
    for o in oncelik:
        istek.append(f"- niş={o['nis']}: ÖNCELİKLİ devam videosu -> {o['konu']}")
    for kod in dagilim:
        n = ayar.nis(kod)
        adaylar = ", ".join(a["konu"] for a in nis_analizi[kod][:15])
        istek.append(f"- niş={kod} ({n['ad']}, kitle: {n['hedef_kitle']}). Aday konular: {adaylar}")
    istek.append("\nAynı hafta içinde aynı konuyu iki kez seçme.")
    if yayinlanan:
        istek.append("Daha önce yayınlananlar (tekrar etme): " + " | ".join(yayinlanan))

    def sahte() -> dict:
        return {"videolar": [
            {"nis": k, "konu": nis_analizi[k][0]["konu"], "anahtar_kelime": nis_analizi[k][0]["konu"],
             "aci": "Deneme açısı", "hedef_kitle": ayar.nis(k)["hedef_kitle"],
             "basliklar": [f"{nis_analizi[k][0]['konu'].title()} {i}" for i in range(3)]}
            for k in [o["nis"] for o in oncelik] + dagilim]}

    cevap = llm.json_uret(ayar, f"plan-{yil}-H{hafta}", SISTEM, "\n".join(istek), PLAN_SEMASI, sahte,
                          max_tokens=8000)
    gecerli = {n["kod"] for n in ayar.nisler}
    plan = []
    for i, v in enumerate(cevap["videolar"][:adet]):
        if v["nis"] not in gecerli:
            v["nis"] = (dagilim or [o["nis"] for o in oncelik])[0]
        v["kod"] = f"{yil}h{hafta:02d}-{i + 1}-{kisa_ad(v['konu'], 40)}"
        v["basliklar"] = [b[:100] for b in v["basliklar"]][:3] or [v["konu"]]
        plan.append(v)

    json_yaz(VERI / "plan" / f"{yil}-H{hafta:02d}.json", plan)
    if oncelik:  # kullanılan öncelikli konuları kuyruktan çıkar
        json_yaz(VERI / "oncelikli_konular.json", oncelikli[len(oncelik):])
    _takvim_yaz(ayar)
    log.info("Plan: %d video", len(plan))
    return plan


def _takvim_yaz(ayar: Ayarlar) -> None:
    satir = ["# İçerik Takvimi", "", "| Hafta | Niş | Konu | Başlık seçenekleri |", "|---|---|---|---|"]
    for dosya in sorted((VERI / "plan").glob("*.json"))[-4:]:
        for v in json_oku(dosya, []):
            satir.append(f"| {dosya.stem} | {v['nis']} | {v['konu']} | {' / '.join(v['basliklar'])} |")
    (VERI / "icerik_takvimi.md").write_text("\n".join(satir) + "\n", encoding="utf-8")
