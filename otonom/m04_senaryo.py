"""MODÜL 4 — Senaryo + metadata + Shorts + blog yazısı (TEK çağrıda).

Bir istek -> 1 uzun video + N Shorts + 1 site makalesi + başlık/açıklama/etiketler.
Böylece aynı maliyetle 3 farklı gelir kanalını besleyen içerik çıkar.
"""
from __future__ import annotations

import re

from .ayarlar import CIKTI, VERI, Ayarlar, json_oku, json_yaz, log

SENARYO_SEMASI = {
    "type": "object",
    "properties": {
        "baslik": {"type": "string", "description": "en fazla 70 karakter, anahtar kelime başta, yanıltıcı değil"},
        "alternatif_basliklar": {"type": "array", "items": {"type": "string"}, "description": "2 adet, A/B testi için"},
        "thumbnail_yazi": {"type": "string", "description": "küçük resimde yazacak 2-4 kelime, BÜYÜK HARF değil"},
        "aciklama": {"type": "string", "description": "YouTube açıklaması: ilk cümle anahtar kelimeyi içerir, 3-5 cümle özet. Link ekleme."},
        "etiketler": {"type": "array", "items": {"type": "string"}, "description": "8 etiket, # işaretsiz"},
        "sahneler": {
            "type": "array",
            "description": "videonun tamamı; her sahne 2-4 cümle (yaklaşık 15-30 saniye)",
            "items": {
                "type": "object",
                "properties": {
                    "metin": {"type": "string", "description": "seslendirilecek metin, konuşma dili, kısa cümleler"},
                    "gorsel_arama": {"type": "string", "description": "stok fotoğraf aramak için 2-4 kelimelik İNGİLİZCE ifade"},
                    "bolum": {"type": "string", "description": "yeni bölüm başlıyorsa kısa bölüm adı, yoksa boş"},
                },
                "required": ["metin", "gorsel_arama", "bolum"],
                "additionalProperties": False,
            },
        },
        "shorts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "baslik": {"type": "string", "description": "en fazla 60 karakter"},
                    "metin": {"type": "string", "description": "90-120 kelime; ilk cümle güçlü kanca; sonunda uzun videoya davet"},
                    "gorsel_arama": {"type": "string", "description": "İngilizce 2-4 kelime"},
                },
                "required": ["baslik", "metin", "gorsel_arama"],
                "additionalProperties": False,
            },
        },
        "makale": {
            "type": "object",
            "properties": {
                "baslik": {"type": "string"},
                "meta_aciklama": {"type": "string", "description": "en fazla 155 karakter"},
                "govde_md": {"type": "string", "description": "Markdown; ## alt başlıklar, madde listeleri ve sonda 'Sık Sorulan Sorular' bölümü"},
            },
            "required": ["baslik", "meta_aciklama", "govde_md"],
            "additionalProperties": False,
        },
    },
    "required": ["baslik", "alternatif_basliklar", "thumbnail_yazi", "aciklama", "etiketler", "sahneler", "shorts", "makale"],
    "additionalProperties": False,
}

# Sabit sistem talimatı: tüm isteklerde aynı -> önbelleğe alınır.
SISTEM = """Sen Türkçe eğitici YouTube videoları yazan deneyimli bir senaristsin.

ÜSLUP
- Samimi, konuşma diline yakın, kısa ve net cümleler. Okuyucuya "sen" diye hitap et.
- Seslendirme yapay sesle okunacak: kısaltma, emoji, parantez, madde işareti, URL kullanma.
  Sayıları okunacak şekilde yaz (ör. "yüzde yirmi").
- İlk sahne güçlü bir kanca: izleyicinin sorununu ilk 2 cümlede söyle ve videonun sonunda
  ne kazanacağını vaat et. "Merhaba arkadaşlar" gibi boş girişler yok.
- Gelişme 3-5 bölüm; her bölümde somut örnek, uygulanabilir adım veya şaşırtıcı bir bilgi.
- Ortalarda bir kez kısa bir izlenme kancası ("birazdan en önemli hatayı anlatacağım" gibi).
- Son sahnede kısa özet + tek bir net çağrı: yorum sorusu, abone ol ve açıklamadaki siteye git.

ÖZGÜNLÜK VE POLİTİKA
- Tamamen özgün cümleler kur; başka kaynaklardan kopyalama.
- Kesin bilmediğin istatistik, isim veya araştırma uydurma; emin değilsen genel ifade kullan.
- Sağlık konularında teşhis/tedavi önerme; gerekirse uzmana yönlendir.
- Başlık ve küçük resim yazısı içerikte gerçekten verilen şeyi vaat etsin (clickbait yasak).

SHORTS: uzun videodaki en ilginç bilgiden bağımsız, kendi başına anlamlı kısa metinler.
MAKALE: aynı konuyu okuyucu için yeniden düzenle (videonun dökümü değil); arama motoru için
faydalı, alt başlıklı, 600-900 kelime, sonda 3 soruluk SSS."""


def istek_olustur(ayar: Ayarlar, v: dict) -> dict:
    nis = ayar.nis(v["nis"])
    site = nis.get("alan_adi") or ""
    deney = v.get("deney") or {}
    hedef = int(deney.get("hedef_kelime") or ayar["youtube"]["hedef_kelime"])
    from .optimizasyon import BASLIK_STILLERI
    stil = BASLIK_STILLERI.get(deney.get("baslik_stili", ""), "")
    sahne = max(4, round(hedef / 75))
    istem = f"""Konu: {v['konu']}
Ana anahtar kelime: {v['anahtar_kelime']}
Özgün bakış açısı: {v['aci']}
Hedef kitle: {v.get('hedef_kitle') or nis['hedef_kitle']}
Kanal nişi: {nis['ad']}
Başlık fikirleri: {' | '.join(v['basliklar'])}
{("Başlık kuralı (deney): " + stil) if stil else ""}
{"İzleyiciyi şu siteye davet et: " + site if site else ""}

Uzun video toplam {hedef - 100}-{hedef + 100} kelime olsun: tam {sahne} sahne yaz,
her sahne 4-6 cümle (yaklaşık 75 kelime). Kısa kesme; her bölümde örnek ve açıklama ver.
gorsel_arama alanlarını İNGİLİZCE 2-4 kelime yaz (ör. "student studying desk").
Site adresini seslendirme metninde yazma; "açıklamadaki link" de.
{ayar['youtube']['video_basina_shorts']} adet Shorts metni yaz."""
    return {"id": v["kod"], "sistem": SISTEM, "istem": istem, "sema": SENARYO_SEMASI,
            "efor": ayar["llm"]["senaryo_efor"], "max_tokens": 16000}


def sahte_icerik(v: dict, shorts: int = 2) -> dict:
    cumle = "Bu bir deneme cümlesidir ve sistemin uçtan uca çalıştığını gösterir."
    return {
        "baslik": f"{v['konu'].title()} — Deneme",
        "alternatif_basliklar": ["Alternatif 1", "Alternatif 2"],
        "thumbnail_yazi": "Deneme Videosu",
        "aciklama": f"{v['anahtar_kelime']} hakkında deneme açıklaması.",
        "etiketler": [v["anahtar_kelime"], "deneme", "eğitim"],
        "sahneler": [
            {"metin": f"{cumle} Sahne {i + 1}.", "gorsel_arama": "brain science", "bolum": b}
            for i, b in enumerate(["Giriş", "", "Asıl konu", "Sonuç"])
        ],
        "shorts": [{"baslik": f"Kısa {i + 1}", "metin": cumle, "gorsel_arama": "brain"} for i in range(shorts)],
        "makale": {"baslik": v["konu"].title(), "meta_aciklama": "Deneme makalesi.",
                   "govde_md": "## Giriş\n\nDeneme metni.\n\n## Sık Sorulan Sorular\n\n**Soru?** Cevap."},
    }


ALAN_ADI = re.compile(r"\b[\w-]+(?:\.(?:com|net|org|tr|io|ai))+(?:'[a-zçğıöşü]+)?\b", re.IGNORECASE)
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


def _seslendirilebilir(metin: str) -> str:
    """Yapay sesin tökezleyeceği şeyleri temizler: site adresi, emoji, fazla boşluk."""
    metin = ALAN_ADI.sub("açıklamadaki link", metin)
    return re.sub(r"\s+", " ", EMOJI.sub("", metin)).strip()


def _temizle(icerik: dict) -> dict:
    """Platform sınırlarını kodla garanti et (model hatasına güvenme; küçük yerel modeller için şart)."""
    icerik["baslik"] = EMOJI.sub("", icerik["baslik"]).strip()[:100]
    icerik["thumbnail_yazi"] = EMOJI.sub("", icerik["thumbnail_yazi"]).strip()
    for s in icerik["sahneler"] + icerik["shorts"]:
        s["metin"] = _seslendirilebilir(s["metin"])
        s["gorsel_arama"] = " ".join(s["gorsel_arama"].split()[:4])
    etiketler, toplam = [], 0
    for e in icerik["etiketler"]:
        e = e.replace("#", "").strip()
        if e and toplam + len(e) + 1 <= 450:
            etiketler.append(e)
            toplam += len(e) + 1
    icerik["etiketler"] = etiketler[:10]
    icerik["sahneler"] = [s for s in icerik["sahneler"] if s["metin"].strip()]
    if icerik["sahneler"] and not icerik["sahneler"][0]["bolum"]:
        icerik["sahneler"][0]["bolum"] = "Giriş"
    return icerik


def kaydet(ayar: Ayarlar, v: dict, icerik: dict) -> dict:
    icerik = _temizle(icerik)
    icerik["plan"] = v
    icerik["kelime"] = sum(len(s["metin"].split()) for s in icerik["sahneler"])
    json_yaz(VERI / "videolar" / v["kod"] / "icerik.json", icerik)
    (CIKTI / v["kod"]).mkdir(parents=True, exist_ok=True)
    (CIKTI / v["kod"] / "senaryo.txt").write_text(
        "\n\n".join(s["metin"] for s in icerik["sahneler"]), encoding="utf-8")
    log.info("Senaryo hazır: %s (%d kelime)", v["kod"], icerik["kelime"])
    return icerik


def yukle(kod: str) -> dict | None:
    return json_oku(VERI / "videolar" / kod / "icerik.json")
