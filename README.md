# Otonom Gelir ve İçerik Sistemi

YouTube içerik üretimi + alan adı gelirini **ücretsiz bulut katmanlarında** çalıştıran,
kendi kendini iyileştiren otomasyon sistemi.

- **Çalışma masası (üretim hattı):** niş analizi → plan → senaryo → ses → görsel → montaj → küçük resim → YouTube
- **Laboratuvar:** her hafta performansı ölçer, kazanan nişlere daha çok video ayırır, viral videoların devamını planlar
- **Alan adları:** her alan adına ücretsiz site (Cloudflare Pages), satış/kiralama teklif formu, hazır satış metinleri

---

## 💰 Maliyet: neredeyse sıfır

| Hizmet | Ne için | Ücret |
|---|---|---|
| GitHub Actions | Zamanlayıcı + video üretimi | **0 ₺** (özel depoda ayda 2.000 dk; sistem ~100-200 dk kullanır) |
| Cloudflare Pages + Workers + KV | Siteler, teklif formu, link takibi | **0 ₺** (sınırsız trafik, ücretsiz SSL) |
| Cloudflare Email Routing + Web Analytics | teklif@alanadınız → Gmail, ziyaretçi sayımı | **0 ₺** |
| Microsoft Edge TTS | Türkçe seslendirme | **0 ₺** |
| Pexels + Pixabay + Openverse | Telifsiz fotoğraflar (Openverse anahtar bile istemez) | **0 ₺** |
| YouTube Data API | Yükleme + istatistik | **0 ₺** (günlük ücretsiz kota) |
| Claude Haiku 5.5 (yapay zekâ) | Senaryo, plan, satış metinleri | **≈ 0,01-0,05 $/ay** (toplu işlemle %50 indirimli) |

Tek gerçek ödeme: Anthropic hesabına bir kez yüklenen **5 $** kredi (bu kullanımla yıllarca yeter)
ve alan adlarınızın yıllık yenileme ücreti (zaten ödüyorsunuz).

## ⚡ Orijinal plana göre yapılan verimlilik iyileştirmeleri

| Orijinal | Yeni | Kazanç |
|---|---|---|
| Senaryo, açıklama, makale ayrı ayrı | **Tek yapay zekâ çağrısı** → 1 uzun video + 2 Shorts + 1 site makalesi + başlık/açıklama/etiket | Aynı maliyetle 4 içerik |
| Anlık yapay zekâ çağrısı | **Toplu işlem (Batch API)**: Pazartesi gönderilir, öğlen alınır | %50 ucuz, bekleme dakikası harcanmaz |
| MoviePy | **Doğrudan ffmpeg**, sahne başına kodlama + kopyalayarak birleştirme | 5-10 kat hızlı, ücretsiz dakikalar korunur |
| Skor = İzlenme×0,5 + CTR×0,3 + Süre×0,2 | **Yüzdelik sıra** puanı (ölçek farkı yok), Shorts/uzun ayrı | Gerçekten iyi videoyu bulur |
| Sabit 4 haftalık takvim | **Her hafta güncel veriyle plan** + kazanan nişe daha çok video (%20 keşif payı) | Sistem kendini iyileştirir |
| Google Sheets | Depodaki **CSV + Markdown rapor** | Ek hesap/izin yok, geçmiş saklanır |
| Açıklamaya doğrudan ortaklık linki | **Kendi alan adınızdan kısa link** (`/git/kurs`) + tıklama sayımı | Link değişince eski videolar otomatik düzelir |
| 3 sn boş intro | Doğrudan **kanca** ile başlangıç (isteğe bağlı açılır) | İlk saniyelerde izleyici kaybı azalır |
| — | **Otomatik bölüm (chapter) zaman damgaları** + altyazı yükleme | Google aramada görünürlük, izlenme süresi |
| — | Videolar **Salı/Perşembe/Cumartesi 18:00**'e zamanlanır | Düzenli yayın, sıfır müdahale |
| Domain parking | Ücretsiz **site + teklif formu**; teklif gelince yanıt taslağı hazırlanır | Park gelirinden fazlası, sıfır maliyet |

---

## 🚀 Kurulum (bir kez, yaklaşık 1-2 saat)

> Her adımda aldığınız anahtarları **GitHub > deponuz > Settings > Secrets and variables > Actions >
> New repository secret** bölümüne, tablodaki adla ekleyin. Anahtarları asla dosyalara yazmayın.

### 1. Yapay zekâ anahtarı (zorunlu)
1. https://console.anthropic.com adresinde hesap açın, **Billing**'den 5 $ kredi yükleyin.
2. **API Keys > Create Key** → `ANTHROPIC_API_KEY` olarak ekleyin.

### 2. Görsel anahtarları (ücretsiz, önerilir)
- https://www.pexels.com/api → `PEXELS_API_KEY`
- https://pixabay.com/api/docs → `PIXABAY_API_KEY`

(Anahtar yoksa sistem anahtarsız Openverse'ten CC0 fotoğraf arar, o da bulamazsa renkli yazı kartı kullanır.
Pexels anahtarı görsel kalitesini belirgin şekilde artırır.)

### 3. YouTube bağlantısı
1. https://console.cloud.google.com → yeni proje → **APIs & Services > Library**:
   "YouTube Data API v3" ve "YouTube Analytics API"yi **Enable** edin.
2. **Credentials > Create credentials > API key** → `YOUTUBE_API_KEY` (istatistik ve niş analizi için).
3. **OAuth consent screen**: "External" seçin, uygulamayı **"In production" (Üretimde)** yapın.
   ⚠️ "Testing" modunda kalırsa bağlantı 7 günde kopar.
4. **Credentials > Create credentials > OAuth client ID > Desktop app** → JSON'u indirin,
   bilgisayarınızda `client_secret.json` adıyla bu klasöre koyun ve çalıştırın:
   ```
   pip install google-auth-oauthlib
   python araclar/youtube_token_al.py
   ```
   Çıkan `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` değerlerini Secrets'a ekleyin.
5. YouTube kanalınızı telefonla doğrulayın (youtube.com/verify) — özel küçük resim için gerekli.
6. ⚠️ **Önemli:** Google, denetimden geçmemiş API projelerinin yüklediği videoları **gizli** tutar.
   Bu yüzden sistem videoları varsayılan olarak "gizli" yükler; siz YouTube Studio'da kontrol edip
   tek tıkla yayınlarsınız (bu aynı zamanda haftalık kalite kontrolünüzdür).
   Tam otomatik yayın için ücretsiz **YouTube API Audit** formunu doldurun; onaydan sonra
   `config/ayarlar.yaml` içinde `gizlilik: "zamanla"` yapın.

> YouTube bağlantısı kurmazsanız da sistem çalışır: videolar her çalıştırmada GitHub
> **Actions > ilgili çalıştırma > Artifacts** bölümüne konur, oradan indirip elle yüklersiniz.

### 4. Cloudflare (siteler, teklif formu, link takibi)
1. https://dash.cloudflare.com → ücretsiz hesap → **Add a domain** ile alan adlarınızı ekleyin,
   alan adı firmanızda (kayıt firması) nameserver'ları Cloudflare'in verdikleriyle değiştirin.
2. **Workers & Pages > KV > Create namespace** → adı `TEKLIFLER` → çıkan kimliği `CF_KV_NAMESPACE_ID` olarak ekleyin.
3. **My Profile > API Tokens > Create Token > Custom token** izinleri:
   *Account – Cloudflare Pages – Edit* ve *Account – Workers KV Storage – Edit* → `CLOUDFLARE_API_TOKEN`.
4. Sağ menüdeki **Account ID** → `CLOUDFLARE_ACCOUNT_ID`.
5. İlk çalıştırmadan sonra **Workers & Pages** altında her alan adı için bir proje oluşur
   (ör. `trustneurohub-com-tr`). Projeye girip **Custom domains > Set up a domain** ile alan adınızı bağlayın.
6. (İsteğe bağlı) **Email > Email Routing**: `teklif@alanadiniz` → Gmail'inize yönlendirin.
7. (İsteğe bağlı) **Web Analytics** → site ekleyin, token'ı `config/ayarlar.yaml` > `cloudflare.web_analytics_token`'a yazın.

### 5. Kendi bilgilerinizi girin
`config/varliklar.yaml` dosyasını GitHub'da açıp (kalem simgesi) düzenleyin:
- `kanal_id`: YouTube Studio > Ayarlar > Kanal > Gelişmiş ayarlar ("UC..." ile başlar)
- Turizm alan adlarınız (dosyadaki örnek satırların başındaki `#` işaretini kaldırın)
- Ortaklık (affiliate) linkleriniz: `kisa-ad: "https://..."` biçiminde
- İsterseniz nişlerin tohum kelimelerini değiştirin

### 6. Önce beta deneyin (önerilir)
GitHub > **Actions > Otonom sistem > Run workflow** → `beta` seçip çalıştırın.
Sistem 1 gerçek video + 2 Shorts + site sayfası üretir, **YouTube'a yüklemez**.
5-10 dakika sonra çalıştırmanın sayfasında en altta **Artifacts** bölümünden indirip izleyin.

### 7. Başlatın
GitHub > **Actions > Otonom sistem > Run workflow** → `haftalik` seçip çalıştırın.
Sonrası otomatik: her Pazartesi plan, her gün üretim/yükleme/teklif kontrolü.
Bir adım hata verirse GitHub size **ücretsiz e-posta** gönderir.

---

## 🗓️ Otomatik takvim

| Ne zaman (TR saati) | Ne olur |
|---|---|
| Pazartesi 09:17 | Laboratuvar raporu → niş analizi → haftalık plan → senaryolar (toplu, %50 ucuz) → alan adı metinleri → siteler |
| Pazartesi 13:37 | Hazır senaryolardan 3 uzun video + 6 Shorts üretilir ve yüklenir |
| Her gün 07:07 | Kalan yüklemeler (kota), viral video kontrolü, yeni teklifler, link tıklamaları, site güncellemesi |
| Salı/Perşembe/Cumartesi 18:00 | Uzun videolar yayına girer (`gizlilik: "zamanla"` iken) |

## ✅ Haftalık 15 dakikalık kontrol (insan denetimi)
1. YouTube Studio'da yeni videoları izleyin (hızlıca), sorun yoksa **Yayınla** / zamanlamayı onaylayın.
2. Bitiş ekranı ekleyin: Studio > video > **Bitiş ekranı > Videodan içe aktar** (tek tık).
3. `veri/raporlar/` içindeki son laboratuvar raporuna bakın; "yeniden düzenlenecekler" listesindeki
   videoların başlık/küçük resmini değiştirin.
4. `veri/teklif_taslaklari/` klasöründe yeni teklif varsa yanıtı kontrol edip gönderin.

## 📁 Dosya haritası

| Dosya | Görev |
|---|---|
| `config/ayarlar.yaml` | Genel ayarlar (model, video sayısı, ses, yayın saatleri) |
| `config/varliklar.yaml` | Alan adları, nişler, ortaklık linkleri |
| `otonom/m01_envanter.py` … `m12_gelir.py` | Master prompttaki 12 modül |
| `otonom/mikro_site.py` | Cloudflare Pages siteleri |
| `otonom/orkestrator.py` | Haftalık / günlük döngü |
| `cloudflare/functions/` | Teklif formu ve kısa link fonksiyonları |
| `veri/` | Sistemin hafızası: planlar, senaryolar, metrikler, raporlar, teklifler |
| `MASTER_PROMPT.md` | Sistemin güncellenmiş ana talimatı (başka yapay zekâ ajanlarına da verilebilir) |

## 🖥️ Kendi bilgisayarınızda deneme
```
pip install -r requirements.txt          # ayrıca ffmpeg kurulu olmalı
python -m otonom haftalik --deneme       # hiçbir servise bağlanmadan uçtan uca test
python -m pytest -q                      # testler
```
Gerçek çalıştırma için `.env.example` dosyasını `.env` adıyla kopyalayıp doldurun.
Komutlar: `beta, haftalik, gunluk, envanter, nis, plan, uret, alanadi, site, analiz, teklifler, rapor, maliyet`

---

## ⚠️ Gerçekçi beklentiler (lütfen okuyun)

- **YouTube para kazanma şartı:** 1.000 abone + son 12 ayda 4.000 saat izlenme
  (veya 90 günde 10 milyon Shorts izlenmesi). Bu genelde aylar sürer; garantisi yoktur.
- **"Özgün olmayan içerik" politikası:** YouTube, toplu üretilmiş, birbirinin tekrarı yapay zekâ
  videolarını para kazanmadan çıkarabilir. Bu yüzden sistem her videoya özgün bir "bakış açısı"
  zorunlu kılar ve haftalık insan kontrolü vardır. Fark yaratmak için zaman zaman kendi sesinizle
  yorum eklemeniz veya kendi deneyiminizi anlatmanız çok faydalıdır.
- **Alan adı satışı:** Çoğu alan adı yıllarca satılmayabilir; fiyatı uydurmak yerine "teklife açık"
  satış yapılır. Sitedeki içerik arttıkça alan adının değeri ve teklif ihtimali artar.
- **Sağlık nişi:** Teşhis/tedavi vaadi yasaktır; senaryo talimatları buna göre ayarlıdır.
- **Gizlilik (KVKK):** Teklif formundaki e-postalar özel deponuzda (`veri/teklifler.csv`) saklanır.
  Depoyu **herkese açık yapmayın**.
