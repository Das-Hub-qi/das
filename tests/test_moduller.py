import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from otonom import (m02_nis_analizi, m03_icerik_plani, m04_senaryo, m05_seslendirme, m08_thumbnail_metadata,
                    m09_youtube_yukleme, m11_analiz)
from otonom.ayarlar import kisa_ad
from otonom.m01_envanter import alan_adi_puani

IST = ZoneInfo("Europe/Istanbul")


def test_kisa_ad_turkce_karakter():
    assert kisa_ad("Beyin Sağlığı İçin 5 Öneri!") == "beyin-sagligi-icin-5-oneri"
    assert kisa_ad("trustneurohub.com.tr") == "trustneurohub-com-tr"
    assert kisa_ad("???") == "icerik"


def test_alan_adi_puani_mantikli_siralama():
    kisa = alan_adi_puani("turizm.com")["puan"]
    uzun = alan_adi_puani("cok-uzun-bir-alan-adi-2024.net")["puan"]
    assert kisa > uzun
    assert 0 <= uzun <= 100
    assert alan_adi_puani("okyanusbilisimtr.com")["seviye"] in {"Yüksek", "Orta", "Düşük"}


def test_firsat_puani_rekabet_yoksa_talebe_esit():
    assert m02_nis_analizi.firsat_puani(0.8, {}) == (0.8, "bilinmiyor")
    kolay, etiket = m02_nis_analizi.firsat_puani(0.8, {"medyan_abone": 2_000, "kucuk_kanal_orani": 0.6})
    zor, _ = m02_nis_analizi.firsat_puani(0.8, {"medyan_abone": 3_000_000, "kucuk_kanal_orani": 0.0})
    assert kolay > zor and etiket == "düşük"


def test_dagit_kazanan_nise_daha_cok_uretim():
    rng = random.Random(1)
    secim = m03_icerik_plani.dagit(["a", "b"], {"a": 1.6, "b": 0.3}, 1000, 0.0, rng)
    assert secim.count("a") > 3 * secim.count("b")
    assert m03_icerik_plani.dagit([], {}, 3, 0.2, rng) == []


def test_yayin_zamanlari_dogru_gun_ve_saat():
    pazartesi = datetime(2026, 11, 2, 9, 0, tzinfo=IST)
    z = m09_youtube_yukleme.yayin_zamanlari(pazartesi, ["sali", "persembe", "cumartesi"], "18:00", 3)
    assert [x.weekday() for x in z] == [1, 3, 5]
    assert all(x.hour == 18 for x in z)
    # Aynı gün, 2 saatten kısa süre kaldıysa o gün atlanır
    sali = datetime(2026, 11, 3, 17, 0, tzinfo=IST)
    assert m09_youtube_yukleme.yayin_zamanlari(sali, ["sali"], "18:00", 1)[0].day == 10


def test_altyazi_duraklamada_bolunur():
    kelimeler = [(0.0, 0.4, "Merhaba"), (1.2, 1.4, "bu"), (1.45, 1.6, "bir"), (1.65, 2.0, "deneme")]
    satirlar = m05_seslendirme.gruplar(kelimeler)
    assert [s[2] for s in satirlar] == ["Merhaba", "bu bir deneme"]
    srt = m05_seslendirme.srt(satirlar)
    assert "00:00:01,200 --> 00:00:02,000" in srt


def test_bolumler_youtube_kurallarina_uyar():
    assert m08_thumbnail_metadata.bolum_satirlari([(0, "Giriş"), (5, "Kısa"), (20, "Asıl"), (60, "Son")]) == [
        "00:00 Giriş", "00:20 Asıl", "01:00 Son"]
    assert m08_thumbnail_metadata.bolum_satirlari([(0, "Giriş"), (30, "Son")]) == []  # 3'ten az bölüm


def test_etiket_ve_baslik_sinirlari():
    icerik = m04_senaryo.sahte_icerik({"konu": "x", "anahtar_kelime": "y"})
    icerik["baslik"] = "a" * 150
    icerik["etiketler"] = ["#etiket" + str(i) * 60 for i in range(20)]
    temiz = m04_senaryo._temizle(icerik)
    assert len(temiz["baslik"]) == 100
    assert sum(len(e) + 1 for e in temiz["etiketler"]) <= 450
    assert all("#" not in e for e in temiz["etiketler"])


def test_yuzdelik_ve_puanlama():
    assert m11_analiz.yuzdelik([10, 20, 30]) == [0.0, 50.0, 100.0]
    videolar = [
        {"tur": "uzun", "nis": "a", "goruntulenme": 1000, "begeni": 50, "yorum": 10, "yas_gun": 10, "ort_izlenme_yuzde": 60},
        {"tur": "uzun", "nis": "b", "goruntulenme": 100, "begeni": 1, "yorum": 0, "yas_gun": 10, "ort_izlenme_yuzde": 20},
        {"tur": "shorts", "nis": "b", "goruntulenme": 5, "begeni": 0, "yorum": 0, "yas_gun": 10, "ort_izlenme_yuzde": 0},
    ]
    m11_analiz.puanla(videolar)
    assert videolar[0]["skor"] > videolar[1]["skor"]
    assert videolar[2]["skor"] == 50.0  # tek shorts kendi grubunda ortada
    agirlik = m11_analiz.nis_agirliklari(videolar, ["a", "b", "c"])
    assert agirlik["c"] == 1.0  # verisi olmayan niş nötr kalır


def test_haftalik_dongu_deneme_modunda_uctan_uca(tmp_path: Path):
    from otonom.__main__ import main
    from otonom.ayarlar import CIKTI, SITE, VERI, csv_oku

    assert main(["haftalik", "--deneme"]) == 0
    yayin = csv_oku(VERI / "yayinlananlar.csv")
    assert {s["tur"] for s in yayin} == {"uzun", "shorts"}
    kod = yayin[0]["kod"]
    for dosya in ("final_video.mp4", "thumbnail.jpg", "metadata.json", "altyazi.srt", "shorts_0.mp4"):
        assert (CIKTI / kod / dosya).exists(), dosya
    assert (SITE / "trustneurohub-com-tr" / "public" / "index.html").exists()
    assert (VERI / "alan_adlari" / "okyanusbilisimtr.com" / "pitch.txt").exists()
    assert main(["gunluk", "--deneme"]) == 0

    # Siteler yüklendikten sonra (özetler kaydedilince) değişmeyen site tekrar yüklenmez
    import shutil

    from otonom import mikro_site
    from otonom.ayarlar import yukle
    shutil.copy(SITE / "ozetler.json", VERI / "site_ozetleri.json")
    assert mikro_site.olustur(yukle(deneme=True)) == []


def test_config_dosyalari_okunur():
    from otonom.ayarlar import yukle

    ayar = yukle(deneme=True)
    assert ayar.nisler and ayar["llm"]["model"].startswith("claude-")


def test_yapay_zeka_saglayici_secimi(monkeypatch):
    from otonom import llm
    from otonom.ayarlar import yukle

    ayar = yukle()
    ayar.genel["llm"]["saglayici"] = "otomatik"
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert llm.saglayici(ayar) == "yerel"           # anahtar yok -> ücretsiz yerel model
    assert llm.toplu_mu(ayar) is False             # yerel modelde toplu işlem yok
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert llm.saglayici(ayar) == "claude"
    assert llm.toplu_mu(ayar) is True
    ayar.genel["llm"]["saglayici"] = "yerel"
    assert llm.saglayici(ayar) == "yerel"


def test_cloudflare_kv_kimligi(monkeypatch):
    from otonom import cloudflare_kur

    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CF_KV_NAMESPACE_ID", raising=False)
    assert cloudflare_kur.kv_kimligi() == ""        # yapılandırılmamış -> sessizce boş
    monkeypatch.setenv("CF_KV_NAMESPACE_ID", "abc123")
    assert cloudflare_kur.kv_kimligi() == "abc123"


def test_ab_testi_deneme_modunda_dokunmaz():
    from datetime import date

    from otonom.ayarlar import yukle

    assert m11_analiz.ab_testi(yukle(deneme=True), [], date.today()) == []
