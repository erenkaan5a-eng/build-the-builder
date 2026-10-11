# Bulut oturumu ilerleme kaydı

Son güncelleme: 2026-10-11 ~02:00 UTC

## Kaynak sürümü
- Depo: erenkaan5a-eng/build-the-builder, dal `claude/lucid-fermat-vxp9u7`. Başlangıç commit `a5de722` (builder ağacı `a4c98a04ab393525`), çalışma ağacı temizdi.
- `research/builder-version.txt`: `84894192a420329c` = "local fixes of 11 Oct, NOT measured live". Hesaplama yöntemi depoda yok; birkaç hash şeması denenip yeniden üretilemedi. Sürüm içerikle doğrulandı: harness, regresyon/yapı testleri, `--local-only`, close_check, hardship_go, fin_ready, rb_pkg mevcut → beklenen 11 Ekim yerel sürümü.
- Bundan sonra kimlik: commit SHA + `git rev-parse <sha>:builder` (bkz. research/teslim-duzeni.md).
- Bulutta yok (yalnız yerelde, git-ignored): `results/` (ham n6 sonuçları, transcript'ler, regress-before/after-fix.txt). Günlükteki sayılar yalnız günlük metni olarak alındı.

## Erişim (değerler okunmadı/yazdırılmadı)
- FREYA_API_KEY, FREYA_BANK_TEAM_KEY, ANTHROPIC_API_KEY ortamda yok; Claude sağlayıcısı host tarafından yönetiliyor.
- Freya `GET /api/v2/workspaces`: başlıksız ve boş `Bearer ` ile 200 (proxy ekliyor). Banka: olmayan müşteri ledger'ı → 404 "unknown customer_id for this team key" (anahtar tanındı).
- Engel: `tools/score.py` anahtar yoksa KeyError. Çözüm: opt-in `FREYA_AUTH_VIA_PROXY=1` (tools/cloud_proxy.py, tools/run_cases_cloud.py, builder/common.py); kit dosyaları değişmedi; değişken yokken davranış aynı (KeyError yeniden üretildi).
- Agent SDK: builder'ın kendi yolu ile 1 küçük çağrı (Opus, "OK", 12 s). Çalışıyor. Kullanım bu oturumun Claude aboneliğinden düşer; kota etkisi ölçülemiyor.

## Tamamlanan işler
1. Yerel testler buluta gelen sürümde: müzakere 53 kontrol (günlükteki 54 = `check(` sayımı, `def` dahil), regresyon 24, tarih 14, yapı 18 → 0 hata.
2. A1–47/B1–11/Closing tablosu: research/ab-kural-tablosu.md.
3. Motor düzeltmeleri (yerel test; eski motorda 8 yeni test başarısız, yenide geçiyor — research/cloud-evidence/):
   - A32 zorluk + gönüllü tarih/tutar aynı mesajda: öneri yutulmuyor (offer_named ile yönlendirme), empati+destek teklifi tek sahip (kod), öneri destek teklifi cevaplanınca işleniyor; answer alanı zorluk turunda düşürülüyor (eski kodda çift empati üretiyordu).
   - "İşimi kaybettim, ödeyemem" tek mesajda: eski kod destek teklifini söyleyip aynı turda kapatıyordu; şimdi teklif açık kalıyor.
   - Zorluk sonrası ikna yok (ürün bayrağı `hs`); `all` kapsamlı destek reddi bekleyen ürünlere ulaşıyor (B'de döngü riski).
   - rec_next `blocked` → `neg_flag` temizleniyor (transfer sonrası yönlendirme döngüsü riski).
   - A45 sayacı policy'den (`stop_statements_to_close`, yoksa eski davranış). Yeni adaylarda iki brief'ten de 2 çıkarıldı.
   - Kimlik aşamasındaki zorluk: identity extraction + `hardship_early` (risk: yanlış pozitif; canlı izleniyor).
4. Manifest'e destek sınırı (`support_boundary`: kod / model / kodla desteklenmeyen).
5. Release davranış kontrolüne yalnız platform 5xx için bütçe içinde sınırlı tekrar (30/90/180 s). `eval/recheck_release.py`: aynı yayınlanmış sürümde (hash eşitliği şartıyla) kontrolleri yeniden koşar.
6. API yeniden adlandırma deneyinin deterministik yarısı: tests/test_api_binding.py 6/6 (çıkarım adımı DEĞİL).
7. Memo deneyi beklenen tarihi bağımsız hesaplandı: 2026-10-21.

## Adaylar
| slot | aday klasörü | workflow / agent | sürüm | içerik hash | kaynak | build | release |
|---|---|---|---|---|---|---|---|
| cl-a | candidates/cl-a/20261011-014815 | 0800b57a-585f-4324-9c6d-d66e40260a37 / 91e04e98-0e9e-4bd0-b87d-efdb923d62a8 | 1 | b2601999470a02c7 | 59e0ba2 (builder fc7d2e36…) | 64 s, 1 Opus | FAILED: chat 503 (platform) |
| cl-ab | candidates/cl-ab/20261011-015018 | 06d2cae1-ed27-4d3a-8ac1-dc664cb91cca / f97de421-84ba-4675-b150-6569b61d9eb5 | 1 | 3390a84c8ad3f3ee | 59e0ba2 | 128 s, 1 Opus | FAILED: chat 502 (platform) |
- Karar değerleri n6 adaylarıyla aynı (compare_builds); yapısal farklar yalnız 11 Ekim + bu oturumun kasıtlı değişiklikleri.
- Eski ölçülmüş adaylar dokunulmadı: cmp-a v8, cmp-ab v7 (slotlar ayrı).

## Platform durumu
- 01:49–01:53 UTC: chat API 503 "Internal server error" / 502 "upstream request failed"; daha önce çalışan cmp-a v8 için de aynı → yeni koddan bağımsız, şüpheli platform hatası. Proxy relay hatası yok. Simülasyon aynı ajan modelini kullandığı için başlatılmadı.

## Kullanım sayacı (üst sınırlar: build 4, simüle koşu 30, platform chat 4)
| tür | kullanılan | not |
|---|---|---|
| builder run | 2 | cl-a, cl-ab (her biri 1 Opus çağrısı) |
| simüle müşteri koşusu | 0 | |
| platform chat oturumu (kurulan) | 0 | |
| chat denemesi (5xx, oturum kurulamadı) | 5 | build içi 2, recheck 1, yoklama 2 |
| ek model çağrısı | 1 | SDK erişim kontrolü |
| Freya dry-run (doğrulama, kayıt yok) | 2 | yeniden üretilen A ve A+B |

## Açıklar
- Kaynak kimliği 84894192a420329c yeniden üretilemiyor.
- Yeni adayların davranış kontrolleri ve canlı ölçümü platform chat/model hatası nedeniyle bekliyor.

## Sonraki adım
Chat yeniden çalışınca: recheck (cl-a, cl-ab) → 3 betikli chat kontrolü → 20 koşuluk hedefli ölçüm.
