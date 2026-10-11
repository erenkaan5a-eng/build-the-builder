# Yerel oturum ölçümleri (11 Ekim 2026)

Bu dosya yalnız bu oturumun adaylarına ait canlı sonuçları içerir. Eski adayların (cl-a v2, cl-ab v2, n6) skorları buraya taşınmaz.

## Adaylar
| aday | builder commit (ağaç) | policy kaynağı | workflow / agent | yayın sürümü | test = export hash | sürüm kontrolleri |
|---|---|---|---|---|---|---|
| loc-a v2 | 09ccb57 (`1d689a7a…`) | build 1 çıkarımı (13:46, Opus, `candidates/loc-a/20261011-134621/policy.json`), 1f'de yeniden kullanıldı | 23150a3a… / 652ad608… | 2 | a6aaac5f83cc5ac4 | yapısal + practice PUB-06: chat API 5xx/500 nedeniyle koşulamadı (eski cl-a da aynı 500'ü aldı) |
| loc-ab v1 | 09ccb57 (`1d689a7a…`) | build 2 çıkarımı (14:57, Opus) + yapısal yeniden kontrol (15:02, küçük Opus çağrısı), `candidates/loc-ab/20261011-150232/policy.json` | cc2873a9… / 41b6d98f… | 1 | a906cc937ea351fe | aynı nedenle koşulamadı |

- Yayınlanan içerik yerel üretimle karşılaştırıldı: platform hiçbir alanı silmedi/değiştirmedi, yalnız varsayılan alanlar ekledi (kimlik düğümleri, motor düğümündeki post-hook, transfer düğümünün TTS satırı korunmuş).
- "build 1/2" = uçtan uca çıkarım çağrısı yapan build. "1b–1f", "2b–2c" = aynı policy ile yayın/yerel üretim (model çağrısı yok; 2b'de yalnız küçük yeniden kontrol çağrısı). Platform kesintisi: `research/platform-olay-1011.md`.

## Canlı koşular
(simülasyon henüz başlatılmadı; kullanılan: 0/60 koşu)

## Sürüm yeniden kontrolü — loc-a v2 (15:33, `eval/recheck_release.py`, canlı hash = export hash)
- PASS açılış cümlesi; PASS kimlik aşamasına giriş; PASS doğrulamadan önce hesap/yazma çağrısı yok.
- FAIL "first security answer reaches verify_identity": düğüm yolu `identity > id_send > id_verify > id_result > id_send > id_verify > id_result > id_consume > id_relay` → motor düğümü verify'ı çağırdı (sahte müşteri: HTTP hatası, bir tekrar, sonra 'kontrol edilemedi'), ama kontrolün olay ayrıştırıcısı bunu `verify_identity` çağrısı olarak görmedi. Muhtemelen kontrol aracının motor-düğümü olay adını okuma biçimi; **doğrulanmadı** — sıradaki iş: chat olaylarındaki fonksiyon adını incelemek, gerekirse `builder/behavior.py`'yi düzeltmek.
- practice PUB-06: chat API 504 ile kesildi; koşulmadı.
