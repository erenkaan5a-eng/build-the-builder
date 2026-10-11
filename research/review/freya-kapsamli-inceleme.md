# Freya: Claude uygulaması ile A/B notlarının kanıta dayalı karşılaştırması

11 Ekim 2026. Karar: mevcut mimariyi koru; bilgi kaybı, onay kapsamı ve desteklenmeyen politika davranışını düzelt. Public başarıyı genel kural uyumuyla karıştırma.

## Kapsam ve kanıt sınırı

Kullanıcının son Claude raporu; kit README, A/B brief'leri; builder/build.py, spec_extract.py, components.py, runtime/negotiation.py; behavior.py'nin kontrolleri; iki yerel test betiği; n6 ve F sonuç özetleri; A/B tasarım notlarının ilgili hükümleri incelendi. Test betikleri Python -B ile çalıştırıldı: ikisi de sıfır başarısızlıkla tamamlandı. Ek motor sondaları aynı test dosyasının Call/P yardımcılarını kullanıyor; bütün banka yanıtları yerel taklit, gerçek banka çağrısı yok.

Proje kodu değişmedi. env.sh okunmadı, Claude/Freya çağrısı ve yeni simülasyon yapılmadı. Bütün tarihî trace ve transcript'ler tek tek yeniden okunmadı; bulgular tüm görüşmelerin eksiksiz denetimi olarak sunulmamalı. Güncel yerel kaynak ile geçmişte yayınlanan ajanların kodunun birebir eşliği bu tur yeniden ispatlanmadı. Yerel sondalar güncel kaynak içindir; n6 skorları geçmiş adaylara aittir.

## Claude'un yaptığı işin anlamı

Ana yol artık tek model çağrısıyla brief/API'den policy çıkarıyor, sabit bileşenler workflow üretiyor. Görüşmede model müşterinin sözünü olaylara dönüştürüyor; müzakere motoru teklif, sayaç, tarih, ürün durumu ve yazım sırasını yönetiyor. TTS sabit borç, aktarım ve ilk kimlik sorusunu modelin yeniden yazmasını önlüyor. Bu doğru yönde bir ayrım; yeni bir framework veya tümüyle başka mimari gerekmiyor.

Modelin hâlâ yorum yaptığı yerler: müşterinin niyeti ve tarihinin çıkarımı, transfer, kimlik tekrar/ret/hint akışı, açılış teyidi, callback uygunluğu ve yan sorular. Kodun deterministik olması, modele yanlış/eksik olay verdirilemeyeceği anlamına gelmez. Üstelik doğru parçalı olaylarda bile aşağıdaki bilgi kayıpları görülebiliyor.

## Sonuçlar

| Dosya | Vaka başarısı | Koşular | Kanıt sınırı |
|---|---|---|---|
| cmp-a-n6-V.json | 9/10 vaka 3/3 | 29/30 | PUB-05 2/3 |
| cmp-ab-n6-V.json | 3/3 vaka 3/3 | 9/9 | Üç public B vakası |
| F-f1-A.json | 10/10 | Bir tekrar | Ayrı build, üç tekrarlı değil |
| F-f2-A.json | 10/10 | Bir tekrar | Ayrı build, üç tekrarlı değil |

PUB-05 logu iki sempati cümlesini açıkça bildiriyor. Bu kez bu gerekçe de logdan doğrulandı; bütün transcript yeniden okunmadı. Raporlanan F politika/yapı eşitliği bu tur yeniden hesaplanmadı, yalnız sonuçları doğrulandı. B bağımsız tekrar-build ve ham memo genellemesi için aynı kanıt yok.

## Yeni yerel sondalar: riskten somut örneğe

### 1. Kısmi onay bütün paketin kaydını açıyor — yüksek öncelik

İki ürün 16 Ekim için agreed/readback durumuna getirildi. Olay `product_id=p1, type=confirms` olduğunda motor record aşamasına geçti; yerel taklit yazım listesinde hem p1 300 hem p2 600 bulundu. ENGINE confirms dalı scope'u dikkate almıyor. A34 ve B7 açısından tam paket onayı ile tek ürün onayı ayrılmalı.

Bu, canlı müşterinin cümlesinin kesin bu olaya çevrileceği kanıtı değildir. Ancak motorun kabul ettiği anlamlı kısmi olayda güvenli sınır eksiktir. İki onay yolu aynı güncel paket/kapsam kontrolüne bağlanmalı; kısmi onay kalan ürünleri otomatik refused yapmamalı.

### 2. Yalnız tutar değişince tarih değişiyor — yüksek öncelik

16 Ekim için anlaşılmış üründe yalnız tutar 150'ye değiştirildi. Motor 150 için 14 Ekim (now) teklifi üretti. Müşteri tarihi değiştirmedi. A35 gereği değişmeyen tarih korunmalı; yeni tutar doğrulanıp paket tekrar okunmalı. Bu bulgu A24–27 ve B6–7 notlarımızdaki kısmi güncelleme kaybını doğruluyor.

### 3. Belirsiz tarihi açıklarken tutar unutuluyor — yüksek öncelik

300 borç/100 floor ürününde müşteri 150 ve belirsiz dönem önerdi; sonraki olay yalnız kesin 16 Ekim tarihiydi. Motor 150 yerine 300 agreed üretti. Teklifi parça parça söyleyen müşterinin önceki tutarı saklanmıyor. README'nin pieces/corrects/in_words koşullarıyla doğrudan ilişkili. Daha yüksek tutar kaydetmek başarı değildir; müşterinin taahhüdü korunmalıdır.

### 4. Not sonucu izlenmiyor — doğrulanmış yerel kontrol boşluğu

İki paid üründe FINISH outcome=paid hesapladı. NOTES_NEXT iki notu, hiçbir başarılı API yanıtı sağlanmadan sırayla tüketti. components.py note_one her durumda sonraki nota geçiyor. Kuyruk bitti diye başarılı ledger notları var denemez. Her gönderimin kendi sonucu izlenmeli; note hatası otomatik müşteri service_error nedeni olmamalı. Brief create_promise için retry tanımlıyor; bu kural add_note/close_call'a otomatik yayılmamalı.

### 5. Karma ilk yanıt ürün başına bugün sorusuna dönebiliyor — kaynak yorumuyla test edilmeli

İlk toplu soruya p1 için ileri tarih önerisi gelince p2 için full/today initial teklifi ve used=0 oluştu. B4, toplu bugün ödemesi olmayınca ürünlerin attempt 1'den başlamasını ve bugün sorusunun ürün başına tekrarlanmamasını söylüyor. Bu girdinin anlamı açık bir canlı/parçalı diyalogla sınanmalı; olayda diğer ürünlerin sessizce reddedildiği varsayılmamalı. Ama sıradaki üründe yeniden today teklifinin mevcut olduğu somut.

### 6. Yazım düğümünde son onay guard'ı yok — doğrudan giriş sondası

Henüz readback aşamasında REC_NEXT doğrudan çağrılınca agreed ürünler için yazım planladı. Normal workflow bu düğüme onaydan sonra yönlendiriyor; bu nedenle bunu normal yolda onaysız kayıt olmuş diye raporlamıyoruz. İşlem sınırında onaylanmış paket, phase ve transfer engeli denetlenirse yanlış geçiş veya gelecekteki değişiklikte ikinci koruma olur.

### 7. Erken finalization gerçeğe dayanmayan terminal nedenler üretiyor — doğrudan giriş sondası

Bir agreed ve bir açık üründe FINISH doğrudan çalıştırılınca ilkine service_error, ikincisine refused atadı; kayıt denemesi veya ret kanıtı yoktu. Normal akışın buraya hangi koşullarda ulaşabileceği ayrıca sınanmalı. Düzeltme doğru outcome adayını silmek değil, unresolved durumla normal kapanışın hazır olmadığını ayırmak.

## A/B notlarıyla hüküm tablosu

| Bölüm | Mevcut durum | Karar |
|---|---|---|
| A1–4 açılış | Model teyidi + sabit açılış | Public başarı var; iki belirsiz cevap ve araya soru dizileri notlardaki ek kapsam, bu tur doğrulanmadı |
| A5–10 callback | Kod pencereyi hesaplıyor, model uygunluğu seçiyor | Baştan yazma; sınır saati/geçmiş saat/iki geçersiz öneri hedefli test |
| A11–15 kimlik | İlk soru TTS, banka sonucu geçişe bağlı | Önemli ilerleme; sayaç/hint/ret hâlâ tam deterministik değil |
| A16–17, B1–2 | Hesap doğrulama ve sabit borç cümlesi | Claude'un yaklaşımı doğru; zfill kısa kart bilgisinin her durumda doğru olduğu kanıtı değil |
| A18–23, B3/B6 | Takvim/deadline kodda | 'Tarih tümüyle modele bırakılmış' eski eleştirisi artık geçersiz; doğal dil ve ortak tarih kökeni hâlâ ayrı risk |
| A24–27 | Tutar/floor motoru var | Kısmi alan ve açıklama turu kaybında notlarımız haklı; yerelde yeniden üretildi |
| A28–33, B4–5 | Ürün sayacı ve ladder var | Claude önemli kısmı uyguladı; karma ilk cevap ve hardship kalıcılığı ayrıca sınanmalı |
| A34–38, B7/B11 | Sürüm, toplu readback, kayıt/retry | Temel tasarım doğru; ürün kapsamı ve yazım sınırı eksik |
| A39–45, B8–10 | Paid/dispute motor, transfer model | Notları erteleme doğru; kayıt zinciri sırasında gelen transferin platformda yakalanması kanıtlanmadı |
| A46–47, B Closing | Başarılı transfer/recorded önceliği | Temel sıra doğru; note/close başarısı ve unresolved durum notlarımızdaki gibi ayrılmalı |

Notlarımız da mutlak doğru değil. Özellikle 'too_much floor teklifini ikna hakkından ayrı tut' yorumu ile Claude'un T3 testinin used=1 beklentisi çelişiyor. A26/29/30 birlikte ve konuşma bağlamıyla değerlendirilmelidir: salt düşük tutar açıklaması mı, yoksa bugün ödeme reddi + tutar itirazı mı? Public PUB-06'nın geçmesi tek yorumu evrensel yapmaz. Bir yorum değişikliğiyle çalışan yolu bozmadan, bu iki farklı anlam için kaynaklı ayrı örnek hazırlanmalı.

Diğer düşük/orta öncelikli statik riskler: shared=len(scope)>1 ortak isteğin kökenini kaybedebilir; clamped bayrağı yeni tekliften sonra eskimiş açıklama taşıyabilir; float toleransı ve sessiz üst tutar kırpma açıklığa kavuşturulmalı; hardship_handled tek başına ileride hiç ikna olmayacağını ispatlamaz. Hepsini aynı anda geliştirme listesine dönüştürme.

## Testlerin neden yeşil kaldığı

Mevcut testler yararlı, fakat çoğu doğru hazırlanmış olay ve başarılı sonuç taklidi kullanıyor. Call.finish yardımcısı bankadan not yanıtı beklemeden kuyruğu tüketiyor; bu yüzden not başarı takibi eksikliğini yakalayamaz. Kısmi onay, parçalı tutar+tarih ve yalnız bir alanı değiştirme kombinasyonları mevcut olumlu örneklerden farklı. 54/14 raporlanmış test sayısı kapsam garantisi değildir; test betikleri bu tur gerçekten yeniden çalıştırılıp sıfır hata verdi.

behavior.py'nin borç kontrolü ilk bulunan cümlede tutarların bulunmasına bakıyor. Test adı 'her ürün önce söylendi' dese de bu kontrol tek başına ürün adını, gecikme gününü ve bütün soru sırasını ispatlamıyor. Aynı tutarlı iki ürün özellikle zayıf nokta. Yerel test, platform sonda ve konuşma/ledger değerlendirmesi farklı kanıt katmanlarıdır.

## Final'e uyum: asıl stratejik açık

README açıkça başka kimlik soruları, takvimler, outcome tabloları, API alanları/değerleri ve ham mail/politika/memo girdileri bekliyor. Şema bazı değişiklikleri taşıyor; ancak deadline N iş günü, floor ürün alanı, ladder belirli menü ile sınırlı. Structural extra_rules ana yolu durduruyor; computational/stateful kurallar aynı sert kapıdan geçmiyor ve known_gaps içinde modele bırakıldığı yazıyor. Kodla çelişen prompt kuralı uygulanmış sayılmaz.

Burada iki uç da kötü: desteklenmeyen her şeyde hiç çıktı üretememek veya yanlış ajanı tam uyumlu saymak. Gerekli olan kaynak→kural→uygulama→test eşlemesi; desteklenmeyeni görünür sınıflandırma; sınırlı onarım ve gerçek kapsamı bilinen yedek yol. Eski fallback'in ana motor kadar iyi olduğunu varsayma; fakat alternatifsiz kapatma da.

Bir ham memo deneyi en az bir mevcut kuralı değiştirip eski kuralın uygulanmadığını göstermeli. Bir API eşleme deneyi mevcut kodda alan adını elle düzeltmeden, yeni sözleşmeden üretimi sınamalı. Her ikisi de dar hazırlanabilir; kapsamlı yeni benchmark kurmak gerekmiyor. Gizli brief açıldıktan sonra o brief'in kural/değerlerini builder koduna veya prompt'una elle eklemek README'ye aykırı; hazırlığın şimdi genel olması önemli.

## Teslim konusunda düzeltme

Claude'un 'teslim edilecek şey builder'ın kendisi' cümlesi eksik. Kit README: final brief başına üretilen/export edilen telefon ajanı dosyaları, kod ve ilgili run trace'i teslim edilir; puanlanan export'tur. GitHub/ilk 10 yeniden çalıştırma gibi ek gereksinimler için son organizatör talimatı ayrıca gerekebilir. Bu tur README_SUBMISSION.md bulunmadı ve submission dizini boş göründü; bu tek başına export'ların başka dizinde olmadığı anlamına gelmez.

## Önerilen aksiyon sırası

1. Başarılı adayı/source sürümünü koru; teslim manifesti ve temiz kurulum provasını hazırla. Yeni kodun eski n6 skorunu devralmadığını açık tut.
2. Parçalı bilgi koruma ve tam paket onayı için yeni negatif testleri önce ekle. Sonra mevcut motorda küçük düzeltme yap. Çalışan mimariyi değiştirme.
3. Not sonucu ve unresolved kapanış için ayrı işlem durumunu tamamla. Normal yol ile doğrudan düğüm giriş sondalarını raporda ayrı tut.
4. PUB-05 zorunlu empati cümlesini tek bileşen üretsin; modelin answer alanı aynı cümleyi çoğaltmasın. Hedefli üç tekrar, yalnız etkilenen komşular.
5. Tek ham memo ve dar API değişikliği deneyiyle destek kapsamını ölç. Başarısızlığı trace'e yazmakla yetinip destekli sayma. Yedek davranışını kapsamına göre düzenle.
6. Son sürümde doğrulama → yayın → gerekli davranış testi → export/hash ve teslim manifesti. Puan eşitliğinde yalnız geçen vakalardaki vaat tutarı, ardından build süresi ve erken teslim etkili; güvenilirliği düşürerek hızlı/tutarlı görünmeye çalışma.

Gecikme raporunda B'de en kötü tur 28 saniye; son koşularda müşteri kaybı olmaması bunun çözüldüğünü kanıtlamaz. Yeni geniş simülasyon serisi açmadan uzun turun hangi düğümden geldiğini mevcut trace'ten çıkar. Görüşme modelini değiştirmek README'ye göre seçenek değil.

## Eksik dosya gerekiyor mu?

Bu analiz için mevcut yerel kod, brief ve sonuçlar yeterliydi; tekrar yükleme gerekmiyor. Yalnız rapordan sonra başka bilgisayarda/oturumda değişiklik yapıldıysa o güncel sürüm ve sonuçları; son teslim yöntemini kesinleştirmek için kit dışındaki en son organizatör duyurusu gerekir. API anahtarı veya env.sh paylaşılmamalı.

Son hüküm: Claude'un ilerlemesi gerçek, notlarımızın bir kısmı uygulanmış, bir kısmı ek sondalarla doğrulanmış açıkları tarif ediyor, bir kısmı ise yorum veya henüz test edilmemiş savunma önerisi. Şampiyonluk garanti edilemez; en yüksek getirili yatırım şimdi motorun parçalı konuşmayı kayıpsız taşıması ve builder'ın değişen kuralları gerçekten uygulamasıdır.
