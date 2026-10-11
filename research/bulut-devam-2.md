# Bulut devamı 2 — local-hardening 888bd30'dan (11 Ekim 2026)

Bu dosya yalnız bu devamın kod değişikliklerini ve yeni adaylarını kaydeder. Eski adayların skorları (n6; cl-a v2 /
cl-ab v2 ile 27/29; loc-a v2 / loc-ab v1 için ölçüm yok) buradaki adaylara atfedilmez.

## Başlangıç durumu (doğrulandı)
- `origin/local-hardening` = 888bd30; 881ea3a'nın (önceki bulut oturumunun son commit'i) torunu. Görev dalı
  `claude/lucid-fermat-vxp9u7` 881ea3a'daydı, ilerlememişti → 888bd30'a fast-forward (çakışma yok). `local-hardening`'e push yapılmadı.
- 888bd30'un temiz kopyasında yerel testler (geçici worktree): api_binding 6, date_tool 14, generator_structure 26, identity 104, negotiation 54, negotiation_regress 48, support 15 — 0 hata. (research/local-evidence/a15-tests-on-888bd30.txt ise yeni A15 testlerinin o koddaki sonucudur: 6 FAIL.)
- Yerel oturumun düzeltmesi kabul edildi: cl-a v2 / cl-ab v2 ham dosyaları **27/29** veriyor (benim önceki "26/29" satırım hatalıydı).
- loc-a v2 (a6aaac5f83cc5ac4) ve loc-ab v1 (a906cc937ea351fe): release kontrolleri platform 5xx yüzünden koşulamamış; 15:33 yeniden kontrolünde "no verify call" FAIL'i incelenmeyi bekliyordu.

## Değişiklikler
| commit | değişiklik | kanıt |
|---|---|---|
| a147224 | A15: araya cevap girince kimlik ret sayacı artık sıfırlanmıyor (8ccf94e'deki sıfırlama kaldırıldı). Hâlâ: mesaj başına en fazla bir ret; cevapla birlikte gelen soru sayılmaz; açıklama bir kez | tests/test_identity.py I11e/f/h/i; 888bd30 kodunda 6 kontrol FAIL (research/local-evidence/a15-tests-on-888bd30.txt) |
| 6bb6719 | `builder/behavior.py`: motorun yürüttüğü banka çağrıları (pre_actions) Freya olaylarında `api_call` adıyla ve `args.url` ile geliyor; operasyon artık URL'nin son yol parçasından okunuyor, sonuçlar kendi çağrısıyla eşleşiyor. `eval/analyze.py`, `eval/chat_probe.py` aynı adlandırmayı kullanıyor | gerçek çağrı olayları (tests/fixtures/chat-events-engine-run.json, C3 çağrısı, başlıklar/kod ayıklandı): eski ayrıştırıcı get_account/create_promise/close_call'ı `api_call` görüyordu → "doğrulamadan önce hesap/yazma çağrısı yok" kontrolü motor çağrılarını hiç göremiyordu (boş geçiş); "verify call yok" FAIL'i yanlıştı. tests/test_behavior_events.py E1–E7 |
| 86f7cbe | release practice kontrolü cevapları kit personası gibi söylüyor (doğum tarihi kelimeyle) | loc-ab v2 build içi practice: ham "1991-01-08" → model gün 19 / ay 91 diye böldü, 0 verify (chat 8669ea77…). Ajan değişmedi; aynı yayın yeniden kontrol edildi |
| (bu commit) | `eval/recheck_release.py` build ile aynı sınırlı 5xx tekrarını kullanıyor | 13:42 yeniden kontrolü 502 ile düşmüştü |

## Yeni adaylar (policy yeniden kullanımı, model çağrısı yok; geliştirme amaçlı `--reuse-policy`)
| aday | kaynak commit | policy | workflow / agent | sürüm | test = export hash | sürüm kontrolü |
|---|---|---|---|---|---|---|
| loc-a v3 | 6bb6719 | candidates/loc-a/20261011-134621/policy.json (yerel build 1, Opus; LF sha256 94052fc3…, Windows CRLF 4865c23c… = aynı içerik) | 23150a3a-fead-4c51-9ad2-2c142b0837f1 / 652ad608-5ecc-44fd-bb7a-b09a271c2ae1 | 3 | 1b567c6fe1f24904 | build içinde **PASSED**: yapısal 4/4 (motor verify çağrısı görüldü), practice PUB-06 4/4 (iki 502 sonrası sınırlı tekrarla) |
| loc-ab v2 | 6bb6719 | candidates/loc-ab/20261011-150232/policy.json (yerel build 2; girdi hash'i kayıtla eşleşiyor) | cc2873a9-c391-44c3-acc8-e8c35624298c / 41b6d98f-2c8e-4ea6-8139-1901d21f32a1 | 2 | e1d03845876722e3 | build içinde FAILED (practice: ham ISO tarih, yukarıda); aynı sürüm yeniden kontrol 13:44 **PASSED** (yapısal 4/4, practice PUB-13 4/4) |
- Adaylar A15 ve behavior düzeltmelerinden sonra üretildi; 86f7cbe ve sonrası yalnız kontrol araçlarını değiştirir (ajan içeriği aynı).
- Uçtan uca (model çağrılı) build yapılmadı. Bu iki yayın, finaldeki tek çıkarımlı koşunun yerine geçmez.

## Hedefli regresyon (tek tekrar; pass^3 değildir)
(çalışıyor)

## Kalan açıklar
- Kimlik çıkarımında sayı biçimli tarih: model ISO dizgeyi yanlış bölebildi; gerçek arayanlar bunu nadiren söyler ama "numbers only" tarihler (A11) için motor modelin parça bölmesine bağlı.
- Dondurulmuş özel set (CF-*) ve standart public kapısı (A ×3, B ×3) bu adaylarda koşulmadı.
