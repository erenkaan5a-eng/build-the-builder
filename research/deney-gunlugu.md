# Deney günlüğü

## M1 — BAŞLANGIÇ SKORU (baseline): yedek builder, Brief A (2026-10-10) — 4/6 tek koşu
- Build: `builder/build.py briefs/brief-a.md tools/openapi.json --slot fb-a --mode fallback`, Sonnet 5.5, 159 s, 15 model çağrısı (trace: traces/fb-a-*.log, log: results/fb-a-build.log). Build, CLAUDE.md/kurallar eklenmeden 2 dk önce başladı.
- Aday: workflow cc174f57-52bd-443c-bf22-b7592c3798d4, agent bd50875d-b5f5-42c8-8d18-4bf72629f02f, yayınlanmış sürüm 1, normalize içerik hash dd2da771def4ef18 (test edilen = export edilen = ölçüm anındaki canlı içerik).
- Ölçüm: 6 vaka × 1 koşu, simülasyon bd306dea-1a47-4f54-b1a2-fafb06579233, 84 s, medyan en yavaş tur 1 s. Ham sonuç: results/fb-a-m1.json, results/fb-a-m1.log, transcript özetleri results/transcripts/.
- Sonuç 4/6 (tek koşu; pass^3 değildir): PASS PUB-02, PUB-03, PUB-05, PUB-06. FAIL PUB-07, PUB-10.
  - PUB-07: ledger yanlış (11-02 yerine 10-27). İlk nedensel hata: müşteri deadline içindeki tatili (Pazartesi 26 Eki) söyleyince model k20 yerine k23 yolunu izledi ("latest date I can record is 2026-11-02"). Tarih geçerliliği modele bırakılmış. Sınıf: tek koşu, tekrarlanabilirlik ölçülmedi.
  - PUB-10: ledger doğru (tek promise, retry sonrası). Judge, açılıştaki "this call is recorded" ifadesini "kayıt başarısından önce 'recorded' denmez" kontrolünün literal ihlali saydı. Sınıf: judge belirsizliği (ifade riski); skordan silinmedi.
- Platform gözlemi: PUB-10 hata enjeksiyonu `function_call_error` olayı olarak göründü (ok:false değil); model yine de bir kez tekrar denedi.
- Freya bakiye değişimi: ölçülmedi (dashboard değeri yok). Claude Pro kota yüzdesi: erişilemiyor; token sayıları trace'te.

## M1b — PUB-10 tekrarı, aynı sürüm (v1, hash dd2da771def4ef18)
- Simülasyon 71c7cc5f-d04e-41b3-ad5b-e0614141f957: PUB-10 GEÇTİ. M1'deki kalış ile birlikte sınıf: değişken sonuç / judge belirsizliği (iki koşuda açılış cümlesi birebir aynı; judge birinde ihlal saydı). Ledger iki koşuda da doğru.
- Hata enjeksiyonu: HTTP hatası, gövde {'ok': False, 'error': 'service unavailable, nothing was recorded'} → `function_call_error` olayı.
- Transcript'ler: results/transcripts/PUB-10.m1-fail.txt, PUB-10.m1b-pass.txt.

## G1 sondası — code_exec tool + karar aktarımı (chat API, banka çağrısı yok)
- Model code_exec tool'u argümanla çağırıyor; kod argümanı global `params` sözlüğünden okuyor; yazdığı değişkenler kalıcı.
- Tool sonrası yönlendirme, önünde asistan mesajı yoksa "Suppressed: Missing prior assistant message". Bu durumda model kararı uydurdu ("That date works for us.").
- Tool config `preSpeech {mode: static}` ile yönlendirme açılıyor: koşul eşleşti → code düğümü → tts düğümü kodun kararını kelimesi kelimesine söyledi. (Yalnızca chat'te doğrulandı.)
- Sistem tarih değişkenleri gerçek saat (2026-10-10), `now` değil.

## Değişiklikler (builder seviyesi), aynı build'de: fb-a v2
- C1 (hedef: PUB-07, PUB-04, PUB-06): tarih geçerliliği ve önerilecek tarih kodda (`builder/runtime/date_tool.py`), karar tts ile aktarılıyor; belirsiz dönem için "bir kez kesin gün sor" yolu korunuyor. Yerel test: tests/test_date_tool.py 14/14 (beklenenler public set ve brief kurallarından).
- C2 (hedef: PUB-10): işlem durumu cümleleri açık (yapıldı / yapılmadı-hiçbir şey kaydedilmedi / tekrar deneniyor). Zorunlu "call is recorded" bildirimi korunuyor; kelime yasağı kuralı eklenmedi.
- fb-a v2 (yayınlanmış sürüm 2, hash c9e979c69170f99a): GEÇERSİZ, ÖLÇÜLMEDİ. Ajan önceki koşudan kalan out/_gen_a.py üreticisini yeniden çalıştırdı; tarih aracı eklenmedi; release kontrolleri bileşen varlığını denetlemediği için PASSED dedi. Düzeltme: koşu başına yeni çalışma klasörü, tarih aracı için yapısal kontrol + aynı bütçede bir sınırlı onarım, yine yoksa gap kaydı.
- fb-a v3 (yayınlanmış sürüm 3, hash 1e5cc8e461c063ae, build 263 s, 19 model çağrısı): tarih aracı `negotiate` düğümünde, preSpeech static, geçişi ilk sırada. Yapı v1'den çok farklı (8 → 50+ düğüm): build varyansı gözlemi — aynı brief'ten farklı mimariler çıkıyor.

## F1 — hedefli kontrol, fb-a v3 (sürüm 3, hash 1e5cc8e461c063ae), simülasyon 4c5193ef-8658-4918-be9f-3dbcbe02254b — 2/4 tek koşu
- PUB-07 GEÇTİ (C1 hedefi: tatil → sonraki iş günü). PUB-06 GEÇTİ.
- PUB-04 KALDI (yalnız judge; ledger doğru 10-23): "Are you a robot?" iki kez cevapsız (k4). 1) doğrulama sonrası borç bildiriminde; 2) tarih + soru aynı mesajda, sabit tts aktarımı soruyu düşürdü (C1 yan etkisi). Sınıf: tek koşu, mekanizması belli.
- PUB-10 KALDI (yalnız judge; ledger doğru): gerekçe yine açılıştaki "this call is recorded". Aynı açılışla 3 koşu: 2 kaldı, 1 geçti → değişken sonuç / judge belirsizliği, yüksek kalış oranı. C2'nin durum cümleleri gerekçede geçmiyor.
- Gecikme: en yavaş tur medyanı 5 s (v1'de 1 s), en kötü 9 s; kapatan müşteri yok.
- Değişiklikler: C3 tarih aktarımı tts → llm (önce aynı mesajdaki soruyu cevapla, sonra kararı kelimesi kelimesine söyle); C4 skill: her düğümün giriş cümlesi müşterinin son mesajındaki soruyu önce cevaplar.

## fb-a v4 (sürüm 4, hash 527861b3363a1d1a, build 245 s) — release kontrolleri BAŞARISIZ, ardından F2 ölçümü 0/4
- Duman testi 504 (iki kez; örnek çağrı değişkenleriyle de). Workflow'da test_variables boştu → düzeltme: skill + lint test_variables şartı.
- F2 (simülasyon 145f1095-0f7b-411f-91aa-ecda4248ba53): PUB-04/06/07/10 hepsi KALDI, aynı ilk nedensel hata: `fetch_account` düğüm eşlemesi `data.products` → `products` hiç set olmadı (platform liste değerini değişkene yazmıyor; yalnız `fetch_account_response.data.products.0.*` düzleştirilmiş anahtarlar var) → `products is set` geçişi düştü → "hesap yüklenemedi" → no_promise/service_error. Sınıf: tekrarlanabilir hata (4/4), build'e özgü (v3'te yoktu) → build varyansı.
- Platform bulgusu (doğrulandı): liste tipindeki yanıt alanı response_mapping ile değişkene yazılmıyor.
- Düzeltme C5: lint, tool API'de dizi/nesne olan yanıt alanının değişkene eşlenmesini hata sayar; skill listeleri düzleştirilmiş anahtarlardan okumayı söyler.

## F3 — fb-a v5 (sürüm 5, hash 5862f86ed71722db, build 159 s), simülasyon b2b795d3-a12e-4e93-932a-d369b3033d20 — 3/4 tek koşu
- PUB-04 GEÇTİ, PUB-06 GEÇTİ, PUB-07 GEÇTİ (C1, C3, C5 sonrası).
- PUB-10 KALDI (ledger): ilk create_promise HTTP hatası → model tekrar denemedi, "It was not done…" deyip no_promise/service_error kapattı. Hook hata yanıtında çalışmıyor (sonuç gövdesi yok). k37 tekrar denemesi modelin hafızasına kalmış; v1/v3'te model tekrar denemişti → build varyansı + değişken davranış.
- Gecikme: en yavaş tur medyanı 8 s, en kötü 12 s (v1: 1 s). İzlenecek risk: >10 s'de müşteri kapatma.
- C6: yazma tekrarları tool `config.maxRetries` ile platforma; model hata raporunda tekrar çağırmaz. (Platformun bu hata türünde tekrar denediği henüz doğrulanmadı.)

## F4 — fb-a v6 (sürüm 6, hash e6255c95794800ea, build 263 s, 22 model çağrısı), simülasyon 94d11452-0a84-46d0-b060-c5a07f75c0e6 — 0/4
- Dört vakada aynı ilk nedensel hata: kimlik düğümünde model verify_identity'yi hiç çağırmadı, doğum tarihini döngüde tekrar sordu; 4 müşteri kapattı. Sınıf: tekrarlanabilir hata (4/4), build'e özgü.
- create_promise config maxRetries=1 yazıldı (C6) ama ajan o noktaya ulaşmadığı için C6 sınanamadı.
- Release kontrolü (tek chat turu) bu bozukluğu yakalamadı.

## Ara değerlendirme (yedek builder, Brief A, hedef kümeler, tek koşular)
| build | sürüm | sonuç | ilk nedensel hata |
|---|---|---|---|
| v1 | 1 | 4/6 (baseline) | PUB-07 tarih (model), PUB-10 judge |
| v3 | 3 | 2/4 | PUB-04 robot sorusu, PUB-10 judge |
| v4 | 4 | 0/4 | liste eşlemesi (account) |
| v5 | 5 | 3/4 | PUB-10 tekrar deneme yok |
| v6 | 6 | 0/4 | kimlik tool'u hiç çağrılmıyor |
- Sonuç: düzeltmeler hedeflerinde çalıştı (C1: PUB-07 v3+v5 geçti; C3: PUB-04 robot sorusu v5 geçti; C5 lint v4 hatasını yakalıyor), ama yedek builder her koşuda yeni mimari tasarlıyor ve 5 build'in 2'si temelden bozuk ajan üretti. Ana risk build varyansı.
- Gecikme artışı: en yavaş tur medyanı v1 1 s → v5 8 s → v6 10 s.
- Her koşunun workflow'u out/fb-a-<zaman>/workflow.json altında korunuyor.

## Ana yol (derleyici-lite): Spec → sabit bileşenler → doğrulama (slot cmp-a)
- Değişiklikler: builder/toolspec.py, spec_extract.py (tek Opus çağrısı + deterministik API doğrulaması), components.py (v5 iskeleti; her konuşma düğümünde on_enter_first_entry_only; hesap listesi düzleştirilmiş anahtarlardan api_binding ile; close_call pre-hook gerçek transfer/kayıt durumundan; tekrar sayısı tek katmanda maxRetries), behavior.py (yapısal + pratik davranış testleri), build.py (aday klasörleri, ortak bütçe, lint hatasında yayın yok, GAP ayrıştırma, teslim dosyası yalnız kontroller geçerse).
- c1 (20261011-004605): extra_rules sınıflandırması konuşma kurallarını "structural" saydı → ana yol yedeğe düştü (main-only modda durdu). Şema tanımları netleştirildi.
- c2 (20261011-004756): workflow 1fd64b44-c8bc-4d02-b609-53ad5ee9205e, agent 5384dbbe-dcdc-441d-b24e-ee4f1c1d1a7a, sürüm 1, hash 700fffa405cbf016, build 125 s, 1 model çağrısı. Yapısal davranış 4/4 PASS; PUB-06 pratik kimlik→hesap→müzakere 4/4 PASS (Adım A).
- Adım B, PUB-10 (simülasyon 515b7d37-d146-48f3-91fa-5a2142547986): ledger DOĞRU — create_promise hata ('nothing was recorded') + ikinci deneme başarılı, tek promise. İkinci denemeyi platform mı model mi yaptı: olaylar ayırt etmiyor (araya asistan mesajı yok, 1,7 s; model'e "tekrar çağırma" denmişti) — kesin değil. Judge: açılıştaki "this call is recorded" (aynı gerekçe, açılışın değerlendirildiği 4 koşunun 3'ü). Ayrıca: close_call sonrası hangup geçişi tetiklenmedi (tool öncesi asistan mesajı yok), "no speakable content" ×2, müşteri 60 s sonra kapattı. Read-back atlandı (müşteri erken onayladı).
- Değişiklikler (ayrı sinyallerle izlenecek): C7 close_call preSpeech = brief'in veda cümlesi (sinyal: endedReason); C8 onay yalnız ajanın read-back'ine (sinyal: transcript'te read-back); C9 açılış kayıt bildirimi etken cümleyle (sinyal: judge gerekçesi).

## Adım C — cmp-a c3 (aday candidates/cmp-a/20261011-005425, workflow 1fd64b44-…, sürüm 2, hash c5a4cc33942dbc7d, build 156 s, 1 Opus çağrısı), simülasyon f946a5dc-9590-4911-8583-007e5b5f131f — 3/4 tek koşu
- Yayın kontrolleri: yapısal 4/4, PUB-06 pratik 4/4.
- PUB-04 GEÇTİ, PUB-07 GEÇTİ, PUB-10 GEÇTİ (ledger: hata + tekrar → tek promise; judge açılışı kabul etti — C9 sinyali), PUB-06 KALDI (yalnız judge; ledger doğru): ikna merdiveni modelde — "Can you make this payment today?" atlandı; "bugün olmaz" sonrası deneme 1 (floor, bu Cuma) yerine "date and amount you can pay" soruldu (k24 ihlali). Sınıf: tek koşu; mekanizma = stateful kural modele bırakılmış (trace'te bilinen eksik).
- C7: 4/4 çağrı assistant-ended-call (asılı kalma yok). C8: 4/4 transcript'te read-back var.
- Gecikme: çağrı başına en yavaş tur 5,6 / 9,3 / 15,2 / 1,5 s; simülasyon 405 s. Risk izlenecek.

## Adım D — tüm Brief A, aynı aday (sürüm 2, hash c5a4cc33942dbc7d)
- Simülasyon 9add9824-2bca-462c-a436-ed6a76ad9daf: 5/10 PASS (01, 02, 06, 08, 09). 5 vaka (03, 04, 05, 07, 10) judge sonucu "inconclusive", gerekçe yok; ledger kontrolleri bu 5'te doğru. Sınıf: şüpheli platform/judge hatası; ham sonuç korunuyor, skordan silinmedi.
- Aynı 5 vakanın tekrarı, simülasyon 429d721d-1857-40a2-b817-d6956e2f3b4f: 5/5 PASS (judge kararlı).
- İki simülasyonda agentVersionNumber = 2 (yürütme sürümü kanıtı).
- v2 tek koşu özeti: her public A vakası en az bir kez geçti; PUB-06 değişken (C'de kaldı, D'de geçti). pass^3 değil.

## Adım E — kritik A vakaları × 3 tekrar, aynı aday (cmp-a sürüm 2, hash c5a4cc33942dbc7d), son simülasyon 45f38efb-a9e8-44f3-b799-fb4120383395
- PUB-03, 04, 05, 06, 07, 10: hepsi 3/3 (18/18 koşu; judge kararsızlığı yok). pass^3 = 6/6 bu alt kümede.
- Gecikme: tekrar 2'de en yavaş tur medyanı 15 s (uyarı), kapatan müşteri yok.
- PUB-06'nın v2 toplamı: 5 koşuda 4 geçiş (C'deki kalış kayıtta).

## Brief A+B adayı (cmp-ab, candidates/cmp-ab/20261011-010951, workflow 6979adbf-…, sürüm 1, hash 26e14257230c8a17, build 136 s, 1 Opus çağrısı)
- Girdi: briefs/brief-a.md + brief-b.md otomatik birleştirildi (out/brief-ab.md; elle düzenleme yok). Policy, B'nin A'yı değiştiren 5 hükmünü kapsamlarıyla amendment olarak kaydetti.
- Yayın kontrolleri: yapısal 4/4, PUB-11 pratik 4/4.
- Brief B × 1 (simülasyon ee93551c-7c91-47f0-b28b-9c897500cf83): 1/3. PUB-11 GEÇTİ. PUB-12 KALDI (yalnız judge): erken bant taşıt kredisinde deneme sayısı aşıldı (ürün başına sayaç modelde). PUB-13 KALDI (ledger): tek tarih iki ürüne — tarih aracı ürün başına doğru karar verdi (kart 30 Eki ok, kredi → 23 Eki), ama model müşterinin 23 kabulünü iki ürüne uyguladı (B6 ihlali); ayrıca ürünler tarih sorusundan önce belirtilmedi (B2), create_promise öncesi "I have recorded" dendi (dürüstlük), tek read-back yok (B7).

## Müzakere çalışma zamanı (builder/runtime/negotiation.py) — yerel
- Platform sondası G1b (chat, sahte müşteri): code_exec tool dizi argümanı alıyor (kart önerisi + kredi reddi ayrı 2 olay); passthrough konuşma düğümü tts söyleyip beklemeden ilerliyor; motorun çalıştırdığı create_promise baked değerler + pre-hook float ile gidiyor; sonuç <düğüm>_success_count / _failure_count / _response.* değişkenlerine yazılıyor (HTTP hatasında post-hook çalışmıyor). Takvimsiz istemde model yılı uydurdu (2023/2024) → kod geçmiş tarihi yakalıyor.
- Kod artık şunları karar veriyor: deneme merdiveni ve ürün başına sayaç, tutar (floor/aralık), tarih (iş günü/deadline/belirsiz), ortak tarihin ürün başına uygulanması, read-back metni ve onay sürümü, kayıt (motor, tek katman tekrar), notlar (transferde yok), kapanış sonucu. Modelde kalan: müşterinin sözünü olaylara ve tarihi YYYY-MM-DD'ye çevirmek, transfer kararı, kimlik akışı, üçüncü kişi/callback.
- Yerel testler: tests/test_negotiation.py 42/42 (beklenenler brief kurallarından elle; ürün sırası ve now değiştirilmiş varyantlar dahil), tests/test_date_tool.py 14/14. Üretici + lint + Freya dry-run temiz (eski policy + test şablonlarıyla).

## Müzakere runtime, ilk uçtan uca adaylar (n1)
- cmp-a n1: candidates/cmp-a/20261011-013957, sürüm 3, hash 6a645cdc4a087dc4, build 138 s; cmp-ab n1: candidates/cmp-ab/20261011-014216, sürüm 2, hash c6b4c887ae86ae4a, build 145 s. Otomatik policy: A ortak-tarih kuralı kapalı/not yok; A+B açık/not var (doğru). Yayın kontrolleri geçti (B'de tüm ürünlerin borcu ilk sorudan önce söylendi).
- Canlı (tek koşu): PUB-11 GEÇTİ, PUB-13 GEÇTİ (önceki ledger hatası giderildi: kart 30 Eki, kredi 23 Eki). PUB-12 KALDI (ledger: promise/not yok, no_promise/service_error, müşteri kapattı). PUB-06 KALDI (judge: "What amount would you be able to pay today?", ayrıca aktarım "payment plan" ekledi).
- İlk nedensel hata (kod, kanıtlı): tekrar-olay anahtarı negotiate.total_turns'a bağlıydı; aktarım sonrası müşteri mesajları neg_relay'de sayıldığı için ikinci "p2 refuses" ilk turdaki ile aynı anahtarı aldı ve atlandı → durum değişmedi, neg_say boş → aktarım modeli kendi cümlelerini uydurdu. Yerel test bunu kaçırmıştı (sayaç her çağrıda yapay artırılıyordu).
- İkinci neden (gözlem): LLM aktarımı "kelimesi kelimesine" talimatına uymadı (soru ekledi, plan teklif etti, borç cümlesinden ilk soruyu düşürdü).
- Düzeltme N2: anahtar = negotiate + neg_relay toplam tur sayısı; kod asla boş cümle döndürmez (bekleyen teklifi yineler); karar ve borç bildirimi TTS ile kelimesi kelimesine; olay aracına isteğe bağlı tek cümlelik "answer" alanı (kod kararın önüne koyar). Testler gerçekçi sayaçla: 45/45 (T15 canlı PUB-12 regresyonu, T16 boş cevap/answer).
- Gecikme: bu koşularda en yavaş tur medyanı 16–17 s, en kötü 29 s, B'de 1 kapatma. LLM aktarımını kaldırmak tur başına bir model çağrısını azaltır.

## n2 adaylar: cmp-a sürüm 4 (37cd27143aa42d7a), cmp-ab sürüm 3 (d8fef97aec53247a) — canlı tek koşu
- PUB-06 KALDI (judge): kodun floor teklifi tek ve doğru; müşteri "minimum ne kadar?" diye sorunca negotiate modeli cevaba kendi teklifini ekledi ("Would you like to make this payment today?") → "iki kez teklif".
- PUB-11 GEÇTİ. PUB-12 ve PUB-13 KALDI (ledger: create_promise hiç yok, no_promise/service_error, müşteri kapattı): read-back'e "Yes, I confirm." neg_relay'e düştü; negotiate modeli confirms olayını çağırmadı, "kaydedemedim" uydurdu. Onay hâlâ modelin tool çağrısına bağlıydı.
- Kimlik giriş cümlesinde model "account flagged for suspicious activity" uydurdu (dürüstlük riski).
- Gecikme düzeldi: en yavaş tur medyanı 4 s (TTS aktarım).
- Düzeltme N3: read-back onayı deterministik (neg_relay çıkarımı rb_answer + neg_phase=readback AND → neg_confirm kodu sürüm kontrolü → kayıt); negotiate modeli soruya cevap verirken teklif/tarih/ödeme sorusu eklemez; kimlik giriş istemi sebep/hesap/dolandırıcılık söylemeyi yasaklar. Testler 47/47.

## n3 adaylar: cmp-a sürüm 5 (candidates/cmp-a/20261011-020200, hash 438a08a6f5f97b07, build 103 s), cmp-ab sürüm 4 (candidates/cmp-ab/20261011-020344, hash f49b52e8c055489f, build 131 s)
- Hedefli canlı tek koşu: PUB-06 GEÇTİ (sim 65874f00-888a-44e4-92d6-69701ebc5863); PUB-11, PUB-12, PUB-13 GEÇTİ (sim 664023af-6a69-4dfb-9454-5a9d9c51371a; PUB-12 ledger: promise kart + refused notlar). Gecikme medyan 2–6 s, kapatma yok.

## V (3 tekrar), n3 adaylar — cmp-a sürüm 5 / cmp-ab sürüm 4
- Brief B (sim son c8e84761-95b5-48f7-873b-119b53762d96): PUB-11 3/3, PUB-12 3/3, PUB-13 3/3 → pass^3 3/3 (9/9 koşu). Tekrar 1'de gecikme medyanı 19 s (uyarı), kapatma yok.
- Brief A (sim son f484150b-ab79-47a0-8e70-f6f135a1e897): pass^3 6/10 (22/30 koşu). 01, 02, 03, 07, 09, 10: 3/3. PUB-04 2/3, PUB-05 1/3, PUB-06 1/3, PUB-08 0/3.
- İlk nedensel hatalar:
  - PUB-08 (kod): "paid" olayı aşamayı finish'e geçirince olayın cümlesi ("payments can take one business day") aktarım atlandığı için kayboldu.
  - PUB-06 (kod/yorum): "too much" sonrası floor bugüne teklif edildi; "you tell me" → deneme 1 floor'u ikinci kez önerdi. Brief k30 + k26 ("attempt 2 may name the floor AGAIN") okunuşu: "too much" sonrası floor teklifi = deneme 1 (bu haftanın son iş günü).
  - PUB-05 (model+kod): model hardship cümlelerini kendi söyledi / olayı göndermedi; declines_support durum değiştirmedi → ikna sürdü; bir koşuda sempati iki kez.
  - PUB-04 (mekanizma): müşteri "Are you a robot?" sorusunu kimlik→borç geçişinde sordu; TTS borç bildirimi soruyu atladı.
  - Biçim: SMS cümlesi iki kez, read-back'te "..".
- Düzeltmeler N4: too_much = deneme 1 floor; declines_support → hardship (her durumda); finish'e geçen olayın cümlesi kapanış satırına; zorunlu cümle tekrarı yok; noktalama; kimlik düğümüne pending_question çıkarımı (robot/scam) → kod borç bildiriminin başına brief'in cevabını koyar; negotiate modeli olay çağırırken kendisi konuşmaz, hardship/dispute/paid cümlelerini kod söyler. Yerel: 51/51 + 14/14.

## n4 adaylar: cmp-a sürüm 6 (candidates/cmp-a/20261011-023040, hash 6523418828d04e72), cmp-ab sürüm 5 (…/20261011-023247, hash 0136cdf6e023d5ef)
- Hedefli tek koşu: PUB-04 GEÇTİ, PUB-06 GEÇTİ, PUB-08 GEÇTİ (sim 5a2f0674-7986-414c-a281-174f55e0e6fa); PUB-11/12/13 GEÇTİ (sim d6c059f4-3228-4069-ad5e-85c9c76ca9ad).
- PUB-05 KALDI (ledger refused, judge: sempati yok, ikna): müşteri iş kaybını kimlik aşamasında söyledi; müzakere mesajı yalnız "hiçbir şey ödeyemem, indirim?" → model refuses gönderdi.
- N5: hardship_seen çıkarımı (negotiate + neg_relay; tanım brief'ten hardship_definition) → kod, ele alınmamış zorlukta reddi destek teklifine çevirir; destek teklifine "hayır"/ret = hardship. Yerel 54/54.

## n5 adaylar
- cmp-a sürüm 7 (candidates/cmp-a/20261011-023911, hash a0a7f5373eaf0d7b): PUB-05 GEÇTİ (sim 71792431-edc4-4790-9dc4-7b98ece59942).
- cmp-ab sürüm 6 (…/20261011-024051, hash 380cce00499d92af): yayın kontrolleri BAŞARISIZ — PUB-13 pratik sohbetinde kimlik giriş satırı (LLM) ilk soruyu sormadı ("How can I help you today?"), model sorulmadan gelen cevabı doğrulamadı, soru döngüsü. Aday terfi ettirilmedi.
- N6: kimlik giriş satırı TTS ile policy'deki ilk güvenlik sorusu (önceki LLM girişi bir kez "şüpheli işlem" de uydurmuştu). Doğrulama mekaniği değişmedi.

## V (3 tekrar), n6 adaylar — cmp-a sürüm 8 (candidates/cmp-a/20261011-024419, hash cc14d923809f6acf), cmp-ab sürüm 7 (candidates/cmp-ab/20261011-024603, hash ef24204f232b8460)
- Brief A (son sim ddc8912c-a750-4841-a2dd-7cf99953c523): pass^3 9/10 (29/30 koşu). PUB-05 2/3: bir koşuda sempati iki cümle (model kendi + kodun cümlesi). Gecikme medyan 2–3 s, kapatma yok.
- Brief B (son sim 31c527e1-e0ff-4bd3-b3f2-c7da7769bdce): pass^3 3/3 (9/9). Gecikme medyan 5–11 s (bir tekrarda uyarı), kapatma yok.

## F — aynı builder kodu (research/builder-version.txt = 1a5910570bcf9fe0), aynı girdiler, iki bağımsız build (Brief A)
- f1: candidates/cmp-a-f1/20261011-025907, workflow 13da28c6-…, sürüm 1, hash 4e219728f8323836, 128 s. f2: candidates/cmp-a-f2/20261011-030116, workflow 3b7dce9e-…, sürüm 1, hash 5937ee68f0107e90, 113 s. İkisi de yayın kontrollerini geçti.
- eval/compare_builds.py: karar değerleri aynı (yalnız extra_rules sınıf sayıları farklı → yalnız bilinen-eksik listesi); yapı (düğüm, geçiş, tool/config, giriş bayrakları) aynı; prompt metni farklı (kural cümlelerinin aşamalara dağılımı: global 6/11, negotiate 27/31). Ölçülen n6 adayı ile f1 de yapı/karar olarak aynı.
- Brief A × 1: f1 10/10 (sim 99b344a6-25ac-4e01-b403-abb818cf1719), f2 10/10 (sim 48b545ed-28b9-4cc9-b8b4-9a9156dbeb5d). Kapatma yok; en kötü tur 23–24 s.

## 11 Ekim — inceleme bulgularının yerel düzeltmesi (model/Freya çağrısı yok)
- Kaynak: freya-kapsamli-inceleme.md + runtime-sonda-sonuclari.json (veri olarak), brief A/B.
- Yeni regresyon testi tests/test_negotiation_regress.py (24): düzeltme öncesi 17 KALDI (results/regress-before-fix.txt), sonrası 24/24 (results/regress-after-fix.txt). Ortak düzenek tests/negotiation_harness.py (not ve kayıt sonuçları sayaç taklidiyle).
- Düzeltmeler (builder/runtime/negotiation.py, builder/components.py): parçalı alanların korunması (bekleyen tutar, read-back'te değişmeyen alanın korunması, tutar-yalnız önerinin bekleyen teklif tarihini koruması); tek mesajdaki olayların birlikte değerlendirilmesi (öneri varken ret/too_much düşer; too_much+ret tek floor; onay+değişiklik → onay yok); tam paket onayı (read-back paketi saklanır, iki onay yolu aynı kontrol, kısmi onay yeniden sorar); REC_NEXT yalnız onaylanmış paketten yazar, transfer sonrası yazmaz, aynı kaydı tekrar göndermez; not sonucu her not için kendi sayaç artışıyla, tekrar yok, not hatası outcome'u değiştirmez; FINISH çözülmemiş üründe "hazır değil" (2 kez sınırlı), uydurma refused/service_error yok; close_check close_call sonucunu görünür kılar; B4 karma ilk cevapta sonraki ürün deneme 1'den başlar; PUB-05 için zorluk cümlesinin tek sahibi kod (hardship_seen → hardship_go, model konuşmadan önce).
- Var olan testler: test_negotiation 54/54 (fixture'a note_node anahtarı; T17b öncülü A35 düzeltmesi yüzünden tatil-değişikliği tetikleyicisiyle yeniden kuruldu, özellik aynı), tarih 14/14, yeni yapı testi 18/18.
- Hazırlanan (çalıştırılmadı): experiments/memo-late-deadline, experiments/api-rename; README_SUBMISSION.md; research/submission-checklist.md; build.py --local-only.
- Temiz kopya provası (183 dosya, gizli değer 0): 4 test seti 0 hata, --help OK.
- n6 canlı skorları bu koda AİT DEĞİL; yeni kod canlıda ölçülmedi.

## 11 Ekim — bulut oturumu (claude/lucid-fermat-vxp9u7; ayrıntı: research/cloud-final-report.md, cloud-progress.md)
- Erişim: Freya/banka anahtarları proxy'de; opt-in `FREYA_AUTH_VIA_PROXY=1` (kit dosyaları değişmedi). SDK erişimi 1 çağrıyla doğrulandı.
- Motor: A32 zorluk + gönüllü öneri (öneri bekletme, tek empati sahibi), zorluk sonrası ikna yok, `all` kapsam düzeltmesi, rec_next blocked bayrağı, A45 sayacı policy'den.
- Platform kontrolü chat C2 (cl-a v1): motorun zorluk yolu platformda çöktü — `global` fonksiyon içinde NameError; yerel düz exec() gizliyordu. Düzeltme c8de7c9; test düzeneği artık platform gibi fonksiyon içinde çalıştırıyor; lint reddediyor. cl-a v1/cl-ab v1 geçersiz.
- Chat C3 (cl-ab v1): kısmi onay kayıt açmadı; tam onay → doğru iki kayıt.
- cl-a v2 (233c8dfe1a7d9d91): PUB-05/06/10 × 3 = 9/9, PUB-04/08 × 1 = 2/2. cl-ab v2 (8abfb3c856c81f25): PUB-11/12/13 × 3 = 9/9.
- Varyasyon zorluk + "Cuma 300" × 3: 2/3 (kalan: simüle müşteri mesajları yarım). Tarzlar: in_words, corrects, asks_back, talkative 1/1; pieces PUB-06 1/2 (kimlikte parçalar birleştirilmedi, banka kanıtsız failed). Kimlik istemi düzeltmesi 503d996 ölçülmedi.
- Kullanım: 4/4 build, 29/30 koşu, 4/4 chat, 5 Opus çağrısı. Memo ve API çıkarım deneyi çalıştırılmadı.
