"""YouTube yetki anahtarı (refresh token) alma — KENDİ BİLGİSAYARINIZDA BİR KEZ çalıştırın.

Ön hazırlık (README'deki adımlar):
  1. Google Cloud Console'da proje açın, "YouTube Data API v3" ve "YouTube Analytics API"yi etkinleştirin.
  2. OAuth izin ekranı: Kullanıcı türü "Harici", yayın durumunu "Üretimde" (In production) yapın.
     ("Test" modunda bırakırsanız anahtar 7 günde geçersiz olur!)
  3. Kimlik bilgisi oluşturun: OAuth istemci kimliği -> "Masaüstü uygulaması".
     JSON dosyasını indirip bu klasöre client_secret.json adıyla koyun.

Çalıştırma:
  pip install google-auth-oauthlib
  python araclar/youtube_token_al.py
Tarayıcı açılır, YouTube kanalınızın bağlı olduğu Google hesabıyla izin verin.
Ekrana çıkan 3 değeri GitHub > Settings > Secrets and variables > Actions'a ekleyin.
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

IZINLER = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",          # altyazı yükleme
    "https://www.googleapis.com/auth/yt-analytics.readonly",       # izlenme süresi
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",  # reklam geliri
]

dosya = Path(sys.argv[1] if len(sys.argv) > 1 else "client_secret.json")
if not dosya.exists():
    sys.exit(f"{dosya} bulunamadı. Google Cloud'dan indirdiğiniz JSON dosyasının yolunu verin.")

akis = InstalledAppFlow.from_client_secrets_file(str(dosya), IZINLER)
kimlik = akis.run_local_server(port=0, prompt="consent", access_type="offline")
istemci = json.loads(dosya.read_text())["installed"]
print("\nAşağıdaki 3 değeri GitHub Secrets'a ekleyin:\n")
print(f"YT_CLIENT_ID      = {istemci['client_id']}")
print(f"YT_CLIENT_SECRET  = {istemci['client_secret']}")
print(f"YT_REFRESH_TOKEN  = {kimlik.refresh_token}")
print("\nBu değerleri kimseyle paylaşmayın. client_secret.json dosyasını depoya eklemeyin.")
