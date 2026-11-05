"""Yapay zekâ katmanı — iki sağlayıcı, en düşük maliyet için ayarlı.

  * "yerel"  : ücretsiz yerel model (yerel_llm.py) — API anahtarı ve ücret yok.
  * "claude" : Claude API (daha kaliteli Türkçe, ayda birkaç kuruş).
  * "otomatik" (varsayılan): ANTHROPIC_API_KEY varsa Claude, yoksa yerel model.

Claude için maliyet düşürme yöntemleri:
Maliyet düşürme yöntemleri:
  1. En ucuz model (Claude Haiku 5.5) varsayılan.
  2. Toplu işlem (Message Batches API): tüm tokenlarda %50 indirim.
     GitHub Actions'ta beklerken dakika harcamamak için iki aşamalı çalışır:
     istek gönderilir, kimliği kaydedilir, sonuç bir sonraki çalıştırmada alınır.
  3. Ortak sistem talimatı önbelleğe alınır (prompt caching).
  4. Yapılandırılmış JSON çıktı: bozuk çıktı yüzünden tekrar deneme maliyeti yok.
  5. Tek çağrıda senaryo + başlık + açıklama + Shorts + blog yazısı üretilir.
Her çağrının maliyeti veri/maliyet.csv dosyasına yazılır.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from .ayarlar import VERI, Ayarlar, csv_ekle, gizli, log

# 1M token başına $ (girdi, çıktı) — Anthropic fiyat listesi
FIYATLAR = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
MALIYET_DOSYASI = VERI / "maliyet.csv"


class LLMHatasi(RuntimeError):
    pass


def saglayici(ayar: Ayarlar) -> str:
    secim = ayar["llm"].get("saglayici", "otomatik")
    if secim == "otomatik":
        return "claude" if (gizli("ANTHROPIC_API_KEY") or gizli("ANTHROPIC_AUTH_TOKEN")) else "yerel"
    return secim


def toplu_mu(ayar: Ayarlar) -> bool:
    """Toplu işlem yalnızca Claude'da anlamlı (yerel model zaten ücretsiz ve anlık)."""
    return bool(ayar["llm"]["toplu_islem"]) and not ayar.deneme and saglayici(ayar) == "claude"


def _istemci():
    import anthropic

    if not (gizli("ANTHROPIC_API_KEY") or gizli("ANTHROPIC_AUTH_TOKEN")):
        raise LLMHatasi(
            "ANTHROPIC_API_KEY tanımlı değil. GitHub > Settings > Secrets'a ekleyin "
            "veya test için --deneme kullanın."
        )
    return anthropic.Anthropic(max_retries=4)


def _parametreler(model: str, sistem: str, istem: str, sema: dict, efor: str, max_tokens: int) -> dict:
    return {
        "model": model,
        "max_tokens": max_tokens,
        # Sabit sistem talimatı en başta ve önbellek işaretli: tekrar eden isteklerde ucuzlar.
        "system": [{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": istem}],
        "output_config": {"effort": efor, "format": {"type": "json_schema", "schema": sema}},
    }


def _maliyet(model: str, usage: Any, toplu: bool) -> float:
    girdi, cikti = FIYATLAR.get(model, FIYATLAR["claude-haiku-5-5"])
    okunan = getattr(usage, "cache_read_input_tokens", 0) or 0
    yazilan = getattr(usage, "cache_creation_input_tokens", 0) or 0
    dolar = (
        usage.input_tokens * girdi
        + okunan * girdi * 0.1
        + yazilan * girdi * 1.25
        + usage.output_tokens * cikti
    ) / 1_000_000
    return dolar * (0.5 if toplu else 1.0)


def _kaydet(gorev: str, model: str, usage: Any, toplu: bool) -> None:
    csv_ekle(
        MALIYET_DOSYASI,
        [{
            "gorev": gorev,
            "model": model,
            "toplu": int(toplu),
            "girdi_token": usage.input_tokens,
            "cikti_token": usage.output_tokens,
            "onbellek_okunan": getattr(usage, "cache_read_input_tokens", 0) or 0,
            "dolar": f"{_maliyet(model, usage, toplu):.6f}",
        }],
        ["gorev", "model", "toplu", "girdi_token", "cikti_token", "onbellek_okunan", "dolar"],
    )


def _mesajdan_json(mesaj: Any, gorev: str) -> dict:
    if mesaj.stop_reason == "refusal":
        raise LLMHatasi(f"[{gorev}] model isteği reddetti; konu değiştirilmeli.")
    if mesaj.stop_reason == "max_tokens":
        raise LLMHatasi(f"[{gorev}] çıktı yarıda kesildi (max_tokens); hedef kelime sayısını düşürün.")
    metin = next((b.text for b in mesaj.content if b.type == "text"), "")
    try:
        return json.loads(metin)
    except json.JSONDecodeError as e:
        raise LLMHatasi(f"[{gorev}] geçersiz JSON: {e}") from e


def yerel_kullanilabilir() -> bool:
    import importlib.util

    return importlib.util.find_spec("llama_cpp") is not None


def _yerel_json(ayar: Ayarlar, gorev: str, sistem: str, istem: str, sema: dict, max_tokens: int) -> dict:
    """Yerel model; çıktı yarım kalırsa metinleri kısaltma talimatıyla bir kez daha dener."""
    from . import yerel_llm

    for deneme in range(2):
        ek = "" if deneme == 0 else "\n\nÖNEMLİ: Önceki deneme sığmadı. Tüm metinleri yaklaşık yarı uzunlukta yaz."
        metin, neden, kullanim = yerel_llm.json_uret(ayar, sistem, istem + ek, sema, max_tokens)
        csv_ekle(MALIYET_DOSYASI, [{
            "gorev": gorev, "model": "yerel:" + ayar["llm"]["yerel_dosya"], "toplu": 0,
            "girdi_token": kullanim.get("prompt_tokens", 0), "cikti_token": kullanim.get("completion_tokens", 0),
            "onbellek_okunan": 0, "dolar": "0"}],
            ["gorev", "model", "toplu", "girdi_token", "cikti_token", "onbellek_okunan", "dolar"])
        if neden != "length":
            try:
                return json.loads(metin)
            except json.JSONDecodeError:
                pass
        log.warning("[%s] yerel model çıktısı yarım kaldı, kısaltılarak tekrar deneniyor.", gorev)
    raise LLMHatasi(f"[{gorev}] yerel model iki denemede de tamamlayamadı; llm.yerel_baglam değerini artırın.")


def _claude_json(ayar: Ayarlar, gorev: str, sistem: str, istem: str, sema: dict, efor: str | None,
                 max_tokens: int) -> dict:
    import anthropic

    model = ayar["llm"]["model"]
    try:
        mesaj = _istemci().messages.create(
            **_parametreler(model, sistem, istem, sema, efor or ayar["llm"]["kisa_is_efor"], max_tokens)
        )
    except anthropic.AuthenticationError as e:
        raise LLMHatasi("API anahtarı geçersiz (ANTHROPIC_API_KEY).") from e
    except anthropic.APIStatusError as e:
        raise LLMHatasi(f"[{gorev}] API hatası {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMHatasi(f"[{gorev}] ağ hatası: {e}") from e
    _kaydet(gorev, model, mesaj.usage, toplu=False)
    return _mesajdan_json(mesaj, gorev)


def json_uret(
    ayar: Ayarlar,
    gorev: str,
    sistem: str,
    istem: str,
    sema: dict,
    sahte: Callable[[], dict],
    efor: str | None = None,
    max_tokens: int = 16000,
) -> dict:
    """Tek, anlık istek. Deneme modunda `sahte()` çıktısını döner.

    Yedek zinciri: Claude kullanılamazsa (kredi bitti, kota, ağ, geçersiz anahtar) iş durmaz,
    ücretsiz yerel modelle devam edilir ve DURUM.md'de uyarı gösterilir.
    """
    if ayar.deneme:
        return sahte()
    if saglayici(ayar) == "claude":
        try:
            return _claude_json(ayar, gorev, sistem, istem, sema, efor, max_tokens)
        except LLMHatasi as e:
            if "reddetti" in str(e) or not yerel_kullanilabilir():
                raise
            from .ayarlar import uyari_ekle
            uyari_ekle("yapay zekâ", f"Claude kullanılamadı ({e}); ücretsiz yerel modelle devam edildi.")
    return _yerel_json(ayar, gorev, sistem, istem, sema, max_tokens)


# ------------------------------------------------------------- toplu işlem

def toplu_gonder(ayar: Ayarlar, istekler: list[dict]) -> str:  # yalnızca Claude
    """istekler: [{"id", "sistem", "istem", "sema", "efor", "max_tokens"}] -> batch kimliği"""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    model = ayar["llm"]["model"]
    batch = _istemci().messages.batches.create(
        requests=[
            Request(
                custom_id=i["id"],
                params=MessageCreateParamsNonStreaming(
                    **_parametreler(model, i["sistem"], i["istem"], i["sema"], i["efor"], i.get("max_tokens", 16000))
                ),
            )
            for i in istekler
        ]
    )
    log.info("Toplu istek gönderildi: %s (%d iş)", batch.id, len(istekler))
    return batch.id


def toplu_sonuc(ayar: Ayarlar, batch_id: str) -> dict[str, dict | str] | None:
    """Bitmediyse None. Bittiyse {custom_id: json | 'HATA: ...'}"""
    istemci = _istemci()
    batch = istemci.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        log.info("Toplu iş %s henüz bitmedi (%s).", batch_id, batch.processing_status)
        return None
    model = ayar["llm"]["model"]
    sonuc: dict[str, dict | str] = {}
    for r in istemci.messages.batches.results(batch_id):
        if r.result.type == "succeeded":
            msg = r.result.message
            _kaydet(r.custom_id, model, msg.usage, toplu=True)
            try:
                sonuc[r.custom_id] = _mesajdan_json(msg, r.custom_id)
            except LLMHatasi as e:
                sonuc[r.custom_id] = f"HATA: {e}"
        else:
            sonuc[r.custom_id] = f"HATA: {r.result.type}"
    return sonuc


def toplam_maliyet() -> float:
    from .ayarlar import csv_oku

    return sum(float(s["dolar"]) for s in csv_oku(MALIYET_DOSYASI))
