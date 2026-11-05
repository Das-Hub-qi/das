# Otonom Gelir ve İçerik Sistemi

YouTube içerik üretimini ve alan adlarından (trustneurohub.com.tr, okyanusbilisimtr.com, turizm alan adları)
gelir elde etmeyi **ücretsiz bulut katmanlarında**, kendi kendine öğrenerek yürüten otomasyon sistemi.
Hiçbir ücretli hesap gerektirmez.

> 🧭 **Tüm sistem tek sayfada → [Kontrol Merkezi](https://claude.ai/artifact/JmGazg5W8YwsfdmMX7WeLf)**
> (çalıştırma düğmeleri, tüm bağlantılar, test sonuçları, kurulum ilerlemesi)
>
> 📊 **Canlı durum, eksik kurulum adımları ve son videolar → [DURUM.md](DURUM.md)**
> (her çalıştırmada kendiliğinden güncellenir; telefondan GitHub uygulamasıyla da okunur)

---

## 🚀 3 adımda başla

Hiçbir anahtar eklemeden başlayabilirsin; sistem eksikleri ücretsiz yedeklerle tamamlar.

1. **Beta'yı çalıştır:** GitHub > **Actions > Otonom sistem > Run workflow** → `beta` seç → **Run**.
   Sistem 1 gerçek video + 2 Shorts + site sayfası üretir, YouTube'a **yüklemez**. Bitince
   çalıştırmanın sayfasında en altta **Artifacts**'tan indirip izle.
2. **DURUM.md'yi aç:** neyin kurulu, neyin eksik olduğunu ve her eksiğin nasıl tamamlanacağını gösterir.
   En büyük kalite artışı için önce ücretsiz **Pexels** anahtarını ekle (aşağıda adım B).
3. **Başlat:** aynı yerden `haftalik` çalıştır. Sonrası otomatik: her pazartesi plan ve üretim,
   her gün yükleme ve teklif kontrolü. Bir adım hata verirse GitHub sana e-posta gönderir.

---

## 💰 Maliyet

| Hizmet | Ne için | Ücret |
|---|---|---|
| GitHub Actions | Zamanlayıcı, yapay zekâ, video üretimi | **0 ₺** (özel depoda ayda 2.000 dk; yerel modelle ~300-600 dk kullanılır) |
| Yerel yapay zekâ: Gemma 4 E2B | Senaryo, plan, satış metinleri | **0 ₺** (GitHub sunucusunda çalışır) |
| Edge TTS (yedek: Piper) | Türkçe seslendirme | **0 ₺** |
| Pexels / Pixabay / Openverse | Telifsiz fotoğraflar | **0 ₺** |
| YouTube Data API | Yükleme ve istatistik | **0 ₺** (günlük ücretsiz kota) |
| Cloudflare Pages, Workers, KV, Email Routing | Siteler, teklif formu, link takibi | **0 ₺** |
| *İsteğe bağlı:* Claude Haiku 5.5 | Daha kaliteli Türkçe metin | ≈ 0,01-0,05 $/ay |

Tek gider alan adlarının yıllık yenileme ücreti. Sistem dakika bütçesini kendisi izler; sınıra yaklaşınca
üretimi azaltır, böylece hesap asla ücretliye dönmez.

---

## ⚙️ Nasıl çalışır?

```
Pazartesi 09:17 ─ Laboratuvar ölçer → Öğrenme Mühendisi sistemi ayarlar → niş ve trend analizi →
                  haftalık plan (Thompson) → senaryolar → [yerel modelde: video üretimi] → alan adı metinleri → siteler
Pazartesi 13:37 ─ (Claude kullanılıyorsa) toplu senaryoları alır ve videoları üretir
Her gün   07:07 ─ Kalan yüklemeler, viral kontrol, teklifler, link tıklamaları, site güncellemesi
```

**Tek senaryodan 4 içerik:** 1 uzun video (5-9 dk, bölümlü, altyazılı) + 2 Shorts (büyük altyazılı)
+ alan adının sitesinde SEO uyumlu yazı + başlık/açıklama/etiketler. Uzun videolar Salı/Perşembe/Cumartesi
yayına girer (`gizlilik: "zamanla"` iken; değilse Studio'dan tek tıkla).

**Alan adları:** Her alan adına Cloudflare'de ücretsiz site kurulur; içerik büyüdükçe değeri artar.
Sitede "satılık/kiralık" teklif formu vardır; gelen teklife yanıt taslağı otomatik hazırlanır.
Ortaklık (affiliate) linkleri kendi alan adından kısa link olur (`/git/kurs`), tıklamalar sayılır,
link değişince eski videolar otomatik düzelir.

## ✅ Haftalık 15 dakikalık kontrol

1. **DURUM.md**'ye bak: eksik adım veya uyarı varsa orada yazar.
2. YouTube Studio'da yeni videoları izle, sorun yoksa **Yayınla**. Bitiş ekranı: **Bitiş ekranı > Videodan içe aktar**.
3. Senaryolara göz at: küçük yerel model ara sıra hatalı bilgi yazabilir.
4. Yeni teklif varsa `veri/teklif_taslaklari/` içindeki yanıtı kontrol edip gönder.

**YouTube bağlantısı kurmadıysan:** videoları Artifacts'tan indirip elle yükle, sonra linklerini
[config/elle_yuklenenler.yaml](config/elle_yuklenenler.yaml) dosyasına ekle (DURUM.md hangi kodla
ekleyeceğini gösterir). Böylece öğrenme motoru bu videolardan da öğrenir.

---

## 🔑 Kurulum ayrıntıları (hepsi isteğe bağlı, hepsi ücretsiz)

Anahtarları **GitHub > Settings > Secrets and variables > Actions > New repository secret** bölümüne,
tablodaki adla ekle. Anahtarları asla dosyalara yazma.

### A. Yapay zekâ
Hiçbir şey yapmana gerek yok: anahtar yoksa ücretsiz yerel model kullanılır (ilk çalıştırmada bir kez
indirilir). Daha kaliteli metin için: https://console.anthropic.com → **Billing**'den 5 $ yükle →
**API Keys > Create Key** → `ANTHROPIC_API_KEY`. Sistem anahtarı görünce Claude'a geçer; kredi biterse
kendiliğinden yerel modele döner.

### B. Görseller (önerilir)
- https://www.pexels.com/api → `PEXELS_API_KEY`
- https://pixabay.com/api/docs → `PIXABAY_API_KEY`

Anahtar yoksa anahtarsız Openverse'ten CC0 fotoğraf aranır, o da olmazsa renkli yazı kartı kullanılır.

### C. YouTube
1. https://console.cloud.google.com → yeni proje → **APIs & Services > Library**:
   "YouTube Data API v3" ve "YouTube Analytics API"yi **Enable** et.
2. **Credentials > Create credentials > API key** → `YOUTUBE_API_KEY` (istatistik ve rekabet analizi).
3. **OAuth consent screen**: "External", uygulamayı **"In production"** yap (⚠️ "Testing" modunda bağlantı 7 günde kopar).
4. **Credentials > OAuth client ID > Desktop app** → JSON'u indir, bilgisayarında `client_secret.json`
   adıyla bu klasöre koy ve çalıştır:
   ```
   pip install google-auth-oauthlib
   python araclar/youtube_token_al.py
   ```
   Çıkan `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` değerlerini Secrets'a ekle.
5. Kanalını telefonla doğrula (youtube.com/verify): özel küçük resim için gerekli.
6. ⚠️ Google, denetimden geçmemiş API projelerinin yüklediği videoları **gizli** tutar. Bu yüzden sistem
   "gizli" yükler, sen Studio'dan yayınlarsın. Tam otomatik yayın için ücretsiz **YouTube API Audit**
   formunu doldur; onaydan sonra `config/ayarlar.yaml` > `gizlilik: "zamanla"` yap.

### D. Cloudflare (siteler, teklif formu, link takibi)
1. https://dash.cloudflare.com → ücretsiz hesap → **Add a domain** ile alan adlarını ekle, alan adı
   firmanda nameserver'ları Cloudflare'inkilerle değiştir.
2. **My Profile > API Tokens > Create Token > Custom token** izinleri: *Account – Cloudflare Pages – Edit*,
   *Account – Workers KV Storage – Edit*, *Zone – Zone – Read*, *Zone – DNS – Edit* → `CLOUDFLARE_API_TOKEN`.
3. Sağ menüdeki **Account ID** → `CLOUDFLARE_ACCOUNT_ID`.
4. Gerisi otomatik: teklif deposu kurulur, siteler yüklenir, alan adları bağlanır, DNS kaydı eklenir.
   (Eski bir park kaydı varsa Cloudflare > DNS'ten sil.) İsteğe bağlı: **Email Routing** ile
   `teklif@alanadin` → Gmail; **Web Analytics** token'ını `config/ayarlar.yaml` > `cloudflare`'e yaz.

### E. Kendi bilgilerin
`config/varliklar.yaml`'ı GitHub'da açıp kalem simgesiyle düzenle: `kanal_id` (Studio > Ayarlar > Kanal >
Gelişmiş, "UC..." ile başlar), turizm alan adların (örnek satırlardaki `#` işaretini kaldır), ortaklık
linklerin (`kisa-ad: "https://..."`). Ayar dosyasında yazım hatası yaparsan sistem satır numarasıyla
Türkçe uyarı verir; eksik bıraktığın ayarları varsayılanla tamamlar.

---

## 🧠 Kendi kendine öğrenme

| Katman | Ne yapar? |
|---|---|
| **Thompson örneklemesi** | Niş, başlık stili, video uzunluğu ve yayın saatini başarı dağılımlarından örnek çekerek seçer. Veri azken her şeyi dener, kazanan netleştikçe ona yoğunlaşır, keşfi bırakmaz. |
| **Zaman aşınması** | Eski videoların etkisi 45 günde yarıya iner; izleyici zevki değişirse uyum sağlar. |
| **Yaşa göre düzeltilmiş puan** | Kanalın izlenme-yaş eğrisinden sapmayı ölçer; yeni ve eski videolar adil karşılaştırılır. |
| **Trend momentumu** | Haftadan haftaya yeni çıkan veya yükselen aramaları öne alır. |
| **Çeşitlilik filtresi** | Yayınlanmışa çok benzeyen konuyu eler (artırmak = arttırmak gibi yazım farkları dahil). |
| **A/B başlık testi** | Zayıf videoda alternatif başlığı dener; 7 gün sonra kötüyse eskiye döner. |
| **Viral takip** | 10.000 izlenmeyi geçen videonun devamını öncelikli planlar. |

20 haftalık simülasyonda sistem gizli "en iyi" seçenekleri kendi buldu: en iyi nişin payı %33 → %67,
en iyi başlık stilininki %17 → %50. Öğrenilenler DURUM.md > "Laboratuvar öğrenimi"nde görünür.

### 👷 Öğrenme Mühendisi
Her pazartesi laboratuvardan sonra çalışır ve **sistemin kendisini** geliştirir:

| Görev | Örnek karar |
|---|---|
| Deney evrimi | "1400 kelime %73 olasılıkla en iyi → 1700'ü de dene" · "'nasıl' başlıkları kaybediyor → emekliye ayır, yerine 'hata uyarısı' dene" |
| Uyum hızı | Performans kaydıysa eski verinin etkisini hızlandırır, kararlıysa yavaşlatır |
| Pazar keşfi | En başarılı videoların anahtar kelimelerini yeni arama tohumu yapar |
| Kendini onarma | Metinler yarım kalıyorsa model belleğini, YouTube kotası doluyorsa Shorts sayısını ayarlar |
| Ders çıkarma | En iyi 3 / en zayıf 3 videodan en fazla 5 kural çıkarıp senaryo yazarına ekler |
| Gözcülük | Çözemediği sorunları ve yeni çıkan yerel modelleri GitHub issue yapar; Dependabot paketleri günceller |

Mühendis senin `config/` dosyalarına dokunmaz; öğrendiklerini `veri/ogrenilen_ayarlar.yaml`'a, her kararı
gerekçesiyle `veri/muhendis_gunlugu.md`'ye yazar. Dosyayı silersen fabrika ayarlarına döner; bir ayarı
korumak için `config/ayarlar.yaml > muhendis > kilitli`'ye ekle; yalnızca öneri istersen `otomatik_uygula: false`.

### 🛡️ Sınıra takılınca sistem durmaz

| Sınır / sorun | Sistem ne yapar? |
|---|---|
| Claude kredisi biter, kota veya ağ hatası | Ücretsiz yerel modelle devam eder |
| Toplu yapay zekâ işi 26 saatte bitmez | Senaryoları anlık üretir |
| Yerel model metni kısa / yarım bırakır | Sahneleri tek tek genişletir; yarım kalırsa kısaltıp tekrar dener |
| Edge seslendirme engellenir | İnternetsiz **Piper** Türkçe sesine geçer |
| Görsel anahtarı yok veya sınır doldu | Openverse → yazı kartı |
| YouTube günlük kotası / yükleme sınırı | Kalan videoları ertesi gün kaldığı yerden yükler |
| YouTube bağlantısı bozulur | Üretime devam eder, videoları indirilebilir bırakır, uyarır |
| GitHub dakikası %85'e yaklaşır / %93'e ulaşır | Üretimi azaltır / ay sonuna kadar yalnızca hafif işler |
| Herhangi bir adım hata verir | Diğer adımlar sürer, GitHub e-posta atar, DURUM.md'de görünür |
| Aynı sorun tekrar eder | Mühendis ayarla düzeltir; düzeltemezse issue açar |

---

## 🤖 Yerel model seçimi (test sonuçları, Kasım 2026)

| Model | Bellek (çalışırken) | Hız | Sonuç |
|---|---|---|---|
| **Gemma 4 E2B** | 4,9 GB | 6,8 token/sn | **Seçildi:** akıcı Türkçe, en hızlı, ücretsiz sunucuya (7 GB) sığar |
| Gemma 4 E4B | 8,8 GB | 4,5 token/sn | En akıcı ama ücretsiz sunucuya sığmaz |
| Qwen3.5 4B | ~3 GB | 4,6 token/sn | Belirgin dil bilgisi hataları |

Küçük model uzun metni kısa keser (700 kelime istendi, 177 yazdı); sistem kısa sahneleri tek tek genişletir
(testte 69 → 233 kelime). Testlerde pomodoro süresini yanlış yazdı (doğrusu 25 dakika): senaryolara haftada bir
göz at. Site adresi ve emoji gibi seslendirmeyi bozan şeyler kodla temizlenir. Modeli değiştirmek için
`config/ayarlar.yaml > llm.yerel_*`.

## ⚡ Orijinal plana göre yapılan iyileştirmeler

| Orijinal | Yeni |
|---|---|
| Ücretli yapay zekâ | Ücretsiz yerel model; anahtar varsa Claude, kredi biterse yerel |
| Senaryo, açıklama, makale ayrı ayrı | Tek çağrıda 4 içerik |
| MoviePy | Doğrudan ffmpeg: 5-10 kat hızlı |
| Skor = İzlenme×0,5 + CTR×0,3 + Süre×0,2 | Yüzdelik sıra + yaşa göre düzeltilmiş izlenme (ölçek farkı yok) |
| Sabit 4 haftalık takvim | Her hafta güncel veriyle, Thompson örneklemesiyle plan |
| Google Sheets | Depoda CSV + Markdown raporlar |
| 3 sn boş intro | Doğrudan kanca (isteğe bağlı açılır) |
| Domain parking | Ücretsiz site + teklif formu + yanıt taslağı |
| — | Otomatik bölüm zaman damgaları, altyazı, A/B başlık testi, Öğrenme Mühendisi |

---

## 📁 Dosyalar ve komutlar

| Dosya | Görev |
|---|---|
| `config/ayarlar.yaml` | Genel ayarlar (yapay zekâ, video sayısı, ses, yayın, deneyler, mühendis) |
| `config/varliklar.yaml` | Alan adları, nişler, ortaklık linkleri, kanal |
| `config/elle_yuklenenler.yaml` | Elle yüklediğin videoların linkleri |
| `otonom/m01_envanter.py` … `m12_gelir.py` | Master prompttaki 12 modül |
| `otonom/optimizasyon.py`, `muhendis.py` | Öğrenme motoru ve Öğrenme Mühendisi |
| `otonom/yerel_llm.py`, `butce.py`, `durum_paneli.py` | Yerel model, sınır bütçesi, DURUM.md |
| `otonom/orkestrator.py`, `mikro_site.py`, `cloudflare_kur.py` | Döngüler, siteler, Cloudflare kurulumu |
| `cloudflare/functions/` | Teklif formu ve kısa link fonksiyonları |
| `veri/` | Sistemin hafızası (bkz. [veri/BENIOKU.md](veri/BENIOKU.md)) |
| `MASTER_PROMPT.md` | Sistemin ana talimatı |

Komutlar (Actions'tan veya bilgisayarında `python -m otonom <komut>`):
`beta, haftalik, gunluk, muhendis, durum, cloudflare, envanter, nis, plan, uret, alanadi, site, analiz, teklifler, rapor, maliyet`

Bilgisayarında denemek için:
```
pip install -r requirements.txt          # ayrıca ffmpeg kurulu olmalı
pip install -r requirements-yerel.txt    # ücretsiz yerel model (bir kez derlenir)
python -m otonom haftalik --deneme       # hiçbir servise bağlanmadan uçtan uca test
python -m pytest -q                      # testler
```
Gerçek çalıştırma için `.env.example` dosyasını `.env` adıyla kopyalayıp doldur.

---

## ⚠️ Gerçekçi beklentiler

- **YouTube para kazanma şartı:** 1.000 abone + son 12 ayda 4.000 saat izlenme (veya 90 günde
  10 milyon Shorts izlenmesi). Genelde aylar sürer; garantisi yoktur.
- **"Özgün olmayan içerik" politikası:** YouTube toplu üretilmiş, birbirinin tekrarı yapay zekâ videolarını
  para kazanmadan çıkarabilir. Sistem her videoya özgün bir bakış açısı zorunlu kılar; yine de ara sıra kendi
  sesinle yorum veya deneyim eklemen çok faydalıdır.
- **Alan adı satışı:** Çoğu alan adı uzun süre satılmayabilir; fiyat uydurulmaz, "teklife açık" satılır.
- **Sağlık nişi:** Teşhis/tedavi vaadi yasaktır; senaryo talimatları buna göre ayarlıdır.
- **Gizlilik (KVKK):** Depo **herkese açıksa** (şu an öyle; GitHub dakikası bu sayede sınırsız) teklif
  e-postaları, isimler ve mesajlar depoya **maskeli** yazılır (`a***@g***.com`); tam hali yalnızca özel
  Cloudflare deponda (Cloudflare > KV > TEKLIFLER) kalır. Raporlar ve metrikler yine herkese açıktır; bunu
  istemezsen deponu **Settings > General > Change visibility** ile özel yap (aylık 2.000 dakika sınırına
  sistem kendiliğinden uyar).
