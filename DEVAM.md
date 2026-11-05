# DEVAM — yeni bir Claude oturumu için devir dosyası

> Yeni oturumda yalnızca şunu yaz: **"DEVAM.md dosyasını oku ve 'Sıradaki işler'i sırayla yap. Türkçe konuş."**
> Bu dosya önceki uzun oturumun özetidir; yeni oturum küçük bağlamla, az kullanım hakkı harcayarak devam eder.

## Kullanıcı ve kurallar
- Kullanıcı **yalnızca Türkçe** konuşur, İngilizce bilmez. Cevaplar kısa, sade, Türkçe.
- Her şey **en ucuz / ücretsiz** olmalı. Değişiklikler `ccr-4374ffb0-5crvc3` dalına işlenip gönderilir
  (depoda tek dal var; PR açılamıyor). Commit sonuna atıf satırları eklenir.
- Sistem **Claude'a bağlı değildir**: GitHub Actions'ta ücretsiz, kendiliğinden çalışır. Claude yalnızca geliştirme için.

## Sistem (Das-Hub-qi/das, herkese açık depo → GitHub dakikası sınırsız)
- Python paketi `otonom/` (13 modül + optimizasyon, Öğrenme Mühendisi, kanal sihirbazı, arama motorları).
- **Çok kanal:** `config/kanallar/<kod>.yaml` (nişler, konu kaynakları, dil, ses, biçim, üslup); veri `veri/kanallar/<kod>/`.
  GitHub'da her kanal ayrı paralel iş (matrix) + genel iş. Yeni kanal: Run workflow → `yeni_kanal` + açıklama.
- **Yapay zekâ zinciri:** Claude (anahtar varsa) → Cloudflare Workers AI → yerel Gemma 4 E2B (llama.cpp, ücretsiz).
- **Ses:** Edge TTS → Piper (çevrimdışı). **Görsel:** Pexels → Pixabay → Openverse → yapay zekâ (Cloudflare/Pollinations) → kart.
- **Öğrenme:** Thompson örneklemesi (niş, başlık stili, uzunluk, saat, kaynak), yaşa göre puan, A/B başlık, viral takip, Öğrenme Mühendisi.
- **Güvenlik:** SECURITY.md. **Arama motorları:** `otonom/arama_motoru.py` (IndexNow + Google Search Console).
- **Panel:** `DURUM.md` (her çalıştırmada) ve Kontrol Merkezi: https://claude.ai/artifact/JmGazg5W8YwsfdmMX7WeLf
- Testler: `python -m pytest -q` (24 test), deneme: `python -m otonom haftalik --deneme`.

## Son gerçek deneme (5 Kasım 2026)
- Anahtarsız, yalnızca yerel modelle beta: 8,4 dk video + 2 Shorts üretildi; senaryo 290 → 859 kelime genişletildi.
- Openverse sık 500 hatası veriyor → devre kesici eklendi. Pillow 13.0.0'a yükseltildi (39 açık kapandı).

## Sıradaki işler (kullanıcının son isteği: "YouTube'da bilinirlik için tüm araçlar, algoritmaya göre aksiyon")
1. **`otonom/buyume.py` — YouTube büyüme araçları** (kota: playlist/yorum/güncelleme 50 birim):
   - Niş başına otomatik **oynatma listesi** (playlists.insert, playlistItems.insert); id'ler `veri/kanallar/<k>/oynatma_listeleri.json`.
   - Yüklemeden sonra kanal sahibi olarak **soru içeren ilk yorum** (commentThreads.insert). Sabitleme API'de yok → DURUM'da hatırlat.
   - Günlük **yorum yanıtlama**: allThreadsRelatedToChannelId ile yeni yorumlar, LLM ile kısa yanıt
     (şema {"uygun": bool, "yanit": str}; spam/link/hakaret → yanıtlama), günde en fazla 10, yanıtlananlar json'da.
   - **Yerelleştirme:** uzun videolara İngilizce başlık/açıklama (videos.update part=snippet,localizations).
   - **Kanal SEO:** kanal açıklaması ve anahtar kelimeleri (channels.update brandingSettings) — bir kez/ayda bir.
   - **İç bağlantı:** açıklamaya nişin en çok izlenen videosu ("▶ Şunu da izle"); Shorts açıklamasına aynı konunun uzun videosu.
   - **Erken aksiyon (algoritma):** 2-4 günlük videoda yaşa göre puan çok düşükse erken başlık değişimi +
     yeni küçük resim (yapay zekâ arka planı + alternatif yazı, thumbnails.set); 7 gün sonra değerlendir (m11.ab_testi'ne benzer).
   - **Paylaşım:** isteğe bağlı Telegram (TELEGRAM_BOT_TOKEN, TELEGRAM_KANAL) ve Bluesky (BLUESKY_KULLANICI, BLUESKY_SIFRE)
     ile yeni video duyurusu. Gizlilere `ayarlar.gizli()` ile eriş (TUM_GIZLILER destekli).
   - Bağla: `orkestrator._uzun_uret/_shorts_uret` sonrası + `kanal_gunluk`; DURUM'a "Büyüme" bölümü; testler (deneme modunda API çağrısı yok).
2. **SEO:** `mikro_site.py` yazı sayfalarına VideoObject JSON-LD + og:image (https://i.ytimg.com/vi/<id>/hqdefault.jpg).
3. README'ye: güvenlik bölümü (SECURITY.md bağlantısı), arama motorları (GOOGLE_ARAMA_TOKEN: `python araclar/youtube_token_al.py arama`,
   Google Cloud'da "Site Verification API" ve "Search Console API" etkinleştirilmeli), büyüme araçları.
4. Kontrol Merkezi'ni güncelle (Artifact, aynı URL; dosya yoksa önce `action: read`).

## Kullanım hakkını korumak için
- Her yeni büyük işe **yeni oturumla** başla (bu dosyayı okut). Uzun oturum bağlamı her mesajda yeniden işlenir ve hakkı hızla tüketir.
- Gerekmedikçe uzun test/derleme çıktısı isteme; "kısa özetle" de.
