"""MODÜL 7 — Montaj (doğrudan ffmpeg: MoviePy'den çok daha hızlı ve az bellekli).

Her sahne kendi sesiyle ayrı kodlanır -> görsel ve anlatım birebir eşleşir;
sonra yeniden kodlama yapmadan (-c copy) birleştirilir. Bu, ücretsiz GitHub Actions
dakikalarını korur.
"""
from __future__ import annotations

import hashlib
import math
import subprocess
from pathlib import Path

from . import gorsel
from .ayarlar import CIKTI, CONFIG, Ayarlar, log
from .m05_seslendirme import gruplar, sure


def _ffmpeg(*args: str) -> None:
    sonuc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
                           capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise RuntimeError(f"ffmpeg hatası: {sonuc.stderr[-1500:]}")


def boyut(ayar: Ayarlar, dikey: bool = False) -> tuple[int, int, int]:
    v = ayar["video"]
    g, y, fps = int(v["genislik"]), int(v["yukseklik"]), int(v["fps"])
    if ayar.deneme:  # testte hızlı olsun
        g, y, fps = 640, 360, 12
    return (y, g, fps) if dikey else (g, y, fps)


def _kodlama(ayar: Ayarlar) -> list[str]:
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(ayar["video"]["crf"]), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"]


def sahne_klibi(ayar: Ayarlar, resim: Path, ses: Path | None, saniye: float, cikti: Path, sira: int) -> Path:
    g, y, fps = boyut(ayar)
    kare = max(1, math.ceil(saniye * fps))
    solma = min(0.4, saniye / 4)
    son = f"fade=t=in:st=0:d={solma:.2f},fade=t=out:st={saniye - solma:.2f}:d={solma:.2f},format=yuv420p"
    if ayar["video"]["ken_burns"]:
        hiz = 0.12 / kare  # sahne boyunca %12 yakınlaşma
        if sira % 2 == 0:
            z, x = f"min(zoom+{hiz:.6f},1.12)", "iw/2-(iw/zoom/2)"
        else:  # tek sahnelerde yatay kaydırma: çeşitlilik
            z, x = "1.12", f"(iw-iw/zoom)*on/{kare}"
        vf = (f"scale={2 * g}:{2 * y}:force_original_aspect_ratio=increase,crop={2 * g}:{2 * y},"
              f"zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d={kare}:s={g}x{y}:fps={fps},{son}")
        girdi = ["-i", str(resim)]
    else:
        vf = f"scale={g}:{y}:force_original_aspect_ratio=increase,crop={g}:{y},fps={fps},{son}"
        girdi = ["-loop", "1", "-framerate", str(fps), "-i", str(resim)]
    ses_girdi = ["-i", str(ses)] if ses else ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    _ffmpeg(*girdi, *ses_girdi, "-vf", vf, "-af", "apad", "-t", f"{saniye:.3f}", "-r", str(fps),
            *_kodlama(ayar), str(cikti))
    return cikti


def _birlestir(klipler: list[Path], cikti: Path) -> None:
    liste = cikti.with_suffix(".txt")
    liste.write_text("".join(f"file '{k.resolve()}'\n" for k in klipler), encoding="utf-8")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", "-movflags", "+faststart", str(cikti))


def _muzik_ekle(ayar: Ayarlar, video: Path, cikti: Path, anahtar: str) -> bool:
    muzikler = sorted((CONFIG / "muzik").glob("*.mp3"))
    if not muzikler:
        return False
    muzik = muzikler[int(hashlib.md5(anahtar.encode()).hexdigest(), 16) % len(muzikler)]
    toplam = sure(video)
    db = ayar["ses"]["muzik_seviyesi_db"]
    _ffmpeg("-i", str(video), "-stream_loop", "-1", "-i", str(muzik), "-filter_complex",
            f"[1:a]volume={db}dB,afade=t=out:st={max(0, toplam - 3):.2f}:d=3[m];"
            f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(cikti))
    return True


def uzun_video(ayar: Ayarlar, kod: str, icerik: dict, sesler: list[dict], gorseller: list[dict]) -> dict:
    klasor = CIKTI / kod / "klipler"
    klasor.mkdir(parents=True, exist_ok=True)
    g, y, _ = boyut(ayar)
    klipler, bolumler, t = [], [], 0.0
    v = ayar["video"]
    ilk = Path(gorseller[0]["dosya"])

    if float(v["intro_saniye"]) > 0:
        kapak = klasor / "intro.png"
        gorsel.shorts_karesi(ilk, icerik["baslik"], "", kapak, g, y)
        klipler.append(sahne_klibi(ayar, kapak, None, float(v["intro_saniye"]), klasor / "000_intro.mp4", 0))
        t += float(v["intro_saniye"])

    for i, (s, ses, gor) in enumerate(zip(icerik["sahneler"], sesler, gorseller)):
        if s.get("bolum"):
            bolumler.append((0.0 if not bolumler else t, s["bolum"]))
        saniye = ses["sure"] + 0.35  # cümleler arası doğal nefes payı
        klipler.append(sahne_klibi(ayar, Path(gor["dosya"]), ses["ses"], saniye, klasor / f"{i + 1:03d}.mp4", i))
        t += saniye

    if float(v["outro_saniye"]) > 0:
        site = ayar.nis(icerik["plan"]["nis"]).get("alan_adi") or ""
        kart = klasor / "outro.png"
        gorsel.shorts_karesi(Path(gorseller[-1]["dosya"]), f"Abone ol • {site}".strip(" •"),
                             "İzlediğin için teşekkürler", kart, g, y)
        klipler.append(sahne_klibi(ayar, kart, None, float(v["outro_saniye"]), klasor / "999_outro.mp4", 0))
        t += float(v["outro_saniye"])

    ham = CIKTI / kod / "ham.mp4"
    _birlestir(klipler, ham)
    final = CIKTI / kod / "final_video.mp4"
    if not _muzik_ekle(ayar, ham, final, kod):
        ham.replace(final)
    log.info("Uzun video hazır: %s (%.0f sn)", final, t)
    return {"video": final, "sure": t, "bolumler": bolumler}


def shorts_video(ayar: Ayarlar, kod: str, sira: int, baslik: str, ses: dict, arka: Path) -> Path:
    """Dikey, büyük altyazılı Shorts. Kareler Pillow ile çizilir (libass gerekmez, çok hızlı)."""
    g, y, _ = boyut(ayar, dikey=True)
    klasor = CIKTI / kod / f"shorts_{sira}"
    klasor.mkdir(parents=True, exist_ok=True)
    toplam = ses["sure"] + 0.3
    hiz = max(1.0, min(1.25, toplam / 58.0))  # Shorts 60 sn altında kalsın
    satirlar = gruplar(ses["kelimeler"], en_fazla=3)

    bos = gorsel.shorts_karesi(arka, "", baslik, klasor / "bos.png", g, y)
    parcalar: list[tuple[Path, float]] = []
    an = 0.0
    for i, (bas, _son, metin) in enumerate(satirlar):
        if bas > an + 0.05:
            parcalar.append((bos, bas - an))
            an = bas
        bitis = satirlar[i + 1][0] if i + 1 < len(satirlar) else toplam
        kare = gorsel.shorts_karesi(arka, metin, baslik, klasor / f"{i:03d}.png", g, y)
        parcalar.append((kare, max(0.05, bitis - an)))
        an = bitis
    if not parcalar:
        parcalar.append((bos, toplam))

    liste = klasor / "kareler.txt"
    satir = [f"file '{p.resolve()}'\nduration {d / hiz:.3f}\n" for p, d in parcalar]
    satir.append(f"file '{parcalar[-1][0].resolve()}'\n")
    liste.write_text("".join(satir), encoding="utf-8")
    cikti = CIKTI / kod / f"shorts_{sira}.mp4"
    af = f"atempo={hiz:.3f},apad" if hiz > 1.0 else "apad"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(liste), "-i", str(ses["ses"]),
            "-vf", f"fps=30,scale={g}:{y},format=yuv420p", "-af", af, "-t", f"{toplam / hiz:.3f}",
            *_kodlama(ayar), "-movflags", "+faststart", str(cikti))
    log.info("Shorts hazır: %s", cikti)
    return cikti

