# Bulut oturumu ilerleme kaydı

Son güncelleme: 2026-10-11 (oturum başı)

## Kaynak sürümü
- Depo: erenkaan5a-eng/build-the-builder, dal `claude/lucid-fermat-vxp9u7`, başlangıç commit `a5de72280d0b` (üstünde `f62fc358f7d7`). Çalışma ağacı temizdi.
- `research/builder-version.txt`: `84894192a420329c` = "local fixes of 11 Oct, NOT measured live". Bu kimliğin hesaplama yöntemi depoda yok; birkaç olası hash şeması (builder/*.py, +tests, +skills; LF/CRLF) denenip yeniden üretilemedi. Bu nedenle sürüm içerikle doğrulandı (aşağıda), kimlik değeriyle değil.
- İçerik doğrulaması: deney günlüğünün "11 Ekim" bölümündeki düzeltmeler dosyalarda var: tests/negotiation_harness.py, tests/test_negotiation_regress.py, tests/test_generator_structure.py, build.py `--local-only`, components.py `close_check`/`hardship_go`/`fin_ready`, negotiation.py `rb_pkg` (tam paket onayı), `hardship_seen`.
- Eksik (yalnız yerelde): `results/` (git-ignored) bulutta yok: deney günlüğünün atıf yaptığı ham sonuçlar (results/*.json, transcript'ler, regress-before/after-fix.txt) buradan okunamıyor. Günlükteki sayılar bu nedenle yalnız günlük metni olarak alındı.
- `env.sh` yok (beklenen; sırlar proxy'de).

## Erişim (düşük etkili kontrol, değerler okunmadı)
- Ortam: FREYA_API_KEY ve FREYA_BANK_TEAM_KEY ortamda yok; ANTHROPIC_API_KEY yok; Claude sağlayıcısı host tarafından yönetiliyor.
- Freya `GET /api/v2/workspaces`: başlıksız 200, mevcut freya.py'nin boş `Bearer ` başlığıyla da 200 (proxy başlığı ekliyor/eziyor). 1 çalışma alanı.
- Banka `GET /v1/practice/ledger/<olmayan id>`: başlıksız 404 "unknown customer_id for this team key" → proxy takım anahtarını ekliyor, anahtar tanındı.
- Engel: `tools/score.py` `os.environ["FREYA_BANK_TEAM_KEY"]` → anahtar ortamda yoksa KeyError (run_cases ve --practice durur).
- Düzeltme (kit dosyalarına dokunmadan): `tools/cloud_proxy.py` + `tools/run_cases_cloud.py`; `builder/common.py` aynı yamayı uygular. Yalnız `FREYA_AUTH_VIA_PROXY=1` iken ve anahtar ortamda yoksa başlık proxy'ye bırakılır. Değişken yokken davranış aynı (KeyError yeniden üretildi). Trace'e yalnız "set/absent" yazılır.
- Agent SDK: builder'ın kendi `spec_extract._ask` yolu ile 1 küçük çağrı (claude-opus-5-5, "OK", 12 s, cache_create 15190 tok, out 4). Çalışıyor. Bu kullanım bu bulut oturumunun bağlı olduğu Claude aboneliğinden düşer; kotaya etkisi buradan ölçülemiyor.

## Yerel testler (bulutta yeniden koşuldu)
- test_negotiation: 53 kontrol, 0 hata (günlükteki "54/54": dosyada 53 `check(` çağrısı + 1 `def check` var; sayım farkı, kapsam farkı değil).
- test_negotiation_regress 24/24, test_date_tool 14/14, test_generator_structure 18/18.

## Kullanım sayacı (üst sınırlar: build 4, simüle koşu 30, chat 4)
| tür | kullanılan | not |
|---|---|---|
| builder run (uçtan uca / local-only) | 0 | |
| simüle müşteri koşusu | 0 | |
| platform chat oturumu | 0 | |
| ek model çağrısı | 1 | SDK erişim kontrolü |
| Freya okuma | 2 | workspaces GET (erişim kontrolü) |
| banka okuma | 2 | olmayan ledger GET (erişim kontrolü) |

## Adaylar
(henüz yok bu oturumda)

## Ölçümler
(henüz yok)

## Açıklar
- Kaynak kimliği 84894192a420329c yeniden üretilemiyor (yöntem belgelenmemiş).

## Sonraki adım
A/B notlarını tablo halinde değerlendirmek; yerel özellikleri doğrulamak.
