"""Komut satırı: python -m otonom <komut> [--deneme]

Komutlar:
  haftalik   Haftalık döngü (analiz, niş, plan, senaryo, alan adı, site, rapor)
  gunluk     Günlük döngü (üretim+yükleme, viral kontrol, teklifler, site)
  envanter   Modül 1        nis       Modül 2        plan      Modül 3
  uret       Kuyruktaki videoları üret/yükle         alanadi   Modül 10
  site       Mikro siteleri oluştur                   analiz    Modül 11
  teklifler  Cloudflare'dan teklifleri al             rapor     Aylık gelir raporu
  maliyet    Bugüne kadarki yapay zekâ harcaması
  cloudflare Alan adlarını Pages sitelerine bağlar, KV deposunu kurar
  beta       Tek örnek video + Shorts + site üretir, YouTube'a yüklemez ('beta/' klasörü)
--deneme: Dış servis çağırmadan, geçici klasörde sahte veriyle uçtan uca test.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="otonom", description="Otonom gelir ve içerik sistemi")
    p.add_argument("komut", choices=["haftalik", "gunluk", "envanter", "nis", "plan", "uret", "alanadi", "site",
                                     "analiz", "teklifler", "rapor", "maliyet", "beta", "cloudflare"])
    p.add_argument("--deneme", action="store_true", help="dış servis yok, geçici klasör, sahte veri")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    if a.komut == "beta" and not a.deneme and not os.environ.get("OTONOM_CALISMA"):
        from pathlib import Path
        os.environ["OTONOM_CALISMA"] = str(Path(__file__).resolve().parent.parent / "beta")
    if a.deneme and not os.environ.get("OTONOM_CALISMA"):
        os.environ["OTONOM_CALISMA"] = tempfile.mkdtemp(prefix="otonom-deneme-")
        print(f"Deneme klasörü: {os.environ['OTONOM_CALISMA']}")

    # Klasör yolları ortam değişkenine göre belirlendiği için içe aktarma burada yapılır.
    from . import (llm, m01_envanter, m02_nis_analizi, m03_icerik_plani, m10_alan_adi, m11_analiz, m12_gelir,
                   mikro_site, orkestrator)
    from .ayarlar import ozet_yaz, yukle

    ayar = yukle(deneme=a.deneme)
    k = a.komut
    hatalar: list[str] = []
    if k == "haftalik":
        hatalar = orkestrator.haftalik(ayar)
    elif k == "gunluk":
        hatalar = orkestrator.gunluk(ayar)
    elif k == "envanter":
        m01_envanter.calistir(ayar)
    elif k == "nis":
        m02_nis_analizi.calistir(ayar)
    elif k == "plan":
        orkestrator.senaryo_asamasi(ayar, m03_icerik_plani.calistir(ayar))
    elif k == "uret":
        orkestrator.toplu_kontrol(ayar)
        orkestrator.uretim_asamasi(ayar)
    elif k == "alanadi":
        m10_alan_adi.calistir(ayar, zorla=True)
    elif k == "site":
        mikro_site.olustur(ayar)
    elif k == "analiz":
        m11_analiz.calistir(ayar)
    elif k == "teklifler":
        m12_gelir.teklifleri_isle(ayar)
        m12_gelir.tiklamalari_topla(ayar)
    elif k == "rapor":
        ozet_yaz(m12_gelir.aylik_rapor(ayar))
    elif k == "cloudflare":
        from . import cloudflare_kur
        cloudflare_kur.kv_kimligi()
        cloudflare_kur.alan_adlarini_bagla(ayar)
    elif k == "beta":
        hatalar = orkestrator.beta(ayar)
    elif k == "maliyet":
        print(f"Toplam yapay zekâ maliyeti: {llm.toplam_maliyet():.4f} $")
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
