# 📊 Sistem Durumu

_Son çalıştırma: 2026-11-05 12:50 · komut: `durum` · ✅ Sorunsuz_

## ⚡ Hızlı erişim

- 🧭 **Kontrol Merkezi** (tüm sistem tek sayfada): [aç](https://claude.ai/artifact/JmGazg5W8YwsfdmMX7WeLf)
- ▶️ **Çalıştır** (beta / haftalık / günlük): [Actions > Otonom sistem > Run workflow](https://github.com/Das-Hub-qi/das/actions/workflows/otonom.yml)
- 🔑 **Anahtarlar**: [Settings > Secrets](https://github.com/Das-Hub-qi/das/settings/secrets/actions)
- 🛠️ **Mühendisin açtığı iş kayıtları**: [Issues](https://github.com/Das-Hub-qi/das/issues)
- ⚙️ **Ayarlar**: [ayarlar.yaml](config/ayarlar.yaml) · [varliklar.yaml](config/varliklar.yaml) (dosyayı açıp kalem simgesine dokunun)
- 📈 **Raporlar**: [veri/raporlar](veri/raporlar) · 👷 [Mühendis günlüğü](veri/muhendis_gunlugu.md) · 🗓️ [İçerik takvimi](veri/icerik_takvimi.md)
- 💰 **Teklifler**: [yanıt taslakları](veri/teklif_taslaklari) · 🏷️ [satış metinleri](veri/alan_adlari)
- 🌐 **Siteler**: [trustneurohub.com.tr](https://trustneurohub.com.tr) · [okyanusbilisimtr.com](https://okyanusbilisimtr.com)
- 🎬 **YouTube Studio**: [studio.youtube.com](https://studio.youtube.com)
- ☁️ **Cloudflare**: [dash.cloudflare.com](https://dash.cloudflare.com) · 📖 [Kurulum rehberi](README.md)

## Kurulum kontrol listesi
8 madde tamamlanabilir — sistem bunlar olmadan da çalışır.

| | Parça | Durum | Ne yapmalı? |
|---|---|---|---|
| ✅ | Yapay zekâ | Ücretsiz yerel model (gemma-4-E2B-it) | İsteğe bağlı: daha kaliteli metin için `ANTHROPIC_API_KEY` (README adım 1) |
| ✅ | Seslendirme | Edge TTS (yedek: çevrimdışı Piper) | — |
| ⚠️ | Görseller | Yalnızca anahtarsız Openverse + yazı kartı | Ücretsiz `PEXELS_API_KEY` ekleyin: görsel kalitesi artar (README adım 2) |
| ❌ | YouTube yükleme | Bağlı değil — videolar Actions > Artifacts'tan indirilebilir | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (README adım 3) |
| ⚠️ | YouTube istatistik / rekabet | Kapalı (niş analizi yalnızca arama önerileriyle) | `YOUTUBE_API_KEY` (README adım 3.2) |
| ❌ | Siteler + teklif formu (Cloudflare) | Kurulmadı | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (README adım 4) |
| ⚠️ | Kanal kimliği | Boş | `config/varliklar.yaml` > kanal_id (abone ol linki için) |
| ⚠️ | Nişlerin alan adları | Alan adı yok: Turizm ve Seyahat | `config/varliklar.yaml` > nisler > alan_adi |
| ⚠️ | Ortaklık (affiliate) linkleri | 0 link | `config/varliklar.yaml` > ortaklik_linkleri (ek gelir) |
| ⚠️ | Arka plan müziği | 0 parça | YouTube Ses Kitaplığı'ndan mp3 → `config/muzik/` |

## Ücretsiz sınırlar
- GitHub dakikası (bu ay): **0** / 2000 · ay sonu tahmini 0 · mod: **normal**
- YouTube API kotası (bugün): **0** / 10000
- Yapay zekâ harcaması (toplam): **0.000 $**
- Sınır dolarsa sistem durmaz: üretimi azaltır, yüklemeyi ertesi güne bırakır veya yedek servise geçer.

## Üretim
- Bekleyen: **0** · yüklendi: 0 · elle yüklenecek: 0 · hata: 0
- Yapay zekâda bekleyen toplu iş: yok

## Gelir (bu ay)
- Alan adı teklifleri: **0**
- Ortaklık link tıklamaları: **0**
- Ayrıntılı raporlar: `veri/raporlar/`

## Laboratuvar öğrenimi
Her seçeneğin şu an 'en iyi' olma olasılığı (Thompson örneklemesi). Veri arttıkça netleşir; sistem yüksek olasılıklı seçeneği daha sık, diğerlerini ara sıra dener.
- Henüz yeterli veri yok (videolar yayınlanıp en az 7 gün geçince öğrenme başlar).

## Öğrenme Mühendisi
Her hafta sistemi kendi verisiyle geliştirir; tüm değişiklikler `veri/muhendis_gunlugu.md`'de. Sıfırlamak için `veri/ogrenilen_ayarlar.yaml` dosyasını silin.
- Henüz çalışmadı (ilk haftalık döngüde başlar).

## Otomatik takvim (Türkiye saati)
- Pazartesi 09:17 — haftalık plan ve senaryolar · Pazartesi 13:37 — video üretimi
- Her gün 07:07 — yükleme, teklifler, site güncellemesi
- Elle çalıştırmak için: GitHub > Actions > Otonom sistem > Run workflow
