# Bulut oturumu ilerleme kaydı

Son güncelleme: 2026-10-11 ~03:00 UTC (oturum sonu)

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
8. Platform çökmesi (chat C2 ile bulundu): `global` üretilen kodda platformda NameError → düzeltildi (c8de7c9); test düzeneği kodu platform gibi fonksiyon içinde çalıştırıyor; lint `global/nonlocal` reddediyor.
9. Hardship tüm açık ürünleri kapsıyor, anlaşılmış ürün korunuyor (23f0227); read-back'te kırpılan ürün notu ayrı cümle (C3'te görüldü).
10. Kimlik aşaması istemi: parçalı cevap birleştirme, banka kanıtı olmadan "failed" yok (503d996) — ÖLÇÜLMEDİ.
11. Teslim düzeni ve yerel aktarma: research/teslim-duzeni.md; ayrıntılı kanıt: research/cloud-final-report.md.

## Adaylar
| slot / sürüm | aday klasörü | workflow / agent | içerik hash | kaynak (builder ağacı) | build | release | durum |
|---|---|---|---|---|---|---|---|
| cl-a v1 | candidates/cl-a/20261011-014815 | 0800b57a-585f-4324-9c6d-d66e40260a37 / 91e04e98-0e9e-4bd0-b87d-efdb923d62a8 | b2601999470a02c7 | 59e0ba2 (fc7d2e36…) | 64 s, 1 Opus | build içinde FAILED (chat 503); recheck 02:10 PASSED | **GEÇERSİZ**: motorun zorluk yolu platformda çöküyor (chat C2) |
| cl-ab v1 | candidates/cl-ab/20261011-015018 | 06d2cae1-ed27-4d3a-8ac1-dc664cb91cca / f97de421-84ba-4675-b150-6569b61d9eb5 | 3390a84c8ad3f3ee | 59e0ba2 | 128 s, 1 Opus | build içinde FAILED (chat 502); recheck PASSED | **GEÇERSİZ** (aynı hata); C3 kanıtı bu sürümden |
| cl-a v2 | candidates/cl-a/20261011-021737 | aynı workflow / agent | 233c8dfe1a7d9d91 | c8de7c9 (c2d52b8c…) | 113 s, 1 Opus | PASSED (yapısal 4/4, practice PUB-05 4/4) | ölçülen A adayı |
| cl-ab v2 | candidates/cl-ab/20261011-021934 | aynı workflow / agent | 8abfb3c856c81f25 | c8de7c9 | 112 s, 1 Opus | PASSED (yapısal 4/4, practice PUB-13 4/4) | ölçülen B adayı |
- Karar değerleri n6 ve v1/v2 arasında aynı (compare_builds; yalnız ifade ve extra_rules sınıf sayıları). `stop_statements_to_close`=2 dört çıkarımda da.
- Eski ölçülmüş adaylar dokunulmadı: cmp-a v8, cmp-ab v7.
- A+B girdisi: `{ cat briefs/brief-a.md; echo; cat briefs/brief-b.md; } > out/brief-ab.md` (sha256 0379260ced21a0a4…).

## Platform kontrolleri (chat; betikli müşteri, gerçek practice oturumu + ledger)
| kontrol | aday | sonuç | kanıt |
|---|---|---|---|
| yoklama 02:09 | cl-a v1 | açılış cümlesi 9,6 s | — |
| C3 kısmi → tam onay (PUB-13) | cl-ab v1 | "Yes, for the credit card" kayıt AÇMADI, yalnız "Do you confirm?"; "Yes, I confirm both" → ürün başına 2 kayıt: kart 300/30 Eki, kredi 900/23 Eki, close promise. 8. turda chat geçidi 504 (uzun kayıt zinciri; sunucu tarafında tamamlandı). Biçim kusuru: kırpılan ürün notu ile tarih arasında nokta yok → düzeltildi (R G12) | research/cloud-runs/chat-c3-partial-confirm.json |
| C2 zorluk + "Cuma 300" (PUB-05) | cl-a v1 | `offer_named` yönlendirmesi doğru çalıştı (model [hardship, proposes] gönderdi) ama motor her turda hata cümlesine düştü: `global hardship_said` platformda NameError. Ledger: promise yok, close yok | research/cloud-runs/chat-c2-hardship-own-offer.json; research/cloud-evidence/regress-platform-exec-on-cl-a-engine.txt |
| C2 ilk deneme | cl-a v1 | 502 (oturum ortasında) | — |
- Kök neden: yerel testler kodu düz `exec()` ile koşuyordu; platform fonksiyon içinde çalıştırıyor. Düzeltme c8de7c9: değiştirilebilir sözlük; test düzeneği platform gibi fonksiyon içinde; lint `global/nonlocal` ve fonksiyon içinde derlenmeyen kodu reddediyor (v1 workflow'larını reddediyor).
- C2'nin düzeltilmiş sürümde platformda yeniden denenmesi chat bütçesi bittiği için chat ile yapılamadı; yerel platform-benzeri testler (R G1–G2) ve simülasyon varyasyonu (experiments/variations/) ile ölçülecek.
- Platform durumu: 01:49–01:53 UTC chat 503/502 (eski cmp-a v8 dahil) → şüpheli platform hatası; 02:09'dan itibaren çalışıyor, aralıklı 502/504 devam ediyor.

## Ölçümler (simüle müşteri; run_cases skorlayıcısı: ledger + judge)
| aday | vaka | koşu | geçen | not |
|---|---|---|---|---|
| cl-a v2 | PUB-05 × 3 | 3 | 3 | zorluk yönlendirmesi doğru zamanda; 1 koşuda model kendi metniyle "Would you like to make a payment…?" ekledi (judge kabul etti — risk) |
| cl-a v2 | PUB-06 × 3 | 3 | 3 | |
| cl-a v2 | PUB-10 × 3 | 3 | 3 | ilk create_promise hatası + tek tekrar, tek promise |
| cl-a v2 | PUB-04 × 1 | 1 | 1 | robot cevabı + deadline 23 Eki |
| cl-a v2 | PUB-08 × 1 | 1 | 1 | |
| cl-ab v2 | PUB-11 × 3 | 3 | 3 | |
| cl-ab v2 | PUB-12 × 3 | 3 | 3 | 1 promise + 2 refused not |
| cl-ab v2 | PUB-13 × 3 | 3 | 3 | kart 30 Eki, kredi 23 Eki |
| cl-a v2 | varyasyon zorluk + "Cuma 300" × 3 | 3 | 2 | kalan koşuda simüle müşteri 3 mesajı yarım gönderdi, teklifi hiç söylemedi |
| cl-a v2 | PUB-06 pieces | 2 | 1 | ilk koşu: kimlikte parçalar birleştirilmedi, banka kanıtsız `failed` (model) |
| cl-a v2 | PUB-10 in_words | 1 | 1 | |
| cl-ab v2 | PUB-13 corrects | 1 | 1 | |
| cl-ab v2 | PUB-12 asks_back | 1 | 1 | |
| cl-ab v2 | PUB-11 talkative | 1 | 1 | |
- İlk paket (planlanan 20 koşu): 20/20. Toplam 29 koşu, 26 geçti. pass^3 yalnız 3 tekrarlı satırlarda: A'da 3/3 vaka (PUB-05/06/10), B'de 3/3 vaka.
- Simülasyon kimlikleri: research/cloud-runs/*.json (`simulation_id`, `call_id`, `customer_id`).
- Gecikme: en yavaş tur medyanı 3–24 s; birkaç koşuda "yavaş model" uyarısı; kapatan müşteri 0.

## Kullanım sayacı (üst sınırlar: build 4, simüle koşu 30, platform chat 4)
| tür | kullanılan | not |
|---|---|---|
| builder run (uçtan uca) | 4 / 4 | cl-a v1, cl-ab v1, cl-a v2, cl-ab v2 (her biri 1 Opus çağrısı) |
| simüle müşteri koşusu | 29 / 30 | 13 simülasyon çalıştırması; 1 koşu yedekte bırakıldı |
| platform chat oturumu | 4 / 4 | yoklama 02:09, C2 1. deneme (502), C3, C2 |
| release kontrol chat'leri | build içi 2 başarısız (503/502) + recheck 4 + v2 build içi 4 | release sürecinin parçası |
| chat yoklaması (5xx, oturum kurulamadı) | 2 | 01:50 cmp-a 503, 01:53 cl-a 502 |
| Opus çağrısı | 5 | 4 çıkarım + 1 SDK erişim kontrolü |
| Freya dry-run (kayıtsız doğrulama) | 4 | |
| Freya workflow | 2 yeni (cl-a, cl-ab), her biri 2 sürüm | eski slotlar dokunulmadı |
- Ölçülemeyen: Claude abonelik kotası yüzdesi; Freya kredi/bakiye değişimi (bakiye uç noktası kullanılmadı). "0" değil, "ölçülmedi".

## Açıklar
- Kaynak kimliği 84894192a420329c yeniden üretilemiyor (içerikle doğrulandı).
- Memo deneyi ve API çıkarım deneyi çalıştırılmadı (build bütçesi; ayrıntı cloud-final-report.md §8).
- Kimlik istemi düzeltmesi (503d996) ölçülmedi.
- Kalan riskler: destek teklifine cevap turunda modelin kendi metni; yarım kalan müşteri cümlesi; kimlik/üçüncü kişi/callback/insan isteği sayaçları modelde.

## Sonraki adım (tek en değerli)
Mevcut kodla (503d996) A için bir build + `--style pieces` ile kimlik ağırlıklı kısa ölçüm (PUB-06, PUB-12, PUB-03 × 3): kimlik istemi düzeltmesini doğrula ya da geri al. Ardından memo deneyi.
