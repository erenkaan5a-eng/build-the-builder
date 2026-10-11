# Brief A/B kural → uygulama tablosu (bulut oturumu, 11 Ekim 2026)

Kaynak: briefs/brief-a.md (A1–47), briefs/brief-b.md (B1–11, Closing); research/review/*.md notları öneri olarak okundu.
Kod: builder/components.py (workflow), builder/runtime/negotiation.py (motor), builder/spec_extract.py (policy).
Testler: N = tests/test_negotiation.py, R = tests/test_negotiation_regress.py, D = tests/test_date_tool.py, S = tests/test_generator_structure.py.
Canlı kanıt yalnız deney günlüğündeki n6/F adaylarına aittir; bu oturumun kodu için canlı sonuç ayrı raporlanır (cloud-progress.md).

Durum kodları: **U** kodla uygulanmış + yerel test · **P** prompt/model yorumu (kodla zorlanmıyor) · **A** hâlâ açık · **B** kaynak yorumu belirsiz · **D** düşük öncelikli savunma önerisi (ertelendi).

| Kural | Uygulayan bileşen | Test / kanıt | Modelde kalan yorum | Durum / karar |
|---|---|---|---|---|
| A1 açılış cümlesi, kayıt bildirimi, kimlikten önce borç sözcüğü yok | policy.opening_line → opening TTS | yapısal davranış kontrolü "opening line spoken"; PUB-10 judge geçmişi (C9) | cümlenin brief'e uygunluğu extraction'da | U (metin model çıkarımı) |
| A2 "Am I speaking with…" | opening_line TTS | — | — | U |
| A3 teyit anlamı, iki soru, unclear | `speaker` extraction + opening prompt | public A geçişleri | teyit sayacı modelde | P/A — kod sayacı yok (not A1–4 önerisi ertelendi) |
| A4 robot sorusu | identity `pending_question` → DEAL_CODE robot_answer; ENGINE `answer` | PUB-04 n4/n6 geçti | algılama modelde | U+P |
| A5 üçüncü kişiye neden söylenmez | third_party prompt; araç yok | PUB-02 geçti | konuşma modelde | P |
| A6 callback penceresi | SETUP_CODE pencere metni; karar modelde | — | geçerlilik modelde (known_gaps) | A — düşük/orta; sınır saatleri test edilmedi |
| A7 pencere dışı bir kez tekrar | prompt | — | sayaç modelde | A/P |
| A8 wrong_number, A9 deceased | prompt + close tablosu | — | modelde | P |
| A10 yakına güvenlik sorusu/hesap yok | third_party düğümünde verify/get_account aracı yok | yapısal | — | U |
| A11 iki soru sırası, DOB YYYY-MM-DD | identity TTS ilk soru, verify tool formatı | yapısal kontrol (alan doğru) | sıra/format çevirisi modelde | U+P |
| A12 toplam üç yanlış | banka `wrong_answers_left` → VERIFY_POST mesajı | PUB-03, PUB-12 geçti | modelin mesaja uyması | U(banka)+P |
| A13 day_month_swapped | VERIFY_POST hint → policy mesajı | — | — | U+P |
| A14 failed kapanışı | prompt + close_call | PUB-03 | modelde | P |
| A15 ret → bir açıklama → declined | prompt (extra_rules stateful) | — | sayaç modelde | A (düşük) |
| A16 iki soru geçince get_account | `all_verified` geçişi → engine-run fetch_account | yapısal "no account call before verification" | — | U |
| A17 borç cümlesi | DEAL_CODE `debt_say` TTS | practice kontrolü | — | U |
| A18 deadline bantları | DEAL_CODE add_bd; ENGINE judge_date | D (PUB-04/07/13), N T2 | — | U |
| A19 tarih geçerliliği | judge_date | D | — | U |
| A20 hafta sonu/tatil → sonraki iş günü; deadline sonrası A23 | judge_date (after > not_bd sırası) | D, N T6 | — | U |
| A21 belirsiz → bir kez sor → deadline | propose vague sayacı + pending_amount | N T6/T6b, R A1 | "vague" sınıfı modelde | U |
| A22 this/next weekday | CALENDAR tablosu (bu/sonraki hafta) | — | eşleme modelde (extra_rules computational) | A — kodla çözülmüyor; known_gaps'te |
| A23 deadline sonrası → deadline; reddi → düz ret | propose 'after' → offer; refuse() | N T2c | — | U |
| A24 önce tam tutar; "ne kadar ödeyebilirsiniz" yok | ENGINE ilk teklif full; negotiate prompt yasağı | PUB-06 geçti | soru üretmeme modelde | U+P |
| A25 floor alanları | policy floor_field + DEAL_CODE | spec_extract.validate | — | U |
| A26 "too much" → floor bir kez, kalan gecikmede; ret = düz ret; deneme 2 floor+deadline | ENGINE too_much (deneme 1 sayılır) | N T3/T20, R E1–E4 | — | U; **B**: too_much'ın deneme 1'i tüketmesi kaynak yorumu (aşağıda) |
| A27 floor–full arası kabul; altı → floor bir kez | propose() | N T5 | — | U; D: `min(amt, full)` kırpması ve 0.005 toleransı |
| A28 ilk soru | DEAL_CODE first_ask_one | — | — | U |
| A29 öneri asla ret değil | ENGINE tur düzeyi olay birleştirme | R E4 | olay sınıfı modelde | U |
| A30 ikna merdiveni | ladder_offer/next_attempt | N T1/T3 | ret/cevapsızlık sınıfı modelde | U |
| A31 haklar bitince dur, reddedileni tekrarlama | refused listesi | N T1/T3 | — | U |
| A32 zorluk: tek empati, ikna yok, destek teklifi; kabul→support transfer; ret→hardship; gönüllü öneri kaydedilir | HARDSHIP düğümü + ENGINE (bu oturum: öneri bekletme, `hs` bayrağı, answer düşürme, `offer_named` ile yönlendirme) | N T13c/T19/T21/T21b, R F1–F2, G1–G9 | zorluk/öneri algılama (extraction), destek kabulünde transfer çağrısı | U (yerel); **canlıda doğrulanacak** |
| A33 indirim/plan yok | prompt; her teklifi kod üretir | PUB-05 judge | modelin serbest metni | U+P |
| A34 read-back + "Do you confirm?" + açık evet | ENGINE readback, CONFIRM, rb_pkg/confirmed_pkg, REC_NEXT paket eşitliği | N T7/T17, R B1–B3, X1–X2, H7–H8 | evet/değişiklik ayrımı modelde (rb_answer) | U |
| A35 read-back'te değişiklik → yeniden kontrol, değişmeyen alan korunur | changes/proposes + agreed alanlarının korunması | R A2–A4, B3, N T7/T17b | — | U |
| A36 ürün başına bir promise; sonra mobil uygulama | REC_NEXT tekrar yazmaz | R B4 | "mobil uygulama" cümlesi modelde | U+P |
| A37 ok:true sonrası "kaydedildi"; bir retry; sonra service_error | record_one (maxRetries 0) + REC_NEXT sayaç | N T10/T10b, R H1/H3; PUB-10 n6 3/3 | — | U |
| A38 SMS cümlesi yalnız başarı sonrası | FINISH after_promise_sentence | R H2/H3, N T18b | — | U |
| A39 zaten ödedim | ENGINE paid | N T13/T18; PUB-08 | paid/dispute ayrımı modelde | U+P |
| A40 itiraz | ENGINE dispute | N T13b | sınıflandırma modelde | U+P |
| A41 yeni plan → restructuring transfer | transfer aracı (model) + FINISH/CLOSE_PRE eşlemesi | N T12, R C3; PUB-09 | transfer kararı ve kuyruk modelde | P (karar) + U (kapanış) |
| A42 insan isteği: bir kez yardım teklifi, ısrarda general | prompt | — | sayaç modelde | A |
| A43 dolandırıcılık sorusu | scam_answer (identity) / answer alanı | — | modelde | U+P |
| A44 bilinmeyen bilgi | prompt | — | modelde | P |
| A45 iki kez konuşmak istemiyorum → refused | ENGINE `stop` sayacı (bu oturum: policy `stop_statements_to_close`, yoksa eski davranış) | R I1–I3 | olay sınıfı modelde; kimlik öncesi kısım modelde | U (yerel); kimlik öncesi P |
| A46 tek close_call, son araç, tablo | finish_prep→finish_say→notes→close_one→close_check; diğer düğümlerde t_close + CLOSE_PRE | S zincir testi, R H9 | erken çıkış yollarında sonuç seçimi modelde | U |
| A47 veda close'dan önce | finish_say TTS / t_close preSpeech | — | — | U |
| B1 1–3 ürün | DEAL_CODE düzleştirilmiş liste | S, N T1 | — | U; D: kardinalite sınırı denetimi yok |
| B2 her ürün sorudan önce | debt_say + first_ask_all | practice kontrolü; PUB-11 | — | U; D: practice kontrolü aynı tutarlı ürünlerde zayıf |
| B3 ürün başına bant/deadline | DEAL_CODE | N T2/T2b | — | U |
| B4 önce toplu bugün; sonra sırayla deneme 1; bugün tekrar yok | ENGINE named → next_attempt | N T1, R D1 | — | U |
| B5 ürün başına sayaç | per-product `used` | N T1; PUB-12 | — | U |
| B6 ortak tarih deadline sonrası → o ürün kendi deadline'ında, read-back'te söylenir | shared clamp + readback_clamped | N T2/T2b; PUB-13 | — | U; D: ortak köken = `len(scope)>1` |
| B7 tek toplu read-back + tek onay, sonra ürün başına kayıt | rb_pkg/confirmed_pkg | R A5/B1/B2b/H7/H8 | — | U |
| B8 promise olmayan ürüne not | FINISH notes + NOTES_NEXT sonuç izleme | N T1, R C1/C2 | — | U |
| B9 paid/dispute çağrıyı bitirmez | ürün başına durum | N T13b | — | U |
| B10 transferde kaydedilmemiş vaat ve not yok | REC_NEXT transferred() engeli; FINISH t_ok dalı; blocked → neg_flag temizlenir (bu oturum) | R C3/H4/H5, N T12 | transfer kararı modelde; kayıt zinciri sırasında kesinti platformda ölçülmedi | U (yerel) |
| B11 bir ürün iki kez başarısız → diğerleri kalır, service_error notu | REC_NEXT + FINISH | N T11, R H1/H2 | — | U |
| B Closing: transfer > promise > hepsi paid > ilk paid olmayan neden | FINISH reducer; çözülmemiş ürün "hazır değil" (2 kez sınırlı) | N T13/T13b, R C2/X3/H6 | — | U |

## Notların yeniden değerlendirmesi (güncel kodda)

**Uygulanmış (önceki 11 Ekim yerel düzeltmeleri, bu oturumda testle yeniden doğrulandı):** parçalı tutar/tarih koruma (inceleme bulgusu 2, 3), tam paket onayı ve iki onay yolunun aynı kontrolü (1), REC_NEXT doğrudan giriş guard'ı (6), not sonucu izleme (4), FINISH "hazır değil" (7), B4 karma ilk cevap (5), transfer sonrası not/kayıt yok, tek katman retry.

**Bu oturumda uygulanan (yerel test; canlı doğrulama ayrı):**
1. A32 karma mesaj: zorluk + gönüllü tarih/tutar. Önceki kodda (a) deterministik `hardship_go` yönlendirmesi diyalog modelinden önce çalışıp öneriyi olaya dönüştürmeden yutuyordu; (b) motor yolunda model yalnız `proposes` gönderirse empati hiç söylenmiyordu; (c) `answer` alanı ikinci empati ekleyebiliyordu (R G1 eski kodda: "I am so sorry about your job. Sorry to hear…" + aynı turda taban teklifi). Şimdi: aynı mesajda tarih/tutar varsa (`offer_named`) yönlendirme diyalog modeline bırakılır; motor empati+destek teklifini tek başına söyler, öneriyi saklar, destek teklifi cevaplanınca önceki öneriyi tarih/tutar kurallarıyla işler.
2. A32 "işimi kaybettim, ödeyemem" tek mesajda (motor yolu): eski kod `hardship`+`refuses` olaylarında destek teklifini söyleyip aynı turda çağrıyı kapatıyordu (R G6). Şimdi o turdaki "hayır" ödeme sorusunun cevabı sayılır, destek teklifi açık kalır.
3. A32 ikna yasağı kalıcı: zorluk görülen üründe sonraki ret/too_much ikna teklifi üretmez (R G3, G9).
4. `product_id="all"` ile gelen destek reddi/ret, destek teklifi bekleyen ürünlere ulaşmıyordu (B'de "tekrar eder misiniz" döngüsü riski) — düzeltildi (R G9).
5. REC_NEXT `blocked` dönüşünde `neg_flag=record` kalıyordu; transfer sonrası negotiate yönlendirmesi rec_next'e geri dönebiliyordu — düzeltildi (R H4).
6. A45 sayacı policy'den (R I1–I3); policy alanı yoksa eski davranış.
7. Kimlik aşamasında söylenen zorluk: identity extraction + hesap adımında kalıcı `hardship_early` (S yapı testi). Risk: kimlik aşamasında yanlış pozitif → normal vakada gereksiz destek teklifi; canlı ölçümde normal vakalarda izlenecek.

**Kaynak yorumu belirsiz (karar kaydı):**
- A26/A30 "too much": mevcut yorum, "too much" sonrası floor teklifinin deneme 1 olarak sayılması (tarih: bu haftanın son iş günü); deneme 2 floor+deadline. Gerekçe: A26 "Attempt 2 may name the floor again, on the deadline" ifadesi, too_much floor teklifinin deneme 1 konumunda olduğunu ima ediyor; PUB-06 bu yorumla n4–n6'da geçti ("minimum payment offered once"). Notlardaki "too_much ikna hakkını tüketmesin" önerisi uygulanmadı: aynı public davranışı bozma riski ve kaynak metnin bu yorumu desteklemesi. Testler: N T3, R E1–E3.
- A3/A45/A15 sayaç etkileşimleri, close_call retry (OpenAPI 500 tekrar edilebilir der; brief "exactly one close_call"): retry=0 korunuyor.
- B6 alt küme kapsamı ("ikisini cuma"): kaynakta tanımlı değil; mevcut davranış event kapsamına bağlı.
- A32 karma mesaj sırası: seçilen yorum "önce empati+destek teklifi, sonra müşterinin kendi önerisi" (tek soru/tur). Alternatif okuma (öneriyi hemen işlemek) iki soruyu aynı tura koyuyordu.

**Hâlâ açık (modelde kalan durumlu kurallar, known_gaps'te listeli):** A3 teyit sayacı, A6/A7 callback geçerliliği ve tekrar sayısı, A15 ret sayacı, A22 this/next eşlemesi (takvim tablosu destekli), A41/A42 transfer kararı ve "bir kez yardım teklifi", kimlik öncesi A45, transferin işlem sınırında guard'ı.

**Düşük öncelikli savunma önerileri (ertelendi, risk olarak kayıtlı):** ortak tarih kökeni (`len(scope)>1`), eski clamped bayrağı (yeniden açılan üründe sıfırlanıyor; yeni ortak/tekil teklif zinciri tam test edilmedi), `min(amt, full)` sessiz kırpma (read-back'te görünür), floor için 0.005 tolerans, para için float, aynı tutarlı ürünlerde practice kontrolünün zayıflığı, B1 kardinalite, `last4` zfill, callback sınır saatleri, kimlik/ret sayaçlarının koda alınması.
