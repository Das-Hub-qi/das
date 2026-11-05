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
- **Öğrenme:** HİYERARŞİK (konuya göre) Thompson: her niş kendi başlık stili/uzunluk/saat/kaynak kazananını öğrenir, az verili niş kanal genelinden %30 ödünç alır (`optimizasyon.nis_posterior`). Yaşa göre puan, A/B başlık, viral takip, Öğrenme Mühendisi.
- **Güvenlik:** SECURITY.md. **Arama motorları:** `otonom/arama_motoru.py` (IndexNow + Google Search Console).
- **Panel:** `DURUM.md` (her çalıştırmada) ve Kontrol Merkezi: https://claude.ai/artifact/JmGazg5W8YwsfdmMX7WeLf
- Testler: `python -m pytest -q` (29 test), deneme: `python -m otonom haftalik --deneme`.

## Son gerçek deneme (5 Kasım 2026)
- Anahtarsız, yalnızca yerel modelle beta: 8,4 dk video + 2 Shorts üretildi; senaryo 290 → 859 kelime genişletildi.
- Openverse sık 500 hatası veriyor → devre kesici eklendi. Pillow 13.0.0'a yükseltildi (39 açık kapandı).

## Tamamlananlar (5 Kasım 2026, 2. oturum)
- `otonom/buyume.py`: oynatma listeleri, soru içeren sahip yorumu (sabitleme hatırlatması DURUM'da), günlük yorum yanıtlama
  (≤10, bağlantı/spam filtresi, LLM şeması {"uygun","yanit"}), İngilizce yerelleştirme, aylık kanal SEO, iç bağlantı
  (yükleme öncesi açıklamaya), erken aksiyon (2-4 gün, zayıfsa başlık + yeni küçük resim → m11 A/B dosyasına "test"),
  Telegram/Bluesky duyurusu. Yayın sonrası adımlar `veri/kanallar/<k>/buyume.json` ile takip edilir.
- Bağlantılar: `kanal_gunluk` → "Büyüme" adımı; `_uzun_uret/_shorts_uret` → iç bağlantı; yeni komut `buyume`
  (workflow seçeneklerine de eklendi); DURUM.md'de "🚀 Büyüme" bölümü (tüm kanallar).
- `mikro_site.py`: yazı sayfalarına VideoObject JSON-LD + og:image. README: F (arama motorları), G (paylaşım),
  Büyüme araçları ve Güvenlik bölümleri. `.env.example`'a yeni anahtarlar. Testler: 29.

## Sıradaki işler
1. **Kontrol Merkezi'ni güncelle** (Artifact, aynı URL https://claude.ai/artifact/JmGazg5W8YwsfdmMX7WeLf;
   önce `action: read`): Büyüme bölümü + yeni gizliler (TELEGRAM_*, BLUESKY_*, GOOGLE_ARAMA_TOKEN).
2. Gerçek kanalda ilk günlük çalıştırmadan sonra DURUM.md "Büyüme" bölümünü kontrol et; YouTube anahtarı eski ise
   yorum/oynatma listesi izni için `python araclar/youtube_token_al.py <kanal>` ile yenilenmeli.
3. İsteğe bağlı fikirler: Shorts'tan uzun videoya "ilgili video" bağlantısı (API'de yok, Studio'dan elle);
   en iyi yorumlardan yeni video konusu çıkarma (oncelikli_konular.json'a).

## Kullanım hakkını korumak için
- Her yeni büyük işe **yeni oturumla** başla (bu dosyayı okut). Uzun oturum bağlamı her mesajda yeniden işlenir ve hakkı hızla tüketir.
- Gerekmedikçe uzun test/derleme çıktısı isteme; "kısa özetle" de.
