"""MODÜL 9 — YouTube'a otomatik yükleme (YouTube Data API v3, ücretsiz günlük kota).

ÖNEMLİ: Google'ın denetiminden (audit) geçmemiş API projeleriyle yüklenen videolar
"gizli" olarak kilitlenir. Ücretsiz denetim formu doldurulana kadar videoları
YouTube Studio'dan kontrol edip tek tıkla yayınlarsınız (bu aynı zamanda haftalık
insan denetimi kuralını da karşılar). Ayrıntılar README'de.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .ayarlar import VERI, Ayarlar, csv_oku, gizli, json_oku, json_yaz, log, uyari_ekle

GUNLER = {"pazartesi": 0, "sali": 1, "carsamba": 2, "persembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6}
KOTA = {"yukleme": 1600, "kucuk_resim": 50, "altyazi": 400}
GUNLUK_KOTA = 10_000
KOTA_DOSYASI = VERI / "kota.json"


def yayin_zamanlari(baslangic: datetime, gunler: list[str], saat: str, adet: int) -> list[datetime]:
    """baslangic'tan sonraki ilk `adet` uygun gün/saat (İstanbul saati)."""
    s, d = (int(x) for x in saat.split(":"))
    hedef_gunler = {GUNLER[g] for g in gunler}
    an = baslangic.astimezone(ZoneInfo("Europe/Istanbul"))
    sonuc = []
    gun = an.replace(hour=s, minute=d, second=0, microsecond=0)
    while len(sonuc) < adet:
        if gun > an + timedelta(hours=2) and gun.weekday() in hedef_gunler:
            sonuc.append(gun)
        gun += timedelta(days=1)
    return sonuc


def sonraki_yayin(ayar: Ayarlar, tur: str, saat: str | None = None) -> datetime | None:
    if ayar["youtube"]["gizlilik"] != "zamanla":
        return None
    onceki = [datetime.fromisoformat(s["yayin_zamani"]) for s in csv_oku(VERI / "yayinlananlar.csv")
              if s["tur"] == tur and s.get("yayin_zamani")]
    baslangic = max([ayar.simdi, *onceki])
    if tur == "uzun":
        gun = yayin_zamanlari(baslangic, ayar["youtube"]["yayin_gunleri"], ayar["youtube"]["yayin_saati"], 1)[0]
        if saat:  # laboratuvarın denediği yayın saati (aynı gün, farklı saat)
            s, d = (int(x) for x in saat.split(":"))
            gun = gun.replace(hour=s, minute=d)
        return gun
    return yayin_zamanlari(baslangic, list(GUNLER), "12:00", 1)[0]


# ------------------------------------------------------------------ kota

def _kota_gunu() -> str:
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()  # kota PT gece yarısı sıfırlanır


def kota_yeterli(birim: int) -> bool:
    kullanilan = json_oku(KOTA_DOSYASI, {}).get(_kota_gunu(), 0)
    return kullanilan + birim <= GUNLUK_KOTA - 300  # analiz için pay bırak


def kota_harca(birim: int) -> None:
    veri = json_oku(KOTA_DOSYASI, {})
    gun = _kota_gunu()
    json_yaz(KOTA_DOSYASI, {gun: veri.get(gun, 0) + birim})


# --------------------------------------------------------------- yükleme

_KIMLIK_BOZUK = False  # bu çalıştırmada yetki reddedildiyse tekrar denenmez


def kimlik_var() -> bool:
    return not _KIMLIK_BOZUK and all(gizli(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def servis(api: str = "youtube", surum: str = "v3"):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    kimlik = Credentials(None, refresh_token=gizli("YT_REFRESH_TOKEN"), client_id=gizli("YT_CLIENT_ID"),
                         client_secret=gizli("YT_CLIENT_SECRET"), token_uri="https://oauth2.googleapis.com/token")
    return build(api, surum, credentials=kimlik, cache_discovery=False)


def yukle(ayar: Ayarlar, video: Path, baslik: str, aciklama: str, etiketler: list[str],
          yayin: datetime | None, kucuk_resim: Path | None = None, altyazi: Path | None = None) -> str | None:
    """Video kimliğini döner. Kota/kimlik yoksa None (sonraki çalıştırmada tekrar denenir)."""
    if ayar.deneme:
        return "DENEME-" + video.stem
    if not ayar.yukleme:
        return None
    if not kimlik_var():
        log.warning("YouTube kimlik bilgileri yok; video Actions 'artifacts' bölümünden elle yüklenebilir.")
        return None
    gerekli = KOTA["yukleme"] + (KOTA["kucuk_resim"] if kucuk_resim else 0) + (KOTA["altyazi"] if altyazi else 0)
    if not kota_yeterli(gerekli):
        log.warning("Günlük YouTube kotası doldu; %s yarın yüklenecek.", video.name)
        return None

    from googleapiclient.errors import HttpError

    try:
        return _yukle(ayar, video, baslik, aciklama, etiketler, yayin, kucuk_resim, altyazi)
    except HttpError as e:
        neden = str(e)
        if "quotaExceeded" in neden or "uploadLimitExceeded" in neden:
            kota_harca(GUNLUK_KOTA)  # bugün için dolu say; yarın kaldığı yerden devam
            uyari_ekle("youtube", "YouTube günlük kotası/yükleme sınırı doldu; kalan videolar yarın yüklenecek.")
            return None
        raise
    except Exception as e:
        if "invalid_grant" in str(e) or "RefreshError" in type(e).__name__:
            global _KIMLIK_BOZUK
            _KIMLIK_BOZUK = True
            uyari_ekle("youtube", "YouTube bağlantısı geçersiz (refresh token süresi dolmuş olabilir). "
                                  "Videolar üretilmeye devam ediyor ve indirilebilir; araclar/youtube_token_al.py "
                                  "ile yeni anahtar alın.")
            return None
        raise


def _yukle(ayar: Ayarlar, video: Path, baslik: str, aciklama: str, etiketler: list[str],
           yayin: datetime | None, kucuk_resim: Path | None, altyazi: Path | None) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = servis()
    durum = {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
             "containsSyntheticMedia": bool(ayar["youtube"]["sentetik_medya_beyani"])}
    if yayin:
        durum["publishAt"] = yayin.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    govde = {
        "snippet": {"title": baslik[:100], "description": aciklama, "tags": etiketler,
                    "categoryId": str(ayar["youtube"]["kategori_id"]),
                    "defaultLanguage": "tr", "defaultAudioLanguage": "tr"},
        "status": durum,
    }
    istek = yt.videos().insert(part="snippet,status", body=govde,
                               media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    cevap = None
    while cevap is None:
        _, cevap = istek.next_chunk()
    vid = cevap["id"]
    kota_harca(KOTA["yukleme"])
    log.info("Yüklendi: https://youtu.be/%s", vid)

    if kucuk_resim:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(kucuk_resim), mimetype="image/jpeg")).execute()
            kota_harca(KOTA["kucuk_resim"])
        except HttpError as e:
            log.warning("Küçük resim yüklenemedi (kanal telefonla doğrulanmalı): %s", e)
    if altyazi:
        try:
            yt.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": vid, "language": "tr", "name": "Türkçe", "isDraft": False}},
                media_body=MediaFileUpload(str(altyazi), mimetype="application/octet-stream"),
            ).execute()
            kota_harca(KOTA["altyazi"])
        except HttpError as e:
            log.warning("Altyazı yüklenemedi: %s", e)
    return vid
