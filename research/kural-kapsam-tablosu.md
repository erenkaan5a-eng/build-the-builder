# Atomik kural kapsam tablosu — Brief A (1–47) ve Brief B (1–11, Closing)

Tarih: 11 Ekim 2026, kod 32bd888 ve sonrası (`local-hardening`). Önceki tablo: `research/ab-kural-tablosu.md` (bulut, c8de7c9).
Kaynak: `briefs/brief-a.md`, `briefs/brief-b.md`, `tools/openapi.json`. Tasarım notları (`research/review/*`) yalnız öneri olarak okundu.

**Sütunlar.** Her satır bir atomik hükümdür. *Kaynak* = brief kural numarası (+alt hüküm harfi bu tabloya aittir). *Tetik → eylem* = koşul ve eylem; istisna/öncelik varsa köşeli parantezde. *API* = bağlandığı istek/yanıt alanı. *Uygulayan*: **K** = kod (dosya/düğüm), **M** = diyalog modeli (istem), **K+M** = model olayı çıkarır, kod karar verir, **B** = banka (API). *Kanıt*: yerel test kimliği (dosya: `I*` test_identity, `S*` test_identity yapısı, `H*` test_support, `N T*` test_negotiation, `R *` test_negotiation_regress, `D` test_date_tool, `G` test_generator_structure); canlı kanıt yalnız bu çalışmanın ölçülen adayıyla yazılır (`research/yerel-olcum.md`). *Durum*: U = kodla uygulanmış + yerel test; P = model/istem (kodla zorlanmıyor); A = açık; Y = yorum farkı kaydı.

Bir paragraf tek etiketle kapatılmadı: örneğin A32 yedi ayrı hükme bölündü. "Modelin hepsini çıkardım demesi" tamlık kanıtı sayılmadı: her satır kaynak cümleye bağlı; uygulayıcı satırı kodda/istemde gösterilebilir olmalı.

## Brief A

| # | Kaynak | Tetik → eylem [istisna/öncelik] | API | Uygulayan | Kanıt | Durum |
|---|---|---|---|---|---|---|
| A1a | 1 | ilk cümle: Freya Bank'tan dijital asistan | — | K: `opening` TTS (policy.opening_line, çıkarım) | build yapısal kontrolü "opening line spoken" | U (metin çıkarımdan) |
| A1b | 1 | ilk cümlede kayıt bildirimi | — | K: aynı TTS | aynı | U |
| A1c | 1 | kimlik doğrulanmadan "collections/debt/payment/ürün" yok, akraba dahil | — | K: kimlik aşamasının bütün cümleleri policy'den (identity.say), hesap/borç yalnız `security_verified` sonrası (DEAL_CODE kapısı); M: opening/third_party serbest metni | S2, S5 | U (kimlik aşaması) / P (açılış, üçüncü kişi) |
| A2 | 2 | "Am I speaking with {title} {last_name}?" | çağrı değişkenleri | K: opening TTS | yapısal | U |
| A3a | 3 | yalnız açık teyit sayılır | — | M: `speaker` çıkarımı | — | P |
| A3b | 3 | belirsizse bir kez daha sor; ikinciden sonra `not_reached/unclear` | close_call | M | — | A (sayaç kodda yok) |
| A3c | 3 | önce müşterinin sorusu (4, 43); sonraki soru ikinci sorudur | — | M | — | A |
| A4 | 4 | robot/AI sorusu → dijital asistan + devam | — | kimlikte K (policy robot_answer, I13); müzakerede M (answer alanı, rakam/soru içeremez H4); açılışta M | I13, H4c | U (kimlik) / P (diğer) |
| A5 | 5 | üçüncü kişiye neden aranıldığı söylenmez; ne zaman ulaşılır sorulur | — | M: third_party istemi; bu düğümde hesap/kimlik aracı yok | yapısal | P |
| A6a | 6 | geri arama: bugün veya sonraki iş günü, 10:00–19:00 dahil, `now`dan sonra | schedule_callback date,time | K: SETUP_CODE pencere metni; karar M | — | P (pencere hesabı K) |
| A6b | 6 | `schedule_callback` + `not_reached/callback` | schedule_callback, close_call | M | PUB-02 (eski aday) | P |
| A7 | 7 | pencere dışı → bir kez başka saat; yine dışı → kayıt yok, `not_reached/no_callback` | close_call | M | — | A |
| A8 | 8 | numara müşterinin değil → `not_reached/wrong_number` | close_call | M | — | P |
| A9 | 9 | vefat → "I am sorry for your loss.", başka soru yok, `not_reached/deceased` | close_call | M | — | P |
| A10 | 10 | akraba güvenlik sorusu cevaplayamaz, hesap bilgisi alamaz, ödeme teklif etse bile | — | K: üçüncü kişi düğümünde kimlik/hesap aracı yok; kimlik yalnız `speaker=self` ile | yapısal | U (yapı) / P (konuşma) |
| A11a | 11 | iki soru, birer birer: önce doğum tarihi, sonra telefon son 4 | verify_identity.field | K: identity runtime (policy.questions sırası) | I1, I5a | U |
| A11b | 11 | her cevapla `verify_identity` | verify_identity | K: motorun çalıştırdığı `id_verify` (tek tam cevap → tek çağrı) | I1, I3, S3 | U |
| A11c | 11 | doğum tarihi YYYY-MM-DD, nasıl söylenirse söylensin | answer | K+M: model parçaları rakama çevirir; kod birleştirir ve biçimler | I1, I2, I14 | U |
| A11d | 11 + API | okunamayan değer servisçe reddedilir (ok=false, yanlış sayılmaz) | ok | K: ok=false → aynı soru, sayaç yok; takvimde olmayan tarih bankaya gitmez | I7, I14c | U |
| A11e | 11 | yalnız rakamla verilen tarih gün-ay-yıl okunur | — | M: araç açıklaması (policy.answer_format); güvenlik ağı banka ipucu | I6 | P |
| A12a | 12 | yanlış cevap yeniden sorulabilir | — | K: aynı soru, parçalar temizlenir | I5a, I6c | U |
| A12b | 12 | toplam üç yanlış, hangi soruda olursa, kontrolü bitirir | wrong_answers_left | B sayar; K kalan=0'da kapatır (API alanı yoksa policy max_wrong) | I4, I5c | U |
| A13a | 13 | `hint: day_month_swapped` → ayı kelimeyle söylemesini iste | hint | K: hint_say; duyulan iki sayı saklanır, yalnız ay söylenirse tarih tamamlanır | I6a, I6b | U |
| A13b | 13 | bu tekrar yanlış sayılmaz | — | B + K (kod saymaz; bayat ipucu kalan hak düşmüşse ipucu sayılmaz) | I6a–c (iki motor modu) | U |
| A14a | 14 | üç yanlıştan sonra borç söylenmez | — | K: hesap yolu yalnız tam doğrulamayla | I4, S2, S5 | U |
| A14b | 14 | mobil uygulama veya şubeye yönlendir | — | K: identity.say.failed | I4 | U |
| A14c | 14 | `not_verified/failed` | close_call | K: yalnız bankanın güncel sonucuyla (kalan=0); modelin kapanış aracında `failed` yok | I4, I11d, S4 | U |
| A15a | 15 | cevap vermek istemiyor → bir kez "sorular hesabınızı korur" | — | K: decline_explain (bir kez) | I11a | U |
| A15b | 15 | yine reddediyor → `not_verified/declined` | close_call | K | I11b | U |
| A15c | 15 | cevap yerine "arama ne hakkında?" = ret | — | K+M: `asks_purpose` olayı; aynı mesajda cevap varsa sayılmaz | I11b, I11c | U (Y: "cevap yerine" ifadesi böyle okundu) |
| A15d | 15 | ikinci ret ya da ikinci böyle soru kapatır | — | K: policy.declines_to_close; sayım kimlik aşaması boyunca, araya giren cevap sayacı sıfırlamaz (bulut düzeltmesi; 8ccf94e'deki sıfırlama kaldırıldı) | I11b, I11f, I11h | U |
| A16 | 16 | iki soru geçince `get_account` | get_account | K: `fetch_account` yalnız `id_result`ten, `security_verified=yes` ve `id_flag=account` ile | S2 | U |
| A17a | 17 | tahsilat ekibinden, gecikmiş ödeme hakkında | — | K: DEAL_CODE debt_intro | practice kontrolü | U |
| A17b | 17 | ürün kelimeyle: "credit card ending 4821" / "personal loan" / "car loan" | products[].type, card_last4 | K: naming şablonu | practice kontrolü | U |
| A17c | 17 | gecikmiş tutar ve gün sayısı | past_due, days_late | K | practice kontrolü | U |
| A-tak | §7 | iş günü Pzt–Cum, tatiller hariç | — | K: policy.calendar | D | U |
| A18 | 18 | bant → deadline (12./7. iş günü) ve ikna hakkı (1/2) | days_late | K: DEAL_CODE add_bd, bands | N T2, D | U |
| A19 | 19 | söz tarihi bugün/sonrası, iş günü, deadline'ı aşmaz | create_promise.date | K: judge_date | D, N | U |
| A20a | 20 | hafta sonu/tatil (deadline içinde) → sonraki iş günü teklif | — | K | N T6 | U |
| A20b | 20 | gün deadline sonrası → kural 23 | — | K (sıra: after > not_bd) | N | U |
| A21a | 21 | belirsiz dönem → bir kez kesin gün sor | — | K (vague sayacı); "vague" sınıfı M | N T6 | U (K+M) |
| A21b | 21 | yine yok → deadline öner | — | K | N T6b | U |
| A22 | 22 | "next/this <weekday>" anlamı | — | K: CALENDAR tablosu; eşleme M | — | P/A |
| A23a | 23 | deadline sonrası tarih → en geç tarih deadline, onu öner | — | K | N T2c | U |
| A23b | 23 | deadline'ı reddetmek = düz ret | — | K | N | U |
| A24a | 24 | önce tam gecikmiş tutar | — | K | N | U |
| A24b | 24 | "ne kadar ödeyebilirsiniz?" asla | — | K (teklifleri kod üretir) + M yasağı; answer alanında soru düşer | H4a | U+P |
| A24c | 24 | her tutarı ajan önerir | — | K | N | U |
| A25 | 25 | floor: kartta minimum_payment, kredilerde instalment_amount | products[] alanları | K: policy.floor_field | spec_extract.validate | U |
| A26a | 26 | tam tutar fazla → floor bir kez + "kalan gecikmede kalır" | — | K | N T3, R E1 | U |
| A26b | 26 | floor reddi = düz ret | — | K | R E2 | U |
| A26c | 26 | deneme 2 floor'u deadline'da yeniden söyleyebilir | — | K: ladder | N T3 | U (Y: "too much" floor teklifi deneme 1 sayılır — bulut kararı korundu) |
| A27a | 27 | floor..tam arası tutar kabul | amount | K | N T5 | U |
| A27b | 27 | floor altı → kaydedilemez, floor bir kez | — | K | N T5 | U |
| A27c | 27 | floor kabul edilmezse düz ret | — | K | N | U |
| A28 | 28 | ilk soru "Can you make this payment today?" | — | K: first_ask_one | — | U |
| A29 | 29 | müşterinin tarih/tutarı asla ret değil | — | K: tur içi olay birleştirme | R E4 | U (sınıflandırma M) |
| A30a | 30 | düz ret/cevapsızlık bir ikna hakkı kullanır | — | K (sınıf M) | N T1 | U |
| A30b | 30 | tarih/tutarsız "bugün hayır" = düz ret | — | K | N | U |
| A30c | 30 | deneme 1: tam (too much sonrası floor) bu haftanın son iş günü (bugünse gelecek hafta) | — | K: ladder_offer | N T1 | U |
| A30d | 30 | deneme 2 (yalnız geç bant): floor, deadline | — | K | N T3 | U |
| A31a | 31 | haklar bitince dur → `no_promise/refused` | close_call | K | N | U |
| A31b | 31 | reddedilen teklif tekrarlanmaz | — | K: refused listesi | N T1 | U |
| A32a | 32 | hastalık/aile vefatı/iş kaybı → tek kısa empati cümlesi | — | K: HARDSHIP/ENGINE, policy say.hardship (tek sahip; answer o turda düşer) | R G1, H2a | U (algılama M) |
| A32b | 32 | ikna denemesi yok (kalıcı) | — | K: `hs` bayrağı | R G3, G9 | U |
| A32c | 32 | destek ekibine bağlamayı teklif et | — | K: aynı cümle | R G*, H1a | U |
| A32d | 32 | kabul → `transfer_to_agent(support)`, `transferred/support` | transfer_to_agent.queue | K: relay çıkarımı → `hs_accept` → motor transferi (policy.hardship_queue), FINISH kapanışı; M yedek yol | H3a–c, G | U (yerel) |
| A32e | 32 | ret → `no_promise/hardship` | close_call | K: relay çıkarımı → `hs_decline` (ENGINE sabit olay); o turda model konuşmaz | H1b, H1c, G | U (yerel) |
| A32f | 32 | öncelik: 30 ve 41'den önce | — | K: hardship rotası relay/negotiate'te model öncesi; zorluk sonrası ikna yok | G, R G* | U / P (zorluk sonrası yapılandırma isteğinin sınıfı M) |
| A32g | 32 | müşteri yine de tarih/tutar söylerse 7–8'e göre kaydet | — | K: aynı mesajdaki öneri saklanır, destek cevabından sonra işlenir; sonradan söylenen öneri işlenir | H2a–c, R G* | U (Y: destek teklifi öneriden önce; A32 teklifi zorunlu kılıyor, yeni adım icat edilmedi) |
| A33 | 33 | indirim/feragat/taksit planı/brief dışı şart yok | — | K: teklifleri kod üretir; destek reddinde indirim sorusuna policy no_terms cümlesi; answer alanında rakam/soru düşer | H1b, H4 | U+P |
| A34a | 34 | ürün, tutar, tarih geri okunur + "Do you confirm?" | — | K | N T7 | U |
| A34b | 34 | `create_promise` yalnız açık evetten sonra | create_promise | K: onay paketine bağlı kayıt | R B1–B3, X1 | U (evet sınıfı K+M) |
| A35 | 35 | geri okumada değişiklik → yeniden kontrol ve geri okuma | — | K | R A2–A4, B3 | U |
| A36a | 36 | ürün başına bir söz | — | K: REC_NEXT | R B4 | U |
| A36b | 36 | kayıtlı söz değiştirilemez; sorarsa mobil uygulama | — | M | — | P |
| A37a | 37 | "kaydedildi" yalnız ok:true sonrası | ok | K: FINISH | N T10, R H2 | U |
| A37b | 37 | başarısızsa bir kez daha dene | — | K: retries=1 (tek katman) | N T10b | U |
| A37c | 37 | yine başarısız → kaydedilemedi + `no_promise/service_error` | close_call | K | R H3 | U |
| A38 | 38 | kayıttan sonra SMS cümlesi | — | K: after_promise_sentence | N T18b | U |
| A39 | 39 | "zaten ödedim" → bir iş günü sürebilir; söz yok; `paid` | close_call | K (sınıf M) | N T13 | U+P |
| A40a | 40 | "borç benim değil/ürünüm yok" → tartışma yok, söz yok, `no_promise/dispute` | close_call | K (sınıf M) | N T13b | U+P |
| A40b | 40 | geçmişte kapandı/ödendi iddiası = itiraz | — | M (olay tanımı) | — | P |
| A41 | 41 | yeni plan/düşük taksit → `transfer_to_agent(restructuring)`, `transferred/restructuring` | transfer_to_agent | M: transfer kararı; K: kapanış eşlemesi | N T12, R C3 | P+U |
| A42a | 42 | insan isteği → bir kez "önce yardımcı olabilir miyim" | — | kimlikte K (policy.human_request.say) I12a; açılış/müzakerede M | I12a | U (kimlik) / P |
| A42b | 42 | ısrar → `general`, `transferred/human` | transfer_to_agent | kimlikte K (motor transferi) I12b; diğer aşamalarda M | I12b | U (kimlik) / P |
| A43 | 43 | "dolandırıcılık mı?" → müşteri hizmetleri numarasıyla doğrulayabilir, devam | — | kimlikte K (policy scam_answer); müzakerede M (answer alanı) | I13 benzeri | U (kimlik) / P |
| A44 | 44 | araçlardan cevaplanamayan soru → bilgi yok; uydurma yok | — | M (answer alanında rakam düşer) | H4b | P |
| A45a | 45 | iki kez "konuşmak istemiyorum" → `no_promise/refused` | close_call | K: ENGINE stop sayacı (policy) | R I1–I3 | U |
| A45b | 45 | doğrulamadan önce aynı müşteri → `not_verified/declined` | close_call | kimlikte K (stop = ret sayılır, I11); açılışta M | I11 | U (kimlik) / P (açılış) |
| A45c | 45 | kural 42 doğrulamadan önce ve sonra geçerli | — | A42 satırları | — | U/P |
| A46a | 46 | her çağrı tam bir `close_call` ile biter, son araç çağrısıdır | close_call | K: kimlik ve müzakere yolları (finish_say → notes → close_one); açılış/üçüncü kişi/wrap_up M | G zincir, R H9 | U / P |
| A46b | 46 | sonuç/gerekçe tablodan | outcome, reason | K kod yollarında; modelin kapanış aracına tablo gerekçeleri (identity failed hariç) enum olarak | S4 | U / P |
| A46c | 46 | kayıtlı sözden sonra transfer → `transferred` + o transferin gerekçesi | — | K: FINISH, CLOSE_PRE | R C3, H3b | U |
| A46d | 46 | Brief A `add_note` kullanmaz | — | K: uses_notes | G | U |
| A47 | 47 | `close_call`dan önce teşekkür ve veda | — | K: finish_say / preSpeech | — | U |

## Brief B

B, Brief A'nın bütün kurallarını devralır ("Every rule of Brief A applies unless a rule below replaces it"). **B'nin değiştirdikleri**: A17 tek ürün → B2 her ürün; A28 ilk soru → B4 hepsi için bugün; A30 sayaçları → B5 ürün başına; A34 geri okuma → B7 toplu; A46 tablosu + "add_note kullanmaz" → B8 notları ve B Closing. **Değişmeden devralınanlar**: kimlik (A11–15), açılış/üçüncü kişi (A1–10), tarih/tutar (A18–27), zorluk (A32), transferler (A41–42), A37 tekrar, A38, A45–47. Devralınan kimlik bileşeni A ile aynı koddur (I*, S* testleri A+B fikstüründe de koşar: S0–S6).

| # | Kaynak | Tetik → eylem [istisna/öncelik] | API | Uygulayan | Kanıt | Durum |
|---|---|---|---|---|---|---|
| B1 | 1 | 1–3 ürün, her biri kendi past_due/days_late/floor | get_account.products[] | K: DEAL_CODE düzleştirilmiş liste | G, N T1 | U (kardinalite denetimi yok: düşük risk) |
| B2 | 2 | her geç ürün, ürün başına bir cümle, bir şey istemeden önce | — | K: debt_say | practice kontrolü | U |
| B3 | 3 | bant ve deadline ürün başına | — | K | N T2/T2b | U |
| B4a | 4 | önce hepsini bugün ödeyebilir mi | — | K: first_ask_all | N T1 | U |
| B4b | 4 | değilse ürün ürün, get_account sırasıyla | — | K | R D1 | U |
| B4c | 4 | her ürün için "bugün" tekrar sorulmaz | — | K | R D1 | U |
| B4d | 4 | her ürün A30 deneme 1'den başlar | — | K | N T1 | U |
| B5 | 5 | ikna hakları ürün başına | — | K | N T1 | U |
| B6a | 6 | tek tarih bir ürünün deadline'ını aşarsa o ürün kendi deadline'ında; geri okumada söylenir | — | K: shared clamp + readback_clamped | N T2/T2b | U (Y: "tek tarih" = birden çok üründe kapsam) |
| B6b | 6 | diğer ürünler müşterinin tarihini korur | — | K | N T2 | U |
| B7a | 7 | bütün sözler birlikte geri okunur, tek onay | — | K: rb_pkg | R A5, B1, B2b | U |
| B7b | 7 | sonra ürün başına bir `create_promise` | create_promise | K: REC_NEXT | R A5 | U |
| B8 | 8 | sözsüz her ürüne `add_note(product_id, reason)`; hiç söz yoksa da | add_note | K: FINISH notları + NOTES_NEXT | N T1, R C1 | U |
| B9 | 9 | bir üründe itiraz/ödedim çağrıyı bitirmez | — | K | N T13b | U |
| B10a | 10 | yapılandırma isteği yine transfer (A41) | transfer_to_agent | M karar, K kapanış | R C3 | P+U |
| B10b | 10 | istekten önce kaydedilen sözler kalır | — | K | R C3 | U |
| B10c | 10 | anlaşılmış ama kaydedilmemiş sözler kaydedilmez | — | K: REC_NEXT transferred() engeli (motor transferi de dahil) | R H4, H5 | U |
| B10d | 10 | `transferred/restructuring` | close_call | K | R C3 | U |
| B10e | 10 | her transferde (restructuring, support, human) hiç not yok, öncesi/sonrası | add_note | K: FINISH transfer dalı | R C3, H3b | U |
| B11 | 11 | bir create_promise iki kez başarısız → diğer kayıtlar kalır, o ürüne `service_error` notu | add_note | K | N T11, R H1 | U |
| BC1 | Closing | söz yok + her ürün `paid` notlu → `paid` | close_call | K: FINISH | R C2 | U |
| BC2 | Closing | aksi hâlde `no_promise` + get_account sırasında ilk paid-olmayan notun gerekçesi | close_call | K | N T13b | U |
| BC3 | Closing | birden çok üründe en az bir kayıt → `promise` (kural 10 hariç) | close_call | K | R C3 | U |

## Önceki tablodan farklar (11 Ekim yerel)
- **Kimlik (A11–A15, A42/43/45 kimlik aşaması)**: P/A'dan U'ya. Önceki tabloda kimlik akışı modelde, `failed` kapanışı modelin seçimiydi; 881ea3a üretecinde S1–S4 başarısız (`research/local-evidence/structure-on-881ea3a.txt`).
- **A32d/e**: destek cevabı model turundan çıkarım+kod yönlendirmesine taşındı (PUB-05 1. tekrarındaki "Would you like to make a payment…" türü serbest konuşma o turda artık yok). 881ea3a'da S5 başarısız.
- **A46b**: `close_call.reason` API'de enum değil; modelin kapanış aracına policy'deki kapanış tablosundan gerekçe listesi verildi, kimlik `failed` hariç.
- Hâlâ açık/modelde: A3 sayaçları, A7, A22 eşlemesi, A36b, A40b sınıfı, A41 kararı, açılış ve müzakere aşamasındaki A42, A44.
- Canlı kanıt: bu tablonun "Kanıt" sütunu yerel testlerdir; canlı sonuçlar `research/yerel-olcum.md`.
