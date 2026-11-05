"""Otomasyon orkestrasyonu — haftalık ve günlük döngüler.

İki aşamalı tasarım (GitHub Actions dakikalarını ve yapay zekâ maliyetini korur):
  HAFTALIK (Pzt 09:00): analiz -> niş -> plan -> senaryo isteği (toplu, %50 ucuz) -> alan adı -> site
  GÜNLÜK  (07:00, Pzt 13:00 ek): toplu sonucu al -> ses/görsel/montaj -> YouTube'a yükle (kotaya göre)
                                 -> viral kontrolü -> teklifler/tıklamalar -> site güncelle
Her adım ayrı korunur: biri hata verirse diğerleri çalışır, sonunda iş "başarısız" işaretlenir
ve GitHub size ücretsiz e-posta bildirimi gönderir.
"""
from __future__ import annotations

import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from . import (buyume, gorsel, llm, m01_envanter, m02_nis_analizi, m03_icerik_plani, m04_senaryo,
               m05_seslendirme, m06_materyal, m07_montaj, m08_thumbnail_metadata, m09_youtube_yukleme, m10_alan_adi,
               m11_analiz, m12_gelir, mikro_site)
from .ayarlar import CIKTI, KANAL_VERI as VERI, Ayarlar, csv_ekle, json_oku, json_yaz, log, ozet_yaz, uyari_ekle

DURUM = VERI / "durum.json"
YAYIN_ALANLARI = ["tarih", "kod", "nis", "tur", "sira", "youtube_id", "baslik", "yayin_zamani", "sure_sn", "kelime"]


def _durum() -> dict:
    return json_oku(DURUM, {"bekleyen_toplu": None, "kuyruk": []})


def _kuyruga_ekle(durum: dict, ayar: Ayarlar, kod: str, icerik: dict) -> None:
    """Kanalın biçimine göre: uzun_ve_shorts | sadece_shorts | sadece_uzun."""
    bicim = ayar.kanal_bilgi.get("bicim", "uzun_ve_shorts")
    if bicim != "sadece_shorts":
        durum["kuyruk"].append({"kod": kod, "tur": "uzun", "sira": 0, "durum": "bekliyor"})
    if bicim != "sadece_uzun":
        for j in range(len(icerik["shorts"])):
            durum["kuyruk"].append({"kod": kod, "tur": "shorts", "sira": j, "durum": "bekliyor"})


# ------------------------------------------------------------- senaryo

def senaryo_asamasi(ayar: Ayarlar, plan: list[dict]) -> None:
    durum = _durum()
    if not plan:
        return
    anlik = list(plan)
    if llm.toplu_mu(ayar):
        if durum.get("bekleyen_toplu"):
            log.warning("Önceki toplu iş hâlâ bekliyor; yeni plan ona eklenmedi.")
            return
        try:
            istekler = [m04_senaryo.istek_olustur(ayar, v) for v in plan]
            durum["bekleyen_toplu"] = {"id": llm.toplu_gonder(ayar, istekler), "plan": plan,
                                       "gonderim": ayar.simdi.isoformat(timespec="seconds")}
            anlik = []
        except Exception as e:  # kredi bitti, anahtar geçersiz vb. -> anlık (gerekirse yerel) üretim
            uyari_ekle("yapay zekâ", f"Toplu işlem gönderilemedi ({e}); senaryolar anlık üretiliyor.")
    _anlik_uret(ayar, durum, anlik)
    json_yaz(DURUM, durum)
    from . import yerel_llm
    yerel_llm.bosalt()  # montajdan önce belleği boşalt


def _anlik_uret(ayar: Ayarlar, durum: dict, plan: list[dict]) -> None:
    """Senaryoları tek tek üretir; biri başarısız olursa diğerleri devam eder."""
    for v in plan:
        ist = m04_senaryo.istek_olustur(ayar, v)
        try:
            icerik = llm.json_uret(ayar, v["kod"], ist["sistem"], ist["istem"], ist["sema"],
                                   lambda v=v: m04_senaryo.sahte_icerik(v, int(ayar["youtube"]["video_basina_shorts"])),
                                   efor=ist["efor"], max_tokens=ist["max_tokens"])
        except llm.LLMHatasi as e:
            uyari_ekle("senaryo", f"{v['kod']} üretilemedi, atlandı: {e}")
            continue
        _kuyruga_ekle(durum, ayar, v["kod"], m04_senaryo.kaydet(ayar, v, icerik))
        json_yaz(DURUM, durum)  # her senaryodan sonra kaydet: iş yarıda kesilse de kaybolmaz


def toplu_kontrol(ayar: Ayarlar) -> None:
    durum = _durum()
    bekleyen = durum.get("bekleyen_toplu")
    if not bekleyen or ayar.deneme:
        return
    try:
        sonuc = llm.toplu_sonuc(ayar, bekleyen["id"])
    except Exception as e:
        sonuc = None
        uyari_ekle("yapay zekâ", f"Toplu iş sonucu alınamadı: {e}")
    if sonuc is None:
        gonderim = datetime.fromisoformat(bekleyen.get("gonderim") or ayar.simdi.isoformat())
        if ayar.simdi - gonderim > timedelta(hours=26):  # takılı kaldı -> vazgeç, anlık üret
            uyari_ekle("yapay zekâ", "Toplu iş 26 saatte bitmedi; senaryolar anlık üretiliyor.")
            durum["bekleyen_toplu"] = None
            _anlik_uret(ayar, durum, bekleyen["plan"])
            json_yaz(DURUM, durum)
        return
    for v in bekleyen["plan"]:
        c = sonuc.get(v["kod"])
        if isinstance(c, dict):
            _kuyruga_ekle(durum, ayar, v["kod"], m04_senaryo.kaydet(ayar, v, c))
        else:  # nadir: tekil istekle (gerekirse yerel modelle) bir kez daha dene
            log.warning("Toplu sonuç başarısız (%s): %s — tekil deneniyor", v["kod"], c)
            _anlik_uret(ayar, durum, [v])
    durum["bekleyen_toplu"] = None
    json_yaz(DURUM, durum)


# -------------------------------------------------------------- üretim

def _kaydet_yayin(ayar: Ayarlar, kod: str, icerik: dict, tur: str, sira: int, vid: str, baslik: str,
                  yayin, sure_sn: float) -> None:
    csv_ekle(VERI / "yayinlananlar.csv", [{
        "tarih": ayar.simdi.isoformat(timespec="seconds"), "kod": kod, "nis": icerik["plan"]["nis"], "tur": tur,
        "sira": sira, "youtube_id": vid, "baslik": baslik, "yayin_zamani": yayin.isoformat() if yayin else "",
        "sure_sn": round(sure_sn), "kelime": icerik.get("kelime", 0),
    }], YAYIN_ALANLARI)


def _uzun_uret(ayar: Ayarlar, kod: str, icerik: dict) -> str | None:
    klasor = CIKTI / kod
    sesler = [m05_seslendirme.seslendir(ayar, s["metin"], klasor / "ses" / f"{i:03d}.mp3", i, len(icerik["sahneler"]))
              for i, s in enumerate(icerik["sahneler"])]
    materyal = m06_materyal.topla(ayar, kod, icerik)
    sahne_gorselleri = [m for m in materyal if "sahne" in m]
    sonuc = m07_montaj.uzun_video(ayar, kod, icerik, sesler, sahne_gorselleri)

    # Altyazı: sahne başlangıç zamanlarına göre kaydırılmış kelimeler
    kelimeler, t = [], float(ayar["video"]["intro_saniye"])
    for ses in sesler:
        kelimeler += [(b + t, s + t, k) for b, s, k in ses["kelimeler"]]
        t += ses["sure"] + m07_montaj.NEFES
    srt = klasor / "altyazi.srt"
    srt.write_text(m05_seslendirme.srt(m05_seslendirme.gruplar(kelimeler)), encoding="utf-8")

    # Küçük resim için ilk gerçek fotoğraf; hiç yoksa yazısız degrade (yazılar üst üste binmesin)
    foto = next((m for m in sahne_gorselleri if m["kaynak"] != "Otomatik kart"), None)
    kapak = Path(foto["dosya"]) if foto else gorsel.yazi_karti(
        "", klasor / "kapak_arka.jpg", 1280, 720, gorsel.renk(icerik["plan"]["nis"]))
    meta = m08_thumbnail_metadata.olustur(ayar, kod, icerik, sonuc["bolumler"], materyal, kapak)
    meta["aciklama"] = buyume.aciklamaya_ekle(meta["aciklama"],
                                              buyume.ic_baglanti(ayar, icerik["plan"]["nis"], kod, "uzun"))
    yayin = m09_youtube_yukleme.sonraki_yayin(ayar, "uzun", (icerik["plan"].get("deney") or {}).get("yayin_saati"))
    vid = m09_youtube_yukleme.yukle(ayar, sonuc["video"], meta["baslik"], meta["aciklama"], meta["etiketler"],
                                    yayin, Path(meta["thumbnail"]),
                                    srt if ayar["youtube"]["altyazi_yukle"] else None,
                                    sentetik=any(m.get("sentetik") for m in materyal))
    if vid:
        _kaydet_yayin(ayar, kod, icerik, "uzun", 0, vid, meta["baslik"], yayin, sonuc["sure"])
    return vid


def _shorts_uret(ayar: Ayarlar, kod: str, icerik: dict, j: int) -> str | None:
    sh = icerik["shorts"][j]
    klasor = CIKTI / kod
    (klasor / "gorseller").mkdir(parents=True, exist_ok=True)
    ses = m05_seslendirme.seslendir(ayar, sh["metin"], klasor / "ses" / f"shorts_{j}.mp3", 0, 1)
    bilgi = m06_materyal.gorsel_bul(ayar, sh["gorsel_arama"], klasor / "gorseller" / f"shorts_{j}.jpg", set(),
                                    icerik["plan"]["nis"], dikey=True, yedek_yazi="")  # başlık zaten üstte yazılı
    video = m07_montaj.shorts_video(ayar, kod, j, sh["baslik"], ses, Path(bilgi["dosya"]))
    baslik = f"{sh['baslik'][:90]} #Shorts"
    aciklama = m08_thumbnail_metadata.aciklama(ayar, icerik, [], [bilgi], shorts=True)
    aciklama = buyume.aciklamaya_ekle(aciklama, buyume.ic_baglanti(ayar, icerik["plan"]["nis"], kod, "shorts"))
    yayin = m09_youtube_yukleme.sonraki_yayin(ayar, "shorts")
    vid = m09_youtube_yukleme.yukle(ayar, video, baslik, aciklama, icerik["etiketler"], yayin,
                                    sentetik=bool(bilgi.get("sentetik")))
    if vid:
        _kaydet_yayin(ayar, kod, icerik, "shorts", j, vid, baslik, yayin, m05_seslendirme.sure(video))
    return vid


def uretim_asamasi(ayar: Ayarlar) -> int:
    durum = _durum()
    tamam = 0
    for is_ in sorted(durum["kuyruk"], key=lambda x: (x["tur"] != "uzun", x["kod"], x["sira"])):
        if is_["durum"] != "bekliyor":
            continue
        icerik = m04_senaryo.yukle(is_["kod"])
        if not icerik:
            is_["durum"] = "icerik_yok"
            continue
        try:
            if is_["tur"] == "uzun":
                vid = _uzun_uret(ayar, is_["kod"], icerik)
            else:
                vid = _shorts_uret(ayar, is_["kod"], icerik, is_["sira"])
        except Exception:
            log.error("Üretim hatası (%s): %s", is_["kod"], traceback.format_exc())
            is_["hata"] = is_.get("hata", 0) + 1
            if is_["hata"] >= 3:
                is_["durum"] = "hata"
            continue
        if vid:
            is_["durum"], is_["youtube_id"] = "yuklendi", vid
            tamam += 1
        elif not ayar.yukleme or not m09_youtube_yukleme.kimlik_var():
            is_["durum"] = "elle_yukle"   # dosyalar Actions 'artifacts' bölümünde
            (CIKTI / "ELLE_YUKLE").touch()
            tamam += 1
        else:
            log.info("Kota doldu; kalan işler sonraki çalıştırmaya kaldı.")
            break
        json_yaz(DURUM, durum)
    # Bitmiş işleri 30 kayıttan fazla tutma (depo küçük kalsın)
    bitmis = [i for i in durum["kuyruk"] if i["durum"] != "bekliyor"]
    durum["kuyruk"] = [i for i in durum["kuyruk"] if i["durum"] == "bekliyor"] + bitmis[-30:]
    json_yaz(DURUM, durum)
    return tamam


# -------------------------------------------------------------- döngüler

def _adimlar(adimlar: list[tuple[str, Callable[[], object]]]) -> list[str]:
    hatalar = []
    for ad, f in adimlar:
        log.info("▶ %s", ad)
        try:
            f()
        except Exception as e:
            log.error("✖ %s: %s\n%s", ad, e, traceback.format_exc())
            hatalar.append(f"{ad}: {e}")
    if hatalar:
        ozet_yaz("## ⚠️ Hatalar\n" + "\n".join(f"- {h}" for h in hatalar))
    return hatalar


def muhendis_calistir(ayar: Ayarlar) -> list[str]:
    """Mühendisi çalıştırır ve öğrendiği ayarları bu haftanın planına hemen uygular."""
    from . import muhendis
    from .ayarlar import yukle

    degisiklik = muhendis.calistir(ayar)
    korunan = {k: ayar.genel["youtube"][k] for k in ("haftalik_uzun_video", "video_basina_shorts")}
    yeni = yukle(ayar.deneme)
    ayar.genel, ayar.varliklar = yeni.genel, yeni.varliklar
    if ayar.mod != "normal":  # bütçe kısıtı bu çalıştırmada geçerli kalsın
        ayar.genel["youtube"].update(korunan)
    return degisiklik


# ---- KANAL ADIMLARI: her kanal kendi sürecinde (GitHub'da ayrı paralel işte) çalışır ----

def kanal_haftalik(ayar: Ayarlar) -> list[str]:
    plan: list[dict] = []
    if ayar.mod == "hafif":  # ücretsiz dakika bitmek üzere: üretim yok, ölçüm sürer
        return _adimlar([("Modül 11 — Laboratuvar analizi", lambda: m11_analiz.calistir(ayar, tam_rapor=True))])
    adimlar = [
        ("Modül 11 — Laboratuvar analizi", lambda: m11_analiz.calistir(ayar, tam_rapor=True)),
        ("Öğrenme Mühendisi — sistemi geliştir", lambda: muhendis_calistir(ayar)),
        ("Modül 2 — Niş ve kaynak analizi", lambda: m02_nis_analizi.calistir(ayar)),
        ("Modül 3 — İçerik planı", lambda: plan.extend(m03_icerik_plani.calistir(ayar))),
        ("Modül 4 — Senaryo", lambda: senaryo_asamasi(ayar, plan)),
    ]
    if not llm.toplu_mu(ayar):  # sonuç hemen hazırsa üretim aynı çalıştırmada yapılır
        adimlar.append(("Modül 5-9 — Video, Shorts ve yükleme", lambda: uretim_asamasi(ayar)))
    return _adimlar(adimlar)


def kanal_gunluk(ayar: Ayarlar) -> list[str]:
    uretim = [] if ayar.mod == "hafif" else [
        ("Toplu senaryo sonuçları", lambda: toplu_kontrol(ayar)),
        ("Modül 5-9 — Video, Shorts ve yükleme", lambda: uretim_asamasi(ayar)),
    ]
    analiz: dict = {}
    return _adimlar(uretim + [
        ("Modül 11 — Günlük metrik / viral kontrol",
         lambda: analiz.update(m11_analiz.calistir(ayar, tam_rapor=False) or {})),
        ("Büyüme — liste, yorum, yerelleştirme, paylaşım, SEO, erken aksiyon",
         lambda: buyume.calistir(ayar, analiz.get("videolar"))),
    ])


def kanal_beta(ayar: Ayarlar) -> list[str]:
    """Tek bir örnek: 1 uzun video + Shorts, YouTube'a YÜKLEMEDEN ('beta/' klasöründe)."""
    ayar.genel["youtube"]["haftalik_uzun_video"] = 1
    ayar.genel["llm"]["toplu_islem"] = False   # sonucu hemen görmek için anlık istek
    ayar.yukleme = False
    plan: list[dict] = []
    return _adimlar([
        ("Modül 2 — Niş ve kaynak analizi", lambda: m02_nis_analizi.calistir(ayar)),
        ("Modül 3 — Plan (1 video)", lambda: plan.extend(m03_icerik_plani.calistir(ayar))),
        ("Modül 4 — Senaryo", lambda: senaryo_asamasi(ayar, plan)),
        ("Modül 5-8 — Video ve Shorts", lambda: uretim_asamasi(ayar)),
    ])


KANAL_ISLERI = {
    "haftalik": kanal_haftalik,
    "gunluk": kanal_gunluk,
    "beta": kanal_beta,
    "nis": lambda a: _adimlar([("Modül 2 — Niş ve kaynak analizi", lambda: m02_nis_analizi.calistir(a))]),
    "plan": lambda a: _adimlar([("Modül 3-4 — Plan ve senaryo",
                                 lambda: senaryo_asamasi(a, m03_icerik_plani.calistir(a)))]),
    "uret": lambda a: _adimlar([("Toplu senaryo sonuçları", lambda: toplu_kontrol(a)),
                                ("Modül 5-9 — Video, Shorts ve yükleme", lambda: uretim_asamasi(a))]),
    "buyume": lambda a: _adimlar([("Büyüme araçları", lambda: buyume.calistir(a))]),
    "analiz": lambda a: _adimlar([("Modül 11 — Laboratuvar analizi", lambda: m11_analiz.calistir(a))]),
    "muhendis": lambda a: _adimlar([("Modül 11 — Laboratuvar analizi", lambda: m11_analiz.calistir(a)),
                                    ("Öğrenme Mühendisi", lambda: muhendis_calistir(a))]),
}


# ---- GENEL ADIMLAR: tüm kanallar bittikten sonra bir kez (siteler tüm kanalların yazılarını toplar) ----

def genel_haftalik(ayar: Ayarlar) -> list[str]:
    if ayar.mod == "hafif":
        return _adimlar([("Mikro siteler", lambda: mikro_site.olustur(ayar)),
                         ("Modül 12 — Gelir raporu", lambda: ozet_yaz(m12_gelir.aylik_rapor(ayar)))])
    return _adimlar([
        ("Modül 1 — Envanter", lambda: m01_envanter.calistir(ayar)),
        ("Modül 10 — Alan adı metinleri", lambda: m10_alan_adi.calistir(ayar)),
        ("Mikro siteler", lambda: mikro_site.olustur(ayar)),
        ("Modül 12 — Gelir raporu", lambda: ozet_yaz(m12_gelir.aylik_rapor(ayar))),
    ])


def genel_gunluk(ayar: Ayarlar) -> list[str]:
    return _adimlar([
        ("Modül 12 — Teklifler", lambda: m12_gelir.teklifleri_isle(ayar)),
        ("Modül 12 — Link tıklamaları", lambda: m12_gelir.tiklamalari_topla(ayar)),
        ("Mikro siteler", lambda: mikro_site.olustur(ayar)),
    ])


GENEL_ISLER = {
    "haftalik": genel_haftalik,
    "gunluk": genel_gunluk,
    "beta": lambda a: _adimlar([("Mikro siteler", lambda: mikro_site.olustur(a))]),
}
