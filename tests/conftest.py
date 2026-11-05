import os
import tempfile

# Testler gerçek veri klasörüne asla yazmasın: içe aktarmadan ÖNCE ayarlanmalı.
os.environ.setdefault("OTONOM_CALISMA", tempfile.mkdtemp(prefix="otonom-test-"))
for anahtar in ("ANTHROPIC_API_KEY", "YOUTUBE_API_KEY", "YT_REFRESH_TOKEN", "PEXELS_API_KEY",
                "PIXABAY_API_KEY", "CLOUDFLARE_API_TOKEN", "CF_KV_NAMESPACE_ID"):
    os.environ.pop(anahtar, None)
