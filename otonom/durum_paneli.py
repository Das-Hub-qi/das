"""DURUM.md — her çalıştırmada güncellenen, telefondan bile okunabilen Türkçe kontrol paneli.

Ne kurulu, ne eksik (ve nasıl tamamlanır), ücretsiz sınırların ne kadarı kullanıldı,
son üretilen videolar ve son uyarılar tek sayfada. Dış servise istek atmaz (kota harcamaz).
"""
from __future__ import annotations

from collections import Counter

from . import butce, llm
from .ayarlar import CONFIG, VERI, Ayarlar, csv_oku, gizli, json_oku, ozet_yaz
from .m09_youtube_yukleme import GUNLUK_KOTA, KOTA_DOSYASI, _kota_gunu, kimlik_var

TAMAM, EKSIK, UYARI = "✅", "❌", "⚠️"


def kurulum_listesi(ayar: Ayarlar) -> list[tuple[str, str, str, str]]:
    """(simge, parça, durum, ne yapmalı) satırları."""
    v = ayar.varliklar
    s = []
    if llm.saglayici(ayar) == "claude":
        s.append((TAMAM, "Yapay zekâ", "Claude Haiku 5.5 (kredi biterse yerel modele otomatik geçer)", "—"))
    else:
        s.append((TAMAM, "Yapay zekâ", f"Ücretsiz yerel model ({ayar['llm']['yerel_dosya'].split('-Q')[0]})",
                  "İsteğe bağlı: daha kaliteli metin için `ANTHROPIC_API_KEY` (README adım 1)"))
    s.append((TAMAM, "Seslendirme", "Edge TTS (yedek: çevrimdışı Piper)", "—"))
    if gizli("PEXELS_API_KEY") or gizli("PIXABAY_API_KEY"):
        s.append((TAMAM, "Görseller", "Pexels/Pixabay (yedek: Openverse, yazı kartı)", "—"))
    else:
        s.append((UYARI, "Görseller", "Yalnızca anahtarsız Openverse + yazı kartı",
                  "Ücretsiz `PEXELS_API_KEY` ekleyin: görsel kalitesi artar (README adım 2)"))
    if kimlik_var():
        s.append((TAMAM, "YouTube yükleme", "Bağlı", "—"))
    else:
        s.append((EKSIK, "YouTube yükleme", "Bağlı değil — videolar Actions > Artifacts'tan indirilebilir",
                  "`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (README adım 3)"))
    s.append((TAMAM if gizli("YOUTUBE_API_KEY") else UYARI, "YouTube istatistik / rekabet",
              "Açık" if gizli("YOUTUBE_API_KEY") else "Kapalı (niş analizi yalnızca arama önerileriyle)",
              "—" if gizli("YOUTUBE_API_KEY") else "`YOUTUBE_API_KEY` (README adım 3.2)"))
    cf = gizli("CLOUDFLARE_API_TOKEN") and gizli("CLOUDFLARE_ACCOUNT_ID")
    s.append((TAMAM if cf else EKSIK, "Siteler + teklif formu (Cloudflare)", "Yayında" if cf else "Kurulmadı",
              "—" if cf else "`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (README adım 4)"))
    kanal = any(k.get("kanal_id") for k in v.get("youtube_kanallari") or [])
    s.append((TAMAM if kanal else UYARI, "Kanal kimliği", "Girildi" if kanal else "Boş",
              "—" if kanal else "`config/varliklar.yaml` > kanal_id (abone ol linki için)"))
    bos_nis = [n["ad"] for n in ayar.nisler if not n.get("alan_adi")]
    s.append((UYARI if bos_nis else TAMAM, "Nişlerin alan adları",
              ("Alan adı yok: " + ", ".join(bos_nis)) if bos_nis else "Hepsi tanımlı",
              "`config/varliklar.yaml` > nisler > alan_adi" if bos_nis else "—"))
    link = sum(len(n.get("ortaklik_linkleri") or {}) for n in ayar.nisler)
    s.append((TAMAM if link else UYARI, "Ortaklık (affiliate) linkleri", f"{link} link",
              "—" if link else "`config/varliklar.yaml` > ortaklik_linkleri (ek gelir)"))
    muzik = list((CONFIG / "muzik").glob("*.mp3"))
    s.append((TAMAM if muzik else UYARI, "Arka plan müziği", f"{len(muzik)} parça",
              "—" if muzik else "YouTube Ses Kitaplığı'ndan mp3 → `config/muzik/`"))
    return s


def olustur(ayar: Ayarlar, komut: str, hatalar: list[str]) -> str:
    zaman = ayar.simdi.strftime("%Y-%m-%d %H:%M")
    durum = (f"{UYARI} {len(hatalar)} adım hata verdi (aşağıda)" if hatalar else f"{TAMAM} Sorunsuz")
    md = ["# 📊 Sistem Durumu", "", f"_Son çalıştırma: {zaman} · komut: `{komut}` · {durum}_", ""]

    liste = kurulum_listesi(ayar)
    eksik = sum(1 for x in liste if x[0] != TAMAM)
    md += ["## Kurulum kontrol listesi",
           f"{'Her şey hazır.' if not eksik else f'{eksik} madde tamamlanabilir — sistem bunlar olmadan da çalışır.'}",
           "", "| | Parça | Durum | Ne yapmalı? |", "|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in liste]

    sinir = butce.limit(ayar)
    kota = json_oku(KOTA_DOSYASI, {}).get(_kota_gunu(), 0)
    maliyet = sum(float(x["dolar"]) for x in csv_oku(llm.MALIYET_DOSYASI))
    md += ["", "## Ücretsiz sınırlar",
           f"- GitHub dakikası (bu ay): **{butce.bu_ay(ayar):.0f}** / {sinir or 'sınırsız'}"
           + (f" · ay sonu tahmini {butce.tahmin(ayar):.0f}" if sinir else "") + f" · mod: **{ayar.mod}**",
           f"- YouTube API kotası (bugün): **{kota}** / {GUNLUK_KOTA}",
           f"- Yapay zekâ harcaması (toplam): **{maliyet:.3f} $**",
           "- Sınır dolarsa sistem durmaz: üretimi azaltır, yüklemeyi ertesi güne bırakır veya yedek servise geçer."]

    d = json_oku(VERI / "durum.json", {"kuyruk": [], "bekleyen_toplu": None})
    say = Counter(i["durum"] for i in d.get("kuyruk", []))
    md += ["", "## Üretim",
           f"- Bekleyen: **{say.get('bekliyor', 0)}** · yüklendi: {say.get('yuklendi', 0)} · "
           f"elle yüklenecek: {say.get('elle_yukle', 0)} · hata: {say.get('hata', 0)}",
           f"- Yapay zekâda bekleyen toplu iş: {'var' if d.get('bekleyen_toplu') else 'yok'}"]
    yayin = csv_oku(VERI / "yayinlananlar.csv")[-8:]
    if yayin:
        md += ["", "| Tarih | Tür | Başlık |", "|---|---|---|"]
        for y in reversed(yayin):
            link = (f"[{y['baslik'][:60]}](https://youtu.be/{y['youtube_id']})"
                    if y["youtube_id"] and not y["youtube_id"].startswith("DENEME") else y["baslik"][:60])
            md.append(f"| {y['tarih'][:10]} | {y['tur']} | {link} |")

    ay = ayar.simdi.strftime("%Y-%m")
    teklif = [t for t in csv_oku(VERI / "teklifler.csv") if t["tarih"].startswith(ay)]
    tik = sum(int(t["tiklama"]) for t in csv_oku(VERI / "tiklamalar.csv") if t["tarih"].startswith(ay))
    md += ["", "## Gelir (bu ay)", f"- Alan adı teklifleri: **{len(teklif)}**"
           + (" → yanıt taslakları `veri/teklif_taslaklari/`" if teklif else ""),
           f"- Ortaklık link tıklamaları: **{tik}**",
           "- Ayrıntılı raporlar: `veri/raporlar/`"]

    uyarilar = json_oku(VERI / "uyarilar.json", [])[-8:]
    if hatalar or uyarilar:
        md += ["", "## Son uyarılar"]
        md += [f"- ❗ {h}" for h in hatalar]
        md += [f"- {u['zaman']} · {u['kategori']}: {u['metin']}" for u in reversed(uyarilar)]

    md += ["", "## Otomatik takvim (Türkiye saati)",
           "- Pazartesi 09:17 — haftalık plan ve senaryolar · Pazartesi 13:37 — video üretimi",
           "- Her gün 07:07 — yükleme, teklifler, site güncellemesi",
           "- Elle çalıştırmak için: GitHub > Actions > Otonom sistem > Run workflow", ""]
    return "\n".join(md)


def yaz(ayar: Ayarlar, komut: str, hatalar: list[str]) -> str:
    metin = olustur(ayar, komut, hatalar)
    (VERI.parent / "DURUM.md").write_text(metin, encoding="utf-8")
    ozet_yaz(metin)
    return metin
