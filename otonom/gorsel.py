"""Pillow ile görsel üretim yardımcıları: yazı kartı, kapak, Shorts karesi, küçük resim."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_ADAYLARI = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]

NIS_RENKLERI = {"noro": (124, 58, 237), "bilisim": (14, 165, 233), "turizm": (245, 158, 11)}


def font(boyut: int) -> ImageFont.FreeTypeFont:
    for yol in FONT_ADAYLARI:
        if Path(yol).exists():
            return ImageFont.truetype(yol, boyut)
    return ImageFont.load_default(boyut)


def renk(nis_kodu: str) -> tuple[int, int, int]:
    return NIS_RENKLERI.get(nis_kodu, (16, 185, 129))


def kapla(resim: Image.Image, g: int, y: int) -> Image.Image:
    """Görseli bozmadan hedef boyutu tamamen kaplayacak şekilde ölçekler ve kırpar."""
    oran = max(g / resim.width, y / resim.height)
    yeni = resim.convert("RGB").resize((max(g, round(resim.width * oran)), max(y, round(resim.height * oran))),
                                       Image.LANCZOS)
    x0, y0 = (yeni.width - g) // 2, (yeni.height - y) // 2
    return yeni.crop((x0, y0, x0 + g, y0 + y))


def _sar(ciz: ImageDraw.ImageDraw, metin: str, fnt: ImageFont.FreeTypeFont, genislik: int) -> list[str]:
    kelimeler, satirlar, satir = metin.split(), [], ""
    for k in kelimeler:
        dene = f"{satir} {k}".strip()
        if ciz.textlength(dene, font=fnt) <= genislik or not satir:
            satir = dene
        else:
            satirlar.append(satir)
            satir = k
    if satir:
        satirlar.append(satir)
    return satirlar


def ortali_yazi(resim: Image.Image, metin: str, boyut: int, merkez_y: float, genislik_orani: float = 0.86,
                dolgu=(255, 255, 255), kontur: int = 6, en_fazla_yukseklik: float = 0.4) -> None:
    """Yazıyı ortalar; sığmazsa (uzun kelime, çok satır) yazı boyutunu otomatik küçültür."""
    if not metin.strip():
        return
    ciz = ImageDraw.Draw(resim)
    genislik = int(resim.width * genislik_orani)
    while True:
        fnt = font(boyut)
        satirlar = _sar(ciz, metin, fnt, genislik)
        sigiyor = all(ciz.textlength(s, font=fnt) <= genislik for s in satirlar)
        if (sigiyor and len(satirlar) * boyut * 1.18 <= resim.height * en_fazla_yukseklik) or boyut <= 14:
            break
        boyut = int(boyut * 0.9)
    kontur = max(2, min(kontur, boyut // 12))
    yukseklik = boyut * 1.18
    y = resim.height * merkez_y - len(satirlar) * yukseklik / 2
    for s in satirlar:
        ciz.text((resim.width / 2, y), s, font=fnt, fill=dolgu, anchor="ma",
                 stroke_width=kontur, stroke_fill=(0, 0, 0))
        y += yukseklik


def yazi_karti(metin: str, yol: Path, g: int, y: int, ana_renk=(16, 185, 129)) -> Path:
    """Stok görsel bulunamazsa kullanılan degrade arka planlı kart (metin boşsa yazısız)."""
    resim = Image.new("RGB", (g, y))
    ust, alt = ana_renk, tuple(int(c * 0.25) for c in ana_renk)
    ciz = ImageDraw.Draw(resim)
    for i in range(y):
        t = i / y
        ciz.line([(0, i), (g, i)], fill=tuple(int(ust[k] * (1 - t) + alt[k] * t) for k in range(3)))
    ortali_yazi(resim, textwrap.shorten(metin, 60, placeholder="…"), max(24, min(g, y) // 9), 0.5)
    yol.parent.mkdir(parents=True, exist_ok=True)
    resim.save(yol, quality=90)
    return yol


def shorts_karesi(arka: Path, metin: str, ust_baslik: str, yol: Path, g: int, y: int) -> Path:
    """Koyulaştırılmış arka plan + üstte başlık + ortada büyük metin (Shorts, intro, outro)."""
    resim = kapla(Image.open(arka), g, y)
    resim = ImageEnhance.Brightness(resim.filter(ImageFilter.GaussianBlur(2))).enhance(0.55)
    taban = min(g, y)
    if ust_baslik:
        ortali_yazi(resim, ust_baslik, max(18, taban // 14), 0.14, kontur=4, dolgu=(255, 230, 80),
                    en_fazla_yukseklik=0.16)
    ortali_yazi(resim, metin, max(24, taban // 9), 0.55, en_fazla_yukseklik=0.45)
    resim.save(yol)
    return yol


def kucuk_resim(arka: Path, yazi: str, yol: Path, ana_renk=(16, 185, 129)) -> Path:
    """1280x720, büyük okunur yazı, sol tarafta koyu degrade, niş renginde şerit. <2 MB JPEG."""
    g, y = 1280, 720
    resim = ImageEnhance.Contrast(kapla(Image.open(arka), g, y)).enhance(1.15)
    katman = Image.new("L", (g, y))
    ciz_k = ImageDraw.Draw(katman)
    for x in range(g):
        ciz_k.line([(x, 0), (x, y)], fill=int(210 * max(0.0, 1 - x / (g * 0.75))))
    resim = Image.composite(Image.new("RGB", (g, y), (0, 0, 0)), resim, katman)
    ciz = ImageDraw.Draw(resim)
    ciz.rectangle([0, y - 22, g, y], fill=ana_renk)
    boyut = 120
    while boyut > 50:
        fnt = font(boyut)
        satirlar = _sar(ciz, yazi.upper() if len(yazi) < 18 else yazi, fnt, int(g * 0.62))
        if len(satirlar) <= 3:
            break
        boyut -= 8
    toplam = len(satirlar) * boyut * 1.1
    yy = (y - toplam) / 2
    for i, s in enumerate(satirlar):
        ciz.text((60, yy), s, font=fnt, fill=(255, 225, 60) if i == 0 else (255, 255, 255),
                 stroke_width=8, stroke_fill=(0, 0, 0))
        yy += boyut * 1.1
    resim.save(yol, "JPEG", quality=88, optimize=True)
    return yol
