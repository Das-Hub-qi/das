"""MODÜL 7 — Montaj v2: akıcı, hareketli, katmanlı video (yalnızca ffmpeg + Pillow + numpy; ücretsiz).

Uzun video:
* Her sahneye farklı, yumuşak (ease-in-out) kamera hareketi: yaklaş, uzaklaş, sağa/sola/yukarı kaydır,
  üçte bir noktasına odaklan, çapraz süzül. Açılış sahnesi hızlı bir "darbe" yakınlaşmasıyla başlar.
* Sahneler arası geçişler (xfade): yumuşak kayma, çözülme, daire, bulanık, çapraz...; bölüm başlarında
  karartmalı geçiş. Her geçişte stereo "whoosh" sesi.
* Ekranda yazı: söylenen cümle alttan yumuşakça belirir (sesi kapalı izleyenler için).
  Bölüm başlığı soldan kayarak gelir.
* Logo filigranı, ilerleme çubuğu, videonun ~%30'unda kayan "Abone ol" rozeti, logolu kapanış.
* Ses: işlenmiş anlatım + her videoya özel üretken fon müziği (konuşmada kısılır) + geçiş sesleri, -14 LUFS.
Shorts: hareketli arka plan + kelime kelime vurgulanan büyük altyazı + başlık + logo + ilerleme çubuğu.

Uzun video gruplar hâlinde kodlanır (bellek dostu): sahne klipleri → geçişli gruplar → kopyalayarak birleştirme.
"""
from __future__ import annotations

import hashlib
import math
import random
import subprocess
from pathlib import Path

from . import gorsel, ses_tasarimi
from .ayarlar import CIKTI, CONFIG, Ayarlar, log
from .m05_seslendirme import gruplar, sure

NEFES = 0.35          # sahneler arası doğal nefes payı (altyazı zamanlaması da buna göre)
GECIS = 0.5           # geçiş süresi (sn)
GRUP = 10             # tek seferde birleştirilen en fazla sahne (bellek)
HAREKETLER = ["yaklas", "saga", "uzaklas", "kose", "sola", "suzul", "yukari"]
YUMUSAK = ["fade", "smoothleft", "dissolve", "smoothright", "fade", "smoothup"]
CANLI = ["circleopen", "slideleft", "radial", "hblur", "zoomin", "diagtl", "wipeleft"]


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


def _kodlama(ayar: Ayarlar, ara: bool = False) -> list[str]:
    """Video kodlama ayarı. Ara dosyalar yüksek kalitede ve hızlı (sonra yeniden kodlanır)."""
    crf = "18" if ara else str(ayar["video"]["crf"])
    return ["-c:v", "libx264", "-preset", "ultrafast" if ara else "veryfast", "-crf", crf, "-pix_fmt", "yuv420p"]


def _font() -> str:
    return next((f for f in gorsel.FONT_ADAYLARI if Path(f).exists()), "")


def logo_yolu(ayar: Ayarlar) -> Path | None:
    if not ayar["video"].get("logo"):
        return None
    aday = ayar.kanal_bilgi.get("logo") or ayar["video"]["logo"]
    yol = Path(aday) if Path(aday).is_absolute() else CONFIG.parent / aday
    return yol if yol.exists() else None


# ------------------------------------------------------------ kamera hareketi

def hareket_ifadesi(tur: str, kare: int, fps: int, guc: float = 1.0) -> tuple[str, str, str]:
    """zoompan için (zoom, x, y) ifadeleri. E: 0→1 yumuşak (ease-in-out) ilerleme."""
    e = f"(1-cos(PI*on/{kare}))/2"
    a = round(0.16 * guc, 3)
    mx, my = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if tur == "darbe":  # açılış: hızlı yakınlaşmadan yavaş süzülmeye
        return f"1.06+0.22*exp(-on/{max(1, int(fps * 0.35))})+0.05*{e}", mx, my
    if tur == "yaklas":
        return f"1+{a}*{e}", mx, my
    if tur == "uzaklas":
        return f"{1 + a}-{a}*{e}", mx, my
    if tur == "saga":
        return f"{1 + a}", f"(iw-iw/zoom)*{e}", my
    if tur == "sola":
        return f"{1 + a}", f"(iw-iw/zoom)*(1-{e})", my
    if tur == "yukari":
        return f"{1 + a}", mx, f"(ih-ih/zoom)*(1-{e})"
    if tur == "kose":  # üçte bir noktasına doğru yakınlaşma
        return f"1+{round(a * 1.4, 3)}*{e}", "(iw-iw/zoom)*0.3", "(ih-ih/zoom)*0.35"
    return f"1.06+{round(a * 0.6, 3)}*{e}", f"(iw-iw/zoom)*(0.2+0.6*{e})", f"(ih-ih/zoom)*(0.6-0.2*{e})"


def _metin_dosyasi(klasor: Path, ad: str, metin: str) -> Path:
    metin = " ".join(metin.split())
    if len(metin) > 42:  # iki satıra böl
        orta = metin.rfind(" ", 0, len(metin) // 2 + 6)
        if orta > 0:
            metin = metin[:orta] + "\n" + metin[orta + 1:]
    yol = klasor / f"{ad}.txt"
    yol.write_text(metin, encoding="utf-8")
    return yol


def _altyazi_suzgecleri(ayar: Ayarlar, kelimeler: list, gecikme: float, son: float, klasor: Path, ad: str) -> list[str]:
    _, y, _ = boyut(ayar)
    font = _font()
    if not (ayar["video"].get("altyazi_yak") and font and kelimeler):
        return []
    fs, kay = max(14, int(y * 0.048)), max(6, int(y * 0.018))
    satirlar = gruplar(kelimeler, en_fazla=6)
    suz = []
    for k, (b, _s, metin) in enumerate(satirlar):
        b0 = b + gecikme
        b1 = (satirlar[k + 1][0] + gecikme) if k + 1 < len(satirlar) else son
        dosya = _metin_dosyasi(klasor, f"{ad}_{k:02d}", metin)
        suz.append(
            f"drawtext=fontfile='{font}':textfile='{dosya}':expansion=none:fontsize={fs}:fontcolor=white:"
            f"line_spacing={fs // 5}:borderw={max(2, fs // 14)}:bordercolor=black@0.9:box=1:boxcolor=black@0.38:"
            f"boxborderw={fs // 3}:x=(w-text_w)/2:y='h*0.88-text_h+{kay}*max(0,1-(t-{b0:.2f})/0.2)':"
            f"alpha='min(1,max(0,(t-{b0:.2f})/0.15))':enable='between(t,{b0:.2f},{b1:.2f})'")
    return suz


def sahne_klibi(ayar: Ayarlar, resim: Path, saniye: float, cikti: Path, hareket: str = "yaklas",
                guc: float = 1.0, kelimeler: list | None = None, bant: Path | None = None,
                gecikme: float = 0.0, karar_gir: float = 0.0, karar_cik: float | None = None) -> Path:
    """Sessiz sahne klibi: kamera hareketi + renk + (varsa) altyazı ve bölüm bandı.
    karar_gir / karar_cik: siyahtan açılma / siyaha kararma (bölüm geçişleri)."""
    g, y, fps = boyut(ayar)
    kare = max(1, math.ceil(saniye * fps))
    z, x, yy = hareket_ifadesi(hareket, kare, fps, guc)
    zincir = [f"scale={2 * g}:{2 * y}:force_original_aspect_ratio=increase", f"crop={2 * g}:{2 * y}",
              f"zoompan=z='{z}':x='{x}':y='{yy}':d={kare}:s={g}x{y}:fps={fps}",
              "eq=contrast=1.05:saturation=1.12", "vignette=PI/5"]
    if karar_gir:
        zincir.append(f"fade=t=in:st=0:d={karar_gir:.2f}")
    if karar_cik is not None:
        zincir.append(f"fade=t=out:st={max(0.0, karar_cik - 0.3):.2f}:d=0.3")
    zincir += _altyazi_suzgecleri(ayar, kelimeler or [], gecikme, saniye, cikti.parent, cikti.stem)
    girdiler = ["-i", str(resim)]
    if bant:
        g0 = gecikme + 0.25
        kenar = max(12, g // 40)
        girdiler += ["-loop", "1", "-framerate", str(fps), "-t", f"{saniye:.3f}", "-i", str(bant)]
        grafik = (f"[0:v]{','.join(zincir)}[v];"
                  f"[1:v]format=rgba,fade=t=out:st={g0 + 3.4:.2f}:d=0.4:alpha=1[b];"
                  f"[v][b]overlay=x='if(lt(t-{g0:.2f},0.45),-w+(w+{kenar})*sin(PI/2*max(0,t-{g0:.2f})/0.45),{kenar})':"
                  f"y=H*0.07:enable='between(t,{g0:.2f},{g0 + 3.8:.2f})',format=yuv420p[o]")
    else:
        grafik = f"[0:v]{','.join(zincir)},format=yuv420p[o]"
    _ffmpeg(*girdiler, "-filter_complex", grafik, "-map", "[o]", "-t", f"{saniye:.3f}", "-r", str(fps), "-an",
            *_kodlama(ayar, ara=True), str(cikti))
    return cikti


# --------------------------------------------------------------- birleştirme

def _katmanlar(ayar: Ayarlar, girdi_no: int, akan: str, ofset: float, toplam: float, sure_: float,
               klasor: Path, abone_an: float | None) -> tuple[list[str], list[str], str]:
    """Logo filigranı, ilerleme çubuğu, abone rozeti. Döner: (ek girdiler, filtreler, son etiket)."""
    g, y, fps = boyut(ayar)
    v = ayar["video"]
    girdiler, suz = [], []
    kenar = max(10, g // 60)
    logo = logo_yolu(ayar)
    if logo:
        girdiler += ["-loop", "1", "-framerate", str(fps), "-t", f"{sure_:.3f}", "-i", str(logo)]
        suz += [f"[{girdi_no}:v]scale=-1:{max(24, y // 11)},format=rgba,colorchannelmixer=aa=0.7[lg]",
                f"[{akan}][lg]overlay=W-w-{kenar}:{kenar}[k1]"]
        akan, girdi_no = "k1", girdi_no + 1
    if v.get("ilerleme_cubugu"):
        cubuk = max(3, y // 200)
        girdiler += ["-f", "lavfi", "-t", f"{sure_:.3f}", "-i", f"color=c=0xE50914:s={g}x{cubuk}:r={fps}"]
        suz.append(f"[{akan}][{girdi_no}:v]overlay=x='-w+W*(t+{ofset:.3f})/{toplam:.3f}':y=H-h:eval=frame[k2]")
        akan, girdi_no = "k2", girdi_no + 1
    if abone_an is not None and ofset <= abone_an < ofset + sure_ - 4:
        a = abone_an - ofset
        rozet = gorsel.abone_rozeti(klasor / "abone.png", g, y)
        girdiler += ["-loop", "1", "-framerate", str(fps), "-t", f"{sure_:.3f}", "-i", str(rozet)]
        suz += [f"[{girdi_no}:v]format=rgba,fade=t=out:st={a + 3.6:.2f}:d=0.4:alpha=1[ab]",
                f"[{akan}][ab]overlay=x='if(lt(t-{a:.2f},0.35),-w+(w+{kenar})*max(0,t-{a:.2f})/0.35,{kenar})':"
                f"y=H-h-{kenar * 3}:enable='between(t,{a:.2f},{a + 4:.2f})'[k3]"]
        akan = "k3"
    return girdiler, suz, akan


def _grup_birlestir(ayar: Ayarlar, klipler: list[tuple[Path, float]], gecisler: list[str], cikti: Path,
                    ofset: float, toplam: float, abone_an: float | None) -> Path:
    """Gruptaki klipleri geçişlerle birleştirir; ardından logo/ilerleme/abone katmanlarını ekler."""
    _, _, fps = boyut(ayar)
    girdiler, suz = [], []
    for i, (yol, _d) in enumerate(klipler):
        girdiler += ["-i", str(yol)]
        suz.append(f"[{i}:v]settb=AVTB,fps={fps},format=yuv420p[c{i}]")
    akan, s = "c0", klipler[0][1]
    for i in range(1, len(klipler)):
        suz.append(f"[{akan}][c{i}]xfade=transition={gecisler[i - 1]}:duration={GECIS}:"
                   f"offset={max(0.05, s - GECIS / 2):.3f}[x{i}]")
        akan, s = f"x{i}", s + klipler[i][1]
    ek, katman, akan = _katmanlar(ayar, len(klipler), akan, ofset, toplam, s, cikti.parent, abone_an)
    _ffmpeg(*girdiler, *ek, "-filter_complex", ";".join(suz + katman + [f"[{akan}]format=yuv420p[son]"]),
            "-map", "[son]", "-t", f"{s:.3f}", "-r", str(fps), "-an", *_kodlama(ayar), str(cikti))
    return cikti


def _kopyala_birlestir(parcalar: list[Path], cikti: Path) -> None:
    liste = cikti.with_suffix(".txt")
    liste.write_text("".join(f"file '{k.resolve()}'\n" for k in parcalar), encoding="utf-8")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", str(cikti))


def anlatim_izi(parcalar: list[tuple[Path | None, float]], cikti: Path) -> Path:
    """Sahne seslerini, her biri kendi süresine tamamlanmış hâlde tek iz yapar (görüntüyle birebir)."""
    girdiler, suz = [], []
    for i, (ses, d) in enumerate(parcalar):
        girdiler += (["-i", str(ses)] if ses else ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"])
        suz.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{d:.3f},"
                   f"asetpts=PTS-STARTPTS[a{i}]")
    suz.append("".join(f"[a{i}]" for i in range(len(parcalar))) + f"concat=n={len(parcalar)}:v=0:a=1[o]")
    _ffmpeg(*girdiler, "-filter_complex", ";".join(suz), "-map", "[o]", "-c:a", "pcm_s16le", str(cikti))
    return cikti


def ses_karistir(ayar: Ayarlar, video: Path, anlatim: Path, cikti: Path, anahtar: str, gecis_anlari: list[float],
                 ruh_hali: str | None = None) -> Path:
    """Anlatım + fon müziği (konuşmada kısılır) + geçiş sesleri → -14 LUFS; görüntü yeniden kodlanmaz."""
    s = ayar["ses"]
    toplam = sure(video)
    tohum = int(hashlib.md5(anahtar.encode()).hexdigest(), 16) % (2 ** 31)
    girdiler = ["-i", str(anlatim)]
    muzikler = sorted((CONFIG / "muzik").glob("*.mp3"))
    muzik = bool(muzikler) or bool(s.get("fon_muzigi"))
    if muzikler:
        girdiler += ["-stream_loop", "-1", "-i", str(muzikler[tohum % len(muzikler)])]
    elif muzik:
        fon = ses_tasarimi.fon_muzigi(cikti.parent / "fon.wav", toplam, tohum, ruh_hali or s.get("ruh_hali", "merakli"))
        girdiler += ["-i", str(fon)]
    efekt = bool(s.get("gecis_sesi") and gecis_anlari)
    if efekt:
        girdiler += ["-i", str(ses_tasarimi.efekt_izi(cikti.parent / "efekt.wav", toplam, gecis_anlari, tohum))]
    vno = 1 + muzik + efekt
    grafik = ses_tasarimi.karisim_suzgeci(float(s["muzik_seviyesi_db"]) + 4, float(s.get("efekt_seviyesi_db", -16)),
                                          muzik, efekt)
    _ffmpeg(*girdiler, "-i", str(video), "-filter_complex", grafik, "-map", f"{vno}:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{toplam:.3f}",
            "-movflags", "+faststart", str(cikti))
    return cikti


# ---------------------------------------------------------------- uzun video

def _plan(icerik: dict, sesler: list[dict], tohum: int) -> list[dict]:
    """Her sahne için süre, hareket ve (bir öncekinden gelen) geçiş türü."""
    rng = random.Random(tohum)
    plan, onceki = [], ""
    for i, (s, ses) in enumerate(zip(icerik["sahneler"], sesler)):
        hareket = "darbe" if i == 0 else rng.choice([h for h in HAREKETLER if h != onceki])
        bolum = bool(s.get("bolum")) and i > 0
        gecis = "fadeblack" if bolum else (rng.choice(CANLI) if rng.random() < 0.2 else rng.choice(YUMUSAK))
        plan.append({"sure": ses["sure"] + NEFES, "hareket": hareket, "bolum": bolum, "gecis": gecis,
                     "guc": 1.25 if i < 3 else 1.0})  # ilk sahneler daha canlı: izleyiciyi tut
        onceki = hareket
    return plan


def uzun_video(ayar: Ayarlar, kod: str, icerik: dict, sesler: list[dict], gorseller: list[dict]) -> dict:
    klasor = CIKTI / kod / "klipler"
    klasor.mkdir(parents=True, exist_ok=True)
    g, y, _ = boyut(ayar)
    v = ayar["video"]
    tohum = int(hashlib.md5(kod.encode()).hexdigest(), 16) % (2 ** 31)
    renk = gorsel.renk(icerik["plan"]["nis"])
    plan = _plan(icerik, sesler, tohum)
    gecisli = bool(v.get("gecis", True))

    # Zaman çizelgesi: (görsel, ses, süre, ...) — intro ve kapanış dâhil
    sahneler: list[dict] = []
    if float(v["intro_saniye"]) > 0:
        kapak = gorsel.shorts_karesi(Path(gorseller[0]["dosya"]), icerik["baslik"], "", klasor / "intro.png", g, y)
        sahneler.append({"resim": kapak, "ses": None, "sure": float(v["intro_saniye"]), "hareket": "yaklas",
                         "bolum": False, "gecis": "fade", "guc": 0.6, "kelimeler": []})
    for p, s, ses, gor in zip(plan, icerik["sahneler"], sesler, gorseller):
        bant = gorsel.bolum_bandi(s["bolum"], klasor / f"bant_{len(sahneler):03d}.png", g, y, renk) \
            if s.get("bolum") and v.get("altyazi_yak") else None
        sahneler.append({**p, "resim": Path(gor["dosya"]), "ses": ses["ses"], "kelimeler": ses["kelimeler"],
                         "bant": bant, "bolum_adi": s.get("bolum")})
    if float(v["outro_saniye"]) > 0:
        site = ayar.nis(icerik["plan"]["nis"]).get("alan_adi") or ""
        kart = gorsel.shorts_karesi(Path(gorseller[-1]["dosya"]), f"Abone ol • {site}".strip(" •"),
                                    "İzlediğin için teşekkürler", klasor / "outro.png", g, y)
        sahneler.append({"resim": kart, "ses": None, "sure": float(v["outro_saniye"]), "hareket": "yaklas",
                         "bolum": True, "gecis": "fadeblack", "guc": 0.5, "kelimeler": [], "kapanis": True})

    # Gruplar: her bölüm başı ve her GRUP sahnede bir yeni grup (gruplar arası kopyalayarak birleşir)
    grup_bas = [i for i, s in enumerate(sahneler) if i == 0 or s["bolum"] or not gecisli]
    sinirlar = []
    for j, b in enumerate(grup_bas):
        bitis = grup_bas[j + 1] if j + 1 < len(grup_bas) else len(sahneler)
        sinirlar += [(k, min(k + GRUP, bitis)) for k in range(b, bitis, GRUP)]

    toplam = sum(s["sure"] for s in sahneler)
    abone_an = toplam * 0.3 if v.get("abone_rozeti") and toplam > 60 else None
    parcalar, bolumler, gecis_anlari, t = [], [], [], 0.0
    for gi, (a, b) in enumerate(sinirlar):
        klipler = []
        for i in range(a, b):
            s = sahneler[i]
            ilk, son = i == a, i == b - 1
            if s.get("bolum_adi"):  # YouTube bölümleri: ilki 0:00'da olmalı
                bolumler.append((0.0 if not bolumler else t, s["bolum_adi"]))
            gecikme = 0.0 if ilk else GECIS / 2         # görüntü sesten yarım geçiş önce başlar
            uzunluk = s["sure"] + (GECIS if not son else gecikme)  # geçiş için kuyruk payı
            sonraki_bolum = son and b < len(sahneler) and sahneler[b]["bolum"]
            klip = sahne_klibi(ayar, s["resim"], uzunluk, klasor / f"{i:03d}.mp4", s["hareket"], s["guc"],
                               s.get("kelimeler"), s.get("bant"), gecikme,
                               karar_gir=0.3 if ilk and s["bolum"] else 0.0,
                               karar_cik=s["sure"] + gecikme if sonraki_bolum else None)
            if s.get("kapanis") and logo_yolu(ayar):
                klip = _kapanis_logosu(ayar, klip, uzunluk)
            klipler.append((klip, s["sure"]))
            if not ilk or gi > 0:
                gecis_anlari.append(t)
            t += s["sure"]
        gecisler = [sahneler[i]["gecis"] for i in range(a + 1, b)]
        parcalar.append(_grup_birlestir(ayar, klipler, gecisler, klasor / f"grup_{gi:03d}.mp4",
                                        t - sum(d for _, d in klipler), toplam, abone_an))

    ham = CIKTI / kod / "ham.mp4"
    _kopyala_birlestir(parcalar, ham)
    anlatim = anlatim_izi([(s.get("ses"), s["sure"]) for s in sahneler], CIKTI / kod / "anlatim.wav")
    final = CIKTI / kod / "final_video.mp4"
    ses_karistir(ayar, ham, anlatim, final, kod, gecis_anlari,
                 ayar.nis(icerik["plan"]["nis"]).get("ruh_hali"))
    for gecici in [*klasor.glob("*.mp4"), ham, anlatim]:  # ara dosyalar diski doldurmasın
        gecici.unlink(missing_ok=True)
    log.info("Uzun video hazır: %s (%.0f sn, %d sahne, %d geçiş)", final, t, len(sahneler), len(gecis_anlari))
    return {"video": final, "sure": t, "bolumler": bolumler}


def _kapanis_logosu(ayar: Ayarlar, klip: Path, saniye: float) -> Path:
    """Kapanış kartına yukarıdan süzülen logo."""
    g, y, fps = boyut(ayar)
    cikti = klip.with_name(klip.stem + "_logo.mp4")
    boy = int(y * 0.3)
    _ffmpeg("-i", str(klip), "-loop", "1", "-framerate", str(fps), "-t", f"{saniye:.3f}", "-i", str(logo_yolu(ayar)),
            "-filter_complex",
            f"[1:v]scale=-1:{boy},format=rgba,fade=t=in:st=0.2:d=0.6:alpha=1[l];"
            f"[0:v][l]overlay=x=(W-w)/2:y='H*0.03+{boy // 4}*exp(-max(0,t-0.2)*4)'[o]",
            "-map", "[o]", "-t", f"{saniye:.3f}", "-an", *_kodlama(ayar, ara=True), str(cikti))
    return cikti


# -------------------------------------------------------------------- Shorts

def shorts_video(ayar: Ayarlar, kod: str, sira: int, baslik: str, ses: dict, arka: Path) -> Path:
    """Dikey Shorts: hareketli arka plan + kelime kelime vurgulanan altyazı + başlık + logo + ses tasarımı."""
    g, y, fps = boyut(ayar, dikey=True)
    klasor = CIKTI / kod / f"shorts_{sira}"
    klasor.mkdir(parents=True, exist_ok=True)
    toplam = ses["sure"] + 0.3
    hiz = max(1.0, min(1.25, toplam / 58.0))  # Shorts 60 sn altında kalsın
    sure_ = toplam / hiz

    # Altyazı katmanları: her kelime anı için bir kare (o an söylenen kelime sarı)
    kelimeler = ses["kelimeler"]
    satirlar = gruplar(kelimeler, en_fazla=3)
    bos = gorsel.seffaf_altyazi([], -1, klasor / "bos.png", g, y)
    parcalar: list[tuple[Path, float]] = []
    an, n = 0.0, 0
    for i, (bas, son, _metin) in enumerate(satirlar):
        grup = [k for k in kelimeler if bas - 1e-6 <= k[0] < (satirlar[i + 1][0] if i + 1 < len(satirlar) else 1e9)]
        sozler = [k[2] for k in grup]
        for j, (kb, _ks, _k) in enumerate(grup):
            if kb > an + 0.03:
                parcalar.append((bos if j == 0 else parcalar[-1][0], kb - an))
                an = kb
            bitis = grup[j + 1][0] if j + 1 < len(grup) else (satirlar[i + 1][0] if i + 1 < len(satirlar) else toplam)
            kare = gorsel.seffaf_altyazi(sozler, j, klasor / f"a{n:04d}.png", g, y)
            n += 1
            parcalar.append((kare, max(0.04, bitis - an)))
            an = bitis
    if not parcalar:
        parcalar.append((bos, toplam))
    liste = klasor / "altyazi.txt"
    satir = [f"file '{p.resolve()}'\nduration {d / hiz:.3f}\n" for p, d in parcalar]
    satir.append(f"file '{parcalar[-1][0].resolve()}'\n")
    liste.write_text("".join(satir), encoding="utf-8")
    ust = gorsel.seffaf_baslik(baslik, klasor / "baslik.png", g, y)

    kare = max(1, math.ceil(sure_ * fps))
    z, x, yy = hareket_ifadesi("darbe", kare, fps, 1.2)
    girdiler = ["-i", str(arka), "-f", "concat", "-safe", "0", "-i", str(liste),
                "-loop", "1", "-framerate", str(fps), "-t", f"{sure_:.3f}", "-i", str(ust)]
    suz = [f"[0:v]scale={2 * g}:{2 * y}:force_original_aspect_ratio=increase,crop={2 * g}:{2 * y},"
           f"zoompan=z='{z}':x='{x}':y='{yy}':d={kare}:s={g}x{y}:fps={fps},eq=brightness=-0.07:saturation=1.15,"
           f"vignette=PI/4[bg]",
           f"[1:v]fps={fps},format=rgba[alt]", "[bg][alt]overlay=0:0:eof_action=pass[v1]",
           "[2:v]format=rgba[ust]", "[v1][ust]overlay=0:0[v2]"]
    ek, katman, akan = _katmanlar(ayar, 3, "v2", 0.0, sure_, sure_, klasor, None)
    video = klasor / "goruntu.mp4"
    _ffmpeg(*girdiler, *ek, "-filter_complex", ";".join(suz + katman + [f"[{akan}]format=yuv420p[son]"]),
            "-map", "[son]", "-t", f"{sure_:.3f}", "-r", str(fps), "-an", *_kodlama(ayar), str(video))

    anlatim = klasor / "anlatim.wav"
    af = f"atempo={hiz:.3f},apad" if hiz > 1.0 else "apad"
    _ffmpeg("-i", str(ses["ses"]), "-af", f"{af},atrim=0:{sure_:.3f}", "-ar", "48000", "-ac", "2", str(anlatim))
    cikti = CIKTI / kod / f"shorts_{sira}.mp4"
    ses_karistir(ayar, video, anlatim, cikti, f"{kod}-s{sira}", [0.05], "enerjik")
    log.info("Shorts hazır: %s", cikti)
    return cikti
