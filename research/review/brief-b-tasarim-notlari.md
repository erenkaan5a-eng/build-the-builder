# Brief B — biriken tasarım önerileri

Son inceleme: `freya-kapsamli-inceleme.md` ve `runtime-sonda-sonuclari.json`. Yerel motorda p1'e ait confirms olayı bütün agreed ürünlerin kayıt yolunu açtı; not kuyruğu başarılı banka yanıtı olmadan tüketildi; karma ilk yanıtta diğer ürün için today teklifi üretildi. İlk ikisi somut motor kontrol açıklarıdır, sonuncusu B4 bağlamıyla ayrıca değerlendirilmelidir. REC_NEXT/FINISH doğrudan giriş sondaları normal workflow'da aynı yolun yaşandığını kanıtlamaz; rapor bu ayrımı korur. Proje uygulaması değiştirilmedi.

Durum: çalışma notları; uygulanmış veya canlı test edilmiş kabul edilmez. 11 Ekim 2026. Bu belge kullanıcı Brief B'yi çalıştıkça güncellenecek. Brief A notlarını tekrar etmez; B'nin değiştirdiği hükümleri ve çok ürünlü bağlantıları inceler. Bankaya özgü sayılar/alanlar gelen brief ve API'den çıkarılır; generic builder'a sabitlenmez.

Kaynaklar: kullanıcının Ders 2.11 metni; briefs/brief-b.md; A'nın devralınan gizlilik ve borç açıklama hükümleri; güncel builder/components.py DEAL_CODE ve negotiate giriş davranışı; builder/spec_extract.py. Bu turda kod salt okunur incelendi; simülasyon veya uygulama değişikliği yapılmadı.

## Kapsam ve belge önceliği

B, A'yı bütünüyle geçersiz kılmaz. Builder her B değişikliğinin kapsamını ve hangi A hükmünü değiştirdiğini kaydetmeli. İlk iki değişiklik ürün sayısını 1–3 yapar ve ödeme görüşmesinden önce bütün gecikmiş ürünlerin ayrı cümlelerle açıklanmasını ister. Kimlik, gizlilik ve kaynaklı bilgi zorunluluğu devam eder.

Önemli: hesapta yalnız bir ürün bulunması, Brief B politikasını Brief A'ya dönüştürmez. B'nin daha sonra inceleyeceğimiz not ve kapanış hükümleri yine geçerlidir. Aktif politika modu ile o çağrının ürün sayısı ayrı tutulmalı; len(products)==1 sadece uygun tekil dil seçimi için kullanılabilir.

## Kurallar 1–2: çok ürünlü hesap ve eksiksiz açıklama

### Değerlendirme
Dersin normalize et → ürün başına cümle hazırla → hepsini açıkla yaklaşımı doğru. En büyük kazanım yeni framework değil, her ürünün kimliğini/verisini aynı zincirde korumak ve açıklama tamamlanmadan ödeme sorusuna geçmemektir. Döngüyle üç cümle yazmak tek başına yeterli değildir: veri kaybı, aynı türde ürünler, kesinti ve tek ürünlü B de sınanmalı.

### Kaynaklı gereksinimler
- get_account 1, 2 veya 3 ürün döndürebilir; her ürünün past_due, days_late ve floor'u kendisine aittir. Tam üç ürün varsayımı yok; ilk ürünü seçip kalanını atlamak yok.
- A'dan gelen kimlik doğrulaması tamamlanmadan hesap sorgusu ve borç açıklaması yapılmaz. Hazır cümleler ancak başarılı, güncel get_account yanıtı alındıktan sonra üretilebilir; görüşmenin başında müşteri borcu biliniyormuş gibi hazırlanmaz.
- Collections team/late payment bildirimi ve ürün adı, gecikmiş tutar, gün sayısı A'dan devralınır. B'de her gecikmiş ürün bir cümleyle açıklanır; bütün liste açıklanmadan normal ödeme sorusu sorulmaz.
- API sırası sonraki B 4 ve kapanış hükümleri için korunur. Toplama, tutara göre sıralama veya ürün türüne göre gruplama kaynak sırasının yerine geçmez.
- 'Before asking for anything' güvenlik sorularını borç açıklamasından sonraya taşıyan bir hüküm değildir; bu bölüm kimlikten sonraki borç açıklama/ödeme akışını değiştirir. İnsan talebi, gizlilik ve diğer üst kurallar kesinti halinde kaybolmaz.

### Ürün snapshot'ı ve durum temsili
Öneri: sıralı product_ids ve kimliğe göre ürün verisi; mevcut liste aynı işi güvenilir yapıyorsa ikinci kopya zorunlu değil. Her ürünün id, source_index, type, spoken_name, past_due, days_late, floor bilgisi birlikte korunur. Sonraki deadline/deneme ve kayıt durumu bu kimliğe bağlanır. Toplam borç yardımcı bilgi olabilir; ürünlerin yerini alamaz.

- Hesap yanıtının başarısını ve güncelliğini doğrula. API adı/alan eşlemesi doğrulanmış adaptörden gelir; farklı response biçimlerini tahminen birleştirme.
- Ürün sayısı politika aralığında olmalı. Sıfır/dörtten fazla ürün bu B kapsamı için hata; fazla ürünü sessizce kesme. Başka brief daha çok ürün destekliyorsa sınır config'ten değişir.
- Id boş veya tekrarlı olamaz. Aynı type'a sahip iki ürün meşrudur; type anahtarlı sözlükle birini diğerinin üzerine yazma.
- Gecikme günü tam sayı, tutarlar sonlu ve sözleşmenin hassasiyetine uygun olmalı. Floor doğru ürün alanından alınmalı; başka ürünün minimumu veya toplam tutar kullanılmamalı.
- Kart son dört hanesi metin olarak korunur. Kaynak '0042' ise '42' yapılmaz; kaynak gerçekten eksikse sessizce sıfır eklenerek tamamlanmaz. Yalnız platformun sayısal dönüştürme yaptığı kanıtlanırsa normalizasyon açık sözleşmeyle uygulanır.
- İki aynı tür ürünün müşteri ifadesiyle ayırt edilmesi gerekirse yalnız bankadan gelen özellikler kullanılır. Bankanın vermediği hesap numarası uydurulmaz; daha sonraki teklif kapsamı belirsizse hedef ürün açıklığa kavuşturulur. İç product_id müşteriye okunmaz.
- Bir ürün bozuksa onu listeden çıkarıp geri kalanı eksiksiz hesapmış gibi anlatma. İlk doğrulama tüm snapshot üzerinde; gerekli veri eksikliğinde kontrollü hata yolu ve bilinen eksik raporu. Yeni outcome/reason icat etme.

### Konuşma sözleşmesi
Kaynak ürün sırasıyla her ürün için bir kısa cümle üret: ürünün adı + past_due + days_late. Minimum, deadline, teknik kimlik ve sayaçları bu ilk açıklamaya gereksiz ekleme. Para birimi kaynakta yoksa ders örneğindeki doları evrenselleştirme; past_due'yu toplam hesap bakiyesi gibi adlandırma.

Metin üretimi deterministic olabilir; TTS/LLM sunumu platformda doğrulanır. Açıklama metnini oluşturmak 'bütün ürünler söylendi' kanıtı değildir. Normal kesintisiz yolda bütün ürün cümleleri ilk ödeme sorusundan önce gelmeli. Kural 4'ün toplu bugün sorusu sonraki bölümde ayrıntılandırılacak; burada yalnız bu soru için önkoşul kuruyoruz.

Kesinti yönetimi: müşteri ikinci ürün söylenmeden soru sorarsa kaynaklı kısa yanıt ve kalan açıklama; transfer veya açık terminal olay varsa borç listesini bitirmekte ısrar yok. Hangi cümlenin gerçekten sunulduğu gözlenemiyorsa kelime düzeyinde 'duyuldu' garantisi verme. Desteklenen en basit ilerleme kontrolü seçilsin; kullanıcıyı gereksiz tekrarlarla yormadan ödeme sorusunun erken sorulması engellensin. Sırf takibi kolaylaştırmak için bütün açıklamayı kesilemez yapma; konuşma kesintileri ayrıca test edilir.

### Mevcut uygulama: yeniden yazılmayacaklar ve açıklar
Olumlu bulgular: DEAL_CODE hesap ok alanını denetliyor; boş/tekrarlı id'yi reddediyor; kesirli days_late'i kontrol ediyor; isim alanları için Strict kullanıyor; ürünleri numeric kaynak indeksi sırasıyla okuyup products_json oluşturuyor. Her ürün için product_line üretilip debt_say'e ekleniyor. negotiate girişinde bu metin TTS ile kullanılıyor. A notlarının eski sürüme ait bazı hesap doğrulama eksikleri bu kodda artık kapatılmış; yeniden yapılacak iş diye alınmamalı.

Kalan kontrol noktaları:
1. DEAL_CODE'da ürün sayısının policy min/max aralığıyla kontrolü görünmüyor; yalnız boş liste reddi var. spec_extract'teki multi_product boolean tek başına tam cardinality sözleşmesi değildir.
2. last4 adını içeren kısa sayısal alanlara genel zfill uygulanıyor. Bu, kanıtlanmış normalizasyon mu yoksa eksik veriyi tamamlamak mı kontrol edilmeli; geçersiz hane/karakter uzunluğu da doğrulanmalı.
3. debt_say tek birleşik metin; first_ask ürün sayısıyla seçiliyor. Hazırlanan sıranın doğru olması olumlu, fakat kesinti sırasında tüm cümlelerin gerçekten sunulduğu kanıtlanmış değil.
4. Hata dalı deal_text/acct_state'i değiştiriyor ama eski products_json/debt_say'i açıkça temizlemiyor. Mevcut hata yönlendirmesi erişimi engelleyebilir; yeniden girişte eski snapshot'ın kullanılamadığı sınanmalı.
5. Flattened liste okumasında eski uzun yanıtın kalan indeksleri yeni kısa yanıta karışmamalı. İlk sorguda üç, sonraki sorguda bir ürün örneğiyle response güncelliği sınanmalı; gereksiz yeniden sorgu eklenmemeli.
6. Tutarlar float ve iki ondalık metin kullanıyor. A tutar notlarındaki tek hassasiyet düzeltmesiyle ele alınmalı; burada ikinci bağımsız para katmanı kurulmasın.
7. len(prods)==1 ile first_ask_one seçimi tek başına yanlış değildir; fakat aynı sayıya göre B not/sonuç/ikna politikası A'ya döndürülmemeli. Bu ayrım bir ürünlü B regresyonuyla kanıtlanmalı.

### Hedef testler
| Durum | Kabul ölçütü |
|---|---|
| B'de 1, 2 ve 3 ürün | İndeks hatası yok; gelen her ürün bir kez açıklanır |
| İki aynı type, farklı id/tutar/gün | Veri üstüne yazılmaz; ayrı cümle ve doğru kimlik bağları |
| API sırası değişir | Açıklama aynı yeni sırayı izler; id'ye ait tutar/gün değişmez |
| Kart 420/6/floor126, kredi780/21/floor260 | Rakamlar ürünler arasında taşınmaz; minimum past_due diye söylenmez |
| Eksik id, tekrarlı id, eksik kart hanesi veya floor | Sessiz ürün atlama/uydurma yok; doğrulama hatası |
| Sıfır/dört ürün | B'nin sınırı görünür uygulanır; ilk üçe kırpma yok |
| Kimlik kısmen doğrulanmış | get_account/borç açıklaması yok |
| ok=false ve önceki snapshot dolu | Eski ürünler açıklanmaz |
| Açıklamada müşteri araya girer | Uygun özel olay işlenir; normal devamda kalan ürünler atlanmaz |
| Üç ürünün kesintisiz açıklaması | İlk ödeme sorusu üçünün açıklamasından sonra |
| Aynı veride yalnız id/sıra değiştirilir | Karar public id veya ilk ürün ezberine bağlı değil |
| B tek ürün | Tekil dil mümkün; aktif B politikası korunur |

Yerel normalize/metin testleri ile canlı sunum testleri ayrı tutulur. Beklenen metin alanları snapshot'a göre bağımsız karşılaştırılır; aynı üreticinin çıktısı testin cevabı olarak kopyalanmaz. Transcript kontrolü ürün, tutar, gün ve ilk ödeme sorusunun sırasını birlikte ölçer. Sesin tam duyulduğu iddiası yalnız platform kanıtı varsa yapılır.

### Uygulama önceliği ve yarışma katkısı
1. Snapshot kimliği/sırası ve B tek ürün modunu koru.
2. Policy'den ürün sayısı ve eksik veri kontrollerini tamamla.
3. Tüm ürünler açıklandıktan sonra ödeme sorusuna geçildiğini platformda ölç.
4. Bu doğrulanmış snapshot'ı mevcut ürün başına müzakere/onay/kayıt motoruna aktar; yeni paralel mimari kurma.

PUB-13'te ürünlerin önce açıklanmaması ve tarihlerin karışması, borç açıklama ile ürün kimliği bağının neden önemli olduğunu gösteren önceki bulgulardı; yeni sürümün aynı hatayı yaptığı varsayılmaz. Mevcut test kampanyasına hedefli kontrol ekle; sırf bu belge oluştu diye bütün simülasyonları tekrar başlatma. Şampiyonluk katkısı yalnız daha iyi cümle değil, tüm ürünlerin görüşme boyunca doğru kimlikle taşınması ve gerekli açıklamanın atlanmamasıdır.

## Kurallar 3–5: ürün politikası, ortak ilk soru ve sıralı müzakere

11 Ekim 2026. Ders 2.12; Brief B 3–5 ve A 18/24–32; mevcut negotiation.py ürün seçimi/refuses/next_attempt akışı karşılaştırıldı. Kod veya simülasyon çalıştırılmadı; aşağıdaki açıklar statik inceleme bulgusudur. Yeni bir müzakere motoru kurmak yerine mevcut motor tamamlanmalı.

### Değerlendirme ve kritik düzeltme
Dersin ürün başına politika/durum ve tek dinamik müzakere akışı önerisi uygun. Fakat tek başına current_product_index artırmak yeterli değil: hangi ürünün neden tamamlandığı, müşterinin başka ürün için önceden verdiği teklif ve toplu sorunun hangi kapsamda reddedildiği tutulmalı. Mevcut sıralı ürün listesi ve ilk açık ürünü seçme yöntemi doğru davranıyorsa ayrıca index eklemek zorunlu değil.

Asıl ayrım: çağrı genelinde ödeme görüşmesinin aşaması; ürün başına band/deadline/ikna geçmişi; müşteri mesajının kapsadığı ürünler. Üçünü aynı sayaç veya 'all' niyetine sıkıştırma.

### Kaynak sözleşmesi
- Band ve deadline her ürünün kendi days_late değerinden, ortak çağrı now'ı ve banka takviminden hesaplanır. Müşterinin en yüksek gecikmesini veya en erken deadline'ını diğer ürünlere uygulama.
- Bütün ürünler açıklandıktan sonra hepsinin bugün ödenip ödenemeyeceği bir kez sorulur. Bu ilk soru ürün başına ikna adımı değildir.
- Hepsini bugün ödememe sonrasında çözümlenmemiş ürünler get_account sırasıyla ele alınır. Her üründe yeniden bugün sorusu yok; agent'ın ikna başlangıcı A kural 30 attempt 1'dir.
- Toplu olumsuz cevap, bütün ürünlerin haklarını bir anda tüketmez. Örneğin early p1/late p2 için başlangıçta (0,0); p1 attempt 1 sunulunca (1,0); p1 son reddinden sonra p2 attempt 1 sunulunca (1,1). p2'nin ikinci teklifi kendi deadline ve floor'uyladır.
- İlk soruya bütün ürünler için açık evet, doğrudan banka yazımı değil; tarih/tutar geçerliliği ve daha sonraki toplu read-back/onay yoludur. Bugün iş günü değilse ödeme tarihi kuralı hâlâ geçerli.
- 'Hayır, kartı cuma öderim' salt tüm ürünleri reddetmek değildir. A 29 sürer: müşterinin açık ürün/tarih/tutar önerisi doğrulanır, ek ikna olarak sayılmaz. 'Attempt 1' kuralı gönüllü uygun teklifi görmezden gelip yeniden teklif dayatmak için kullanılmaz.

### Temsil ve karar akışı
Çağrı durumu: aktif B politikası, account_order, all_today_question sunuldu bilgisi, collective_response ve ürün bazlı aşamaya geçildi bilgisi. Ürün durumu: id, band, deadline, floor/full, allowed/used, teklif geçmişi, pending offer, volunteered proposal, negotiation status. Bekleyen cevabın ürün kapsamı ve olay kimliği de tutulur.

1. Müşteri turundaki anlamları birlikte çıkar: hepsini bugün yapamama, belirtilen ürünler, gönüllü teklifler, affordability, hardship, paid/dispute ve transfer talebi. Aynı mesajdan hem toplu ret hem ürün teklifi çıkarsa önce teklif kapsamını çöz; körlemesine bütün ürünlere refuse uygulama.
2. Ürün bazlı moda geçişi çağrı seviyesinde kaydet. Bu bilgi, ancak ilk turdaki 'refuses all' olayından her ürünün initial_refused bayrağına yayılıyorsa karma cevaplarda eksik kalabilir.
3. Geçerli gönüllü öneriyi hedef üründe koru. Müşteri API sırasındaki ikinci ürün hakkında konuştu diye agent ilk çözümlenmemiş ürünü atlamasın; fakat açık ikinci ürün bilgisini de silmesin. İleride o ürüne gelindiğinde aynı bilgiyi gereksiz yere yeniden sorma veya üstüne full yazma.
4. Agent'ın bir sonraki ödeme teklifi, API sırasındaki ilk çözümlenmemiş ürün için olsun. Tek mesajda birden çok ürünün açık müşteri teklifini işlemek mümkündür; bu, agent'ın bütün ürünler için aynı anda ikna soruları sormasıyla aynı şey değildir.
5. Bir ürünün son ikna teklifi sunulmuş olması tamamlandığı anlamına gelmez; cevap beklenir. Kabul/uygun teklif, hak sonrası son ret veya ilgili özel sonuç ürünü müzakere açısından sonuçlandırır. agreed, recorded değildir.
6. Sonraki ürüne geçişte yalnız geçici çıkarım alanlarını temizle; o ürünün önceden verilmiş teklifini, kullanılmış haklarını veya çağrı genelindeki hardship/insan talebini sıfırlama. Geri dönülürse yeni hak yaratma.
7. Tüm ürünler müzakere açısından sonuçlandığında B 6–7'nin toplu onay aşamasına bağlan. İlk ürün agreed oldu diye hemen create_promise yapma. Transfer/terminal kuralları varsa sırayı zorla tamamlamaya çalışma.

### Ders önerisinde eksik kalan sınırlar
- can_pay_all_today=false ile 'hiçbir ürünü bugün ödeyemem' aynı kapsam değildir. 'Kartı bugün, krediyi cuma' ayrıntıları korunmalı. Eksik kapsam her ürüne bir ret olarak çoğaltılmamalı.
- can_pay_all_today=false tek başına 'tutarlar çok fazla' anlamına gelmez. Bir ürünün full-too-much bilgisi diğerlerine taşınmaz; genel affordability cümlesinin kapsamı ayrı çözümlenir.
- current_product_index kimlik değildir. Dizinin sırası saklanır ama banka argümanları product_id'den gelir. Aynı türde iki ürün varsa type ile indeks seçme.
- Aynı deadline'a sahip ürünlerde bile sayaçlar ayrı kalır. Yalnız mixed-band testleri yeterli değil; aynı band/farklı cevap dizileri de küresel sayaç hatasını yakalar.
- Düğümün yeniden girişi veya araç sonucunun tekrar işlenmesi yeni ikna hakkı tüketmez. Sunulmayan teklif ile tüketilmiş ladder adımı ayrımı A 28–33 notlarındaki ortak düzeltmeyle ele alınır.

### Güncel kodda hedefli kontrol noktaları
- Olumlu: ürünler ayrı deadline/allowed/used taşıyor ve active[0] seçimi kaynak liste sırasını kullanıyor. Bunları yeniden yazmak gerekmiyor.
- first_ask aşamasındaki refuses yalnız olay scope'undaki ürünlere initial_refused yazıyor. Sonrasında next_attempt seçimi bu bayrağa veya used>0'a bağlı; diğer açık ürünler full/today teklifine dönebiliyor. Karma ilk cevap sonrası her çözümlenmemiş üründe B'nin başlangıç adımının korunduğu sınanmalı.
- Ürün scope'u 'all' olduğunda refuses, first_ask dışındaysa listedeki birden çok open/offered ürün için refuse→next_attempt çağırabiliyor. Tek turda birden çok ikna teklifi ve hak tüketimi riski var. Ürünlerin hangi pending soruya gerçekten cevap verdiği kontrol edilmeli.
- Aktif ürün seçimi out boş olduğunda çalışıyor. paid/dispute gibi metin üreten olaydan sonra kalan ürüne nasıl devam edildiği ve gereksiz boş müşteri turu beklenip beklenmediği platformda ölçülmeli.
- len(products)>1 dil/named seçimi olarak kullanılabilir; B'nin tek ürünlü çağrısında politika değişmemeli. İlk toplu soru sonrası yine kural 30 başlangıcı ve B'nin daha sonraki not hükümleri korunmalı.
- next_attempt ve too_much sayaç riskleri A notlarında zaten var; bu bölümde ürünler arası izolasyon ve B 4 moda geçişi açısından test et, ayrı ikinci çözüm üretme.

### Hedefli test dizileri
| Dizi | Beklenen |
|---|---|
| now=14 Ekim, days_late 6/21 | İlgili ürünlerde 2 Kasım/23 Ekim; haklar 1/2 |
| days_late 7/8, ürün sırası ters | Bant sınırı doğru; kısa deadline diye sıra değişmez |
| Hepsine bugün hayır; early ilk teklife hayır | Late ürün attempt 1'e geçer; tekrar bugün sorusu yok |
| İlk ürün son teklifine evet | Cevap işlenir; hak doldu diye reddedilmiş sayılmaz |
| 'Hepsini değil, kartı cuma' | Kart önerisi korunur; diğer üründe yeniden bugün sorulmaz |
| 'Kart bugün, kredi cuma' | Her ürünün tarihi/tutarı ayrı; her ikisine bugün uygulanmaz |
| İkinci ürün için önceden teklif | Saklanır; agent müzakere sırasını keyfî değiştirmez |
| Üç ürün, aktif soruya 'hiçbirini yapamam' | Kapsam kaynaklı değerlendirilir; bir yanıtta bütün ladder teklifleri dökülmez |
| İlk ürün hakları biter; sonraki ürün aynı band | Sonraki ürünün hakkı etkilenmez |
| Ürüne geri dönüş / aynı olay tekrar işlenir | Sayaç sıfırlanmaz veya iki kez artmaz |
| İlk ürün paid/dispute, diğerleri açık | Ödeme talebi o ürüne dönmez; B sırasıyla devam |
| Hardship/insan talebi ürünler arasında | Çağrı genelindeki kısıtlar kaybolmaz |
| Tek ürünlü B | B politikası korunur; adım/sayaç tutarlı |

Yerel testte her tur sonrası bütün ürünlerin used/offer/status değerleri karşılaştırılır; yalnız final toplam başarıya bakılmaz. Ürün id ve sırası değiştirilerek aynı özellik yeniden sınanır. Gerçek metin→event çıkarımı ayrıca kontrol edilir. Sonra mevcut PUB-12 odaklı ve B regresyon ölçümüne katılır; yeni bir gereksiz tam simülasyon serisi başlatılmaz.

### Uygulama önceliği ve yarışma katkısı
İlk iş toplu ilk sorudan ürün bazlı moda geçişi açık hale getirmek; ikinci iş karma cevaplarda gönüllü teklifleri korumak ve agent'ın tek aktif ürün için soru sormasını sağlamak; üçüncü iş sayaç izolasyonu ve ürün değişiminde eski çıkarımların temizlenmesini doğrulamak. Tek müşteri için global en erken deadline veya global hak sayısı kullanılmamalı. Kazanım: tek üründe başarılı görünen motorun üç üründe sırasını, haklarını ve müşteri tekliflerini kaybetmesini önlemek.

## Kurallar 6–7: ortak tarih, ürün bazlı düzeltme ve tek toplu onay

11 Ekim 2026. Kaynaklar: Ders 2.13, Brief B 6–7 ve çapraz 8–11, A 19–23/34–38, güncel negotiation.py propose/ENGINE/CONFIRM/REC_NEXT. Yalnız statik inceleme yapıldı; kod değişikliği veya yeni canlı test yok. A 34–38 notlarındaki ortak kayıt guard'ını tamamlayan bölüm; ikinci bağımsız kayıt sistemi kurulmaz.

### Değerlendirme ve kapsam ayrımı
Dersin yönü doğru: tarih ürün bazında, onay bütün bekleyen vaatler için, banka isteği ürün başına. Üç kapsam ayrı tutulmalı. Mevcut motor ayrı agreed değerleri, toplu read-back ve sıralı kayıt içeriyor; sıfırdan normalizer/controller yazmak yerine eksik kapsam kontrolleri tamamlanmalı.

Kural 6 yalnız ortak tarihin deadline sonrası olması için özel davranış getirir. `min(requested_date, deadline)` eksiksiz tarih doğrulaması değildir: geçmiş, belirsiz dönem, hafta sonu ve tatil için A kuralları geçerlidir. Ortak tarih ifadesi, müşterinin bütün ürünler için aynı tutarı önerdiği anlamına da gelmez.

### Kaynak sözleşmesi
- Müşteri her şey için bir tarih önerdiğinde bu tarihi ürün başına değerlendir. Deadline'ı aşan ürün kendi deadline'ına çekilir, geçerli diğer ürünler istenen tarihi korur. Global en erken deadline'a bütün ürünleri çekme.
- Örnek: now=14 Ekim, kart deadline 2 Kasım, kredi deadline 23 Ekim, ortak istek 30 Ekim → kart 30 Ekim, kredi 23 Ekim. Her ürün kendi geçerli tutarını korur.
- Düzeltme read-back'te açıkça ilgili ürüne bağlanır. 'Tarih 23 oldu' gibi kapsamı belirsiz cümle yerine hangi ürünün hangi tarihte olduğunu belirt.
- Tarih düzeltmesi kayıt yetkisi değildir. B 7 ve A 34 gereği bütün vaatler birlikte okunur, tek açık onay alınır, sonra her ürün için ayrı create_promise çağrısı yapılır.
- Toplu liste bütün hesap ürünleri değil, teklif oluşturulmuş ürünlerdir. Paid/dispute/refused gibi sonuçlanmış ürünleri ödeme vaadi olarak ekleme. Sıfır vaat varsa boş paket onayı/kayıt yok; tek vaat kaldıysa tek öğeli paket mümkündür.
- Kayıtlar atomik değildir. Bir üründeki başarı diğer ürünün başarısı sayılmaz; izinli retry aynı onaylı ürün işlemini tekrarlar. Başarılı ürüne yeni promise oluşturulmaz.

### Ortak tarih kökeni ve ürün kapsamı
Müşteri ifadesinin tarih kapsamını açık tut: shared_request_id veya eşdeğer kaynak olay, requested_date_text, çözümlenmiş requested_date ve scope_product_ids. Bunlar örnek iç alanlar; platformun hazır alanları değildir. Her üründe resolved_date, deadline ve adjustment_reason (none/deadline/non-business-day vb.) ayrı tutulur.

- Aynı tarihin iki üründe bulunması tek başına 'her şey için tek tarih' kanıtı değildir. Müşteri iki ayrı teklif vermiş olabilir. Event'in hedeflediği ürün sayısından kural 6 tetikleyicisi türetilmemeli.
- 'İkisini cuma öderim' üç ürünlü hesapta hangi ikisi? Belirli bir alt küme için B 6'nın kapsamı kaynakta tam açıklanmıyorsa yorumu kaydet ve gerektiğinde kapsamı netleştir; otomatik tüm ürünlere yayma.
- Aynı ortak teklif model tarafından iki ayrı ürün event'ine bölündüyse ortak kaynak ilişkisi kaybolmamalı. Sırf tek event yerine iki event üretildi diye farklı banka politikası uygulanmamalı.
- Müşteri sonradan yalnız kredi için tarihi değiştirirse kartın tarihi aynı kalır. requested_date ve adjustment_reason güncel teklif sürümünden yeniden türetilir; eski 'deadline'a çekildi' bayrağı sonsuza kadar taşınmaz.
- Müşteri ortak tarih yerine vague dönem verirse önce kesin gün yolu; bir ürün için sorduğun açıklamayı bütün ürünler adına tekrar tekrar sorma. Ortak geçmiş tarih veya tatil için uygun A kuralı uygulanır.

### Tek toplu onayın sözleşmesi
Read-back ve banka istekleri aynı kanonik teklif listesinden üretilir: sıralı product_id, ürün adı, kesin tutar, ISO tarih ve açıklanacak tarih düzeltmesi. Her değişiklikte liste sürümü değişir, eski onay geçersizleşir. Metin oluşturuldu diye tamamının müşteriye sunulduğu varsayılmaz.

1. Onay olayı güncel read-back'e ve listenin tamamına ait olmalı. 'Sadece kartı onaylıyorum' için bütün paketin commit kapısı açılmaz.
2. Kısmi onay veya ürün çıkarma talebinde kalan ürünün niyeti netleştirilir; 'yalnız kart' ifadesi otomatik kredi için refused/not yazma yetkisi sayılmaz. Yeni vaat listesi gerekiyorsa tamamı tekrar okunur ve tek yeni onay alınır.
3. 'Yes, but change the loan date' tek bir değişiklik olayı olarak değerlendirilir; yes önce işlenmez. Müşteri bir alanı değiştirdiğinde diğer ürünler ve değişmeyen alanlar korunur.
4. 'Tek onay' konuşma boyunca yalnız bir onay sorusu sorulabilir demek değildir: değişiklik sonrası yeni paket yeniden onaylanmalıdır. Yasaklanan normal akış, her ürünü ayrı ayrı onaylayıp hemen yazmaktır.
5. Açık onay yalnız 'yes' metnine birebir eşleme değildir; bağlamdaki olumlu anlam gerekir. 'That's correct' uygun olabilir, 'maybe' veya koşullu onay yetmez. Sabit confidence=0.8 bir doğruluk garantisi değildir.
6. İki mevcut onay yolu aynı guard'a bağlanmalı: güncel ve tamamen sunulan liste + yeni açık tam onay + aynı snapshot + geçerli ürün/tutar/tarih + transfer/terminal engeli yok. Modelin serbest confirm etiketi tek başına bu şartları sağlamaz.
7. Commit başlarken liste sabitlenir. Ürün başına pending işlem ve sonuç ayrı tutulur; yalnız o listeye ait istek gönderilir. Başarılı kayıtlar geri alınmaz. Arada transfer veya değişiklik işlenebiliyorsa kalan kayıtlar için B 10/A 36 sınırları uygulanır; platform kesinti desteği varsayılmaz.

### Güncel kodda somut açıklar
- `shared = len(scope) > 1` ortak tarih semantiğini ürün sayısına bağlıyor. Scope'un küçülmesi veya çıkarımın iki event üretmesi aynı müşteri isteğinin farklı ele alınmasına neden olabilir. Ortak istek kökeni açık temsil edilmeli.
- `clamped=True` atanıyor fakat yeni geçerli teklifte sıfırlama görünmüyor; özgün requested_date de ürün durumunda saklanmıyor. Sonradan düzeltme değiştiğinde read-back yanlış gerekçe taşıyabilir.
- `typ == 'confirms'` dalı phase/readback sürümünü kontrol edip ürün scope'unu denetlemeden tüm akışı record yapıyor. Event yalnız p1'i hedefliyorsa bile diğer agreed ürünler yazılabilir. Bu kritik statik açık için doğrudan negatif test gerekir.
- `rb_version=version` read-back metni hazırlanırken atanıyor. Bu, müşterinin listeyi duyduğunun veya tam onay verdiğinin kanıtı değildir; A 34–38 ortak kontrolü uygulanmalı.
- REC_NEXT bütün agreed ürünleri seçiyor; ayrı confirmed snapshot kontrolü görünmüyor. 'Agreed' adı, müşterinin son toplu onayı yerine geçmemeli. Tarihi kural 6 ile düzeltilen ürünün hemen agreed işaretlenmesi, ancak bu ayrım kesin korunursa güvenli.
- Read-back sırasında değişiklik yolu ürünün agreed bilgisini temizliyor; A tutar notlarında belirtilen kısmi değişiklikte tarih/tutar kaybı burada bütün paketi bozabilir. Aynı düzeltme tek iş kalemi olarak yapılmalı.

### Hedef testler
| Senaryo | Beklenen |
|---|---|
| Ortak gün iki üründe geçerli | İkisinde istenen gün korunur |
| 30 Ekim: kart deadline 2 Kasım, kredi 23 Ekim | Kart 30, kredi 23; fark read-back'te; onaydan önce sıfır kayıt |
| Ortak gün tüm deadline'ları aşar | Her ürün kendi deadline'ı; global en erken güne çekme yok |
| Ortak 26 Ekim tatili, early/late ürün | Early için A tatil yolu, late için deadline yolu; aynı sonuç varsayılmaz |
| Aynı ortak istek bir event / bağlı iki event olarak gelir | Aynı politika sonucu; çıkarım paketleme şekli sonucu değiştirmez |
| Önce clamp, sonra müşteri geçerli yeni tarih verir | Eski adjustment bayrağı/açıklaması kalmaz |
| Tek ürüne ait confirms; 'yalnız kart' | Bütün paket için kayıt yetkisi yok |
| Yes + tarih/tutar değişikliği aynı mesaj | Eski veya onaysız yeni değer yazılmaz; yeni toplu read-back |
| Ürün listeden çıkarılır | Eski paket onayı geçersiz; belirsiz ürün sonucu uydurulmaz |
| İki ürün ayrı ayrı onaylatılıp hemen yazılır | B 7 ihlali olarak yakalanır |
| Toplu onay sonrası ilk ürün başarılı, ikinci pending | İkinci ürün başarılı sayılmaz; ilk ürün yeniden yazılmaz |
| Ürün id/sırası değiştirilir | Tarihler kimliğe bağlı kalır; read-back ve gerçek API gövdeleri eşleşir |
| Eski confirm_all yeni read-back'te kalır | Yeni müşteri onayı olmadan sıfır istek |

Üç kanıt birlikte ölçülmeli: müşteriye okunan ürün/tutar/tarih listesi, bu listeye ait yeni açık onay, bankaya gerçekten gönderilen ürün başına gövdeler ve sonuçlar. Yerel event testi, doğal dil çıkarımı testi ve canlı kayıt testi ayrı raporlanır. PUB-13 mevcut hedefli kampanyada kullanılır; public örneğin tarihleri/ürünleri runtime'a sabitlenmez.

### Öncelik ve yarışma katkısı
Önce kısmi onayın bütün paketi açmasını engelle; sonra ortak tarih kökenini ve ürün bazlı düzeltme bilgisini koru; ardından read-back→confirmed snapshot→API bağı için negatif testleri tamamla. Mevcut bileşenleri koruyarak yap. Bu bölümün puan katkısı yalnız doğru tarih hesaplamak değil, müşterinin duyup onayladığı farklı tarihlerin bankaya doğru ürünlerle ulaşmasını sağlamaktır.

## Kurallar 8–9: ürün sonuçları ve ertelenmiş banka notları

11 Ekim 2026. Ders 2.14 ve 2.15 birlikte değerlendirildi; Brief B 8–11, A 32/37/39–46 ve OpenAPI add_note sözleşmesi esas alındı. Mevcut FINISH/NOTES_NEXT/REC_NEXT için önceki statik bulgularla birleştirildi; yeni canlı test yapılmadı. Kod uygulanmış kabul edilmez.

### Değerlendirme ve sözleşme
Ürün sonucunu saklayıp banka notunu daha sonra göndermek doğru tercih; B 10 nedeniyle gerekli bir tasarım bağlantısıdır. 'Not adayı hazır' ile 'not başarıyla bankaya yazıldı' kesinlikle ayrı tutulmalı.

- Transfer olmayan, ürün sonuçları tamamlanmış akışta başarılı promise bulunmayan her ürün için kendi product_id ve kaynaklı nedeni ile not gerekir. Hiç promise yoksa da bu gereklilik sürer.
- Nedenler: refused, hardship, dispute, paid, service_error. Bu enum'a uymak tek başına yeterli değil: ilgili üründe nedeni destekleyen olay/sonuç olmalı. Henüz çözümlenmemiş ürünü otomatik refused veya service_error yapma.
- Paid/dispute tek ürünü sonuçlandırır; diğer ürünlere API sırasıyla devam edilir. Paid beyanı banka ödeme teyidi değildir. Geçmişte ürünün tamamen kapatılması iddiası dispute ayrımı korunur.
- Başarılı promise olan ürüne bu 'promise yok' notu yazılmaz. Sadece agreed/pending_confirmation olan ürün henüz başarılı değildir, fakat bundan otomatik not nedeni de çıkarılamaz.
- Ders örneğindeki endpoint yazımını sabitleme: gerçek URL OpenAPI server ve operation path eşlemesinden üretilir. İsteğe bağlı text alanına gereksiz serbest özet, güvenlik cevabı veya uydurulmuş bilgi koyma.

### Önerilen durum ayrımı
Ürün konuşma sonucu (paid/dispute/refused/hardship), promise işlem durumu (not_started/pending/recorded/failed/unknown) ve note işlem durumu (not_required/planned/in_flight/recorded/failed/unknown) birbirini ezmesin. Mevcut temsil bu ayrımları sağlayabiliyorsa yeni paralel state sistemi kurma.

Not planı yalnız ürün sonuçlarından türetilir; transfer kontrolü yapılmadan yürütülmez. Her not için id, neden, kaynak olay, gönderim durumu ve güncel yanıt eşleşmesi tutulur. Kuyruktan almak başarı değildir; başarı yalnız o notun ok=true sonucudur. Aynı node'da önceki ürünün ok değeri yeni ürüne uygulanamaz.

Normal tamamlanan ve transfer olmayan çağrıda ürün kapsam kontrolü: her bilinen ürün ya başarılı promise kümesinde ya gerekli başarılı not kümesinde bulunur; iki küme çakışmaz. Bu, uygulama/test invariant'ıdır; unresolved/unknown durumda sahte not yazarak denklemi sağlama. Yeni veya yabancı product_id yok, gereksiz mükerrer not yok. Notlar bilinçli olarak hâlâ planned ise ledger tamamlanmış sayılmaz.

Müşteri önceki beyanını not gönderilmeden düzeltirse güncel anlamı kaynakla değerlendir; eski geçici sonucu bankaya yazma. Not zaten gönderilmişse API'de geri alma aracı varmış gibi davranma. Bu nedenle notlar müzakere sırasında gönderilmez.

## Kurallar 10–11: transferde bekleyen işleri durdurma ve kısmi başarı

### Kaynak öncelikleri
- Uygun restructuring talebinde transfer yolu; A 32 hardship önceliği ve A 42 insan talebi süreci geçerliliğini korur. Her 'insan istiyorum' ifadesi anında tamamlanmış transfer değildir.
- Başarıyla kaydedilmiş promises korunur. Transfer yolunda henüz gönderilmemiş anlaşmalar kaydedilmez. Mevcut başarılı kayıtları yerel state'ten silmek bankadan iptal etmek değildir; böyle bir iptal yapılmaz.
- General, support veya restructuring transferi olan çağrıda transfer öncesinde de sonrasında da add_note yok. B 10, B 8/9/11'in not gereğini bu durumda geçersiz kılar. 'Önce service_error notunu yazıp sonra transfer' yanlış.
- Bir ürünün promise kaydı iki kez açıkça başarısızsa, transfer olmayan akışta o ürüne service_error notu; diğer başarılı promises korunur. Birinci hata ardından başarı varsa not yok. Bir ürünün hatası, kalan geçerli ve onaylı ürünlerin kayıt sürecini kendiliğinden iptal etmez.

### Transfer talebi, yönlendirme kararı ve başarı ayrı
Durum en az transfer_requested / transfer_authorized_or_pending / transfer_succeeded / failed_or_unknown ayrımını taşımalı. Kaynak koşullarını sağlayan transfer yoluna girildiğinde yeni promise/not gönderimi engellenir; transferred kapanış iddiası ise gerçek banka başarısına bağlıdır. Sadece ilk insan talebinde yardım teklif edilirken bütün süreci kalıcı iptal etmek doğru değildir.

Transfer API'si başarısız olursa 'başarılı transfer yok, o halde notları gönderelim' otomatik geri dönüşü yapılmaz. İstek hâlâ çözülmemiştir; ilgili hata davranışı kaynakta açık değilse bilinen eksik olarak tutulur. Yeni reason veya sınırsız transfer retry uydurulmaz.

Bekleyen ile gönderilmiş işlem ayrımı kritik: transfer geldiğinde henüz başlamamış kayıtlar durdurulabilir; bankaya gönderilmiş in_flight istek sırf yerel bayrak değişti diye iptal edilmiş olmaz. Geç gelen başarılı cevap gerçek kaydı yansıtmalı. API iptal/rollback veya atomik toplu işlem sağlamıyorsa böyle garanti verilmez. Kesinti hangi anda işlendi, hangi istek daha önce gönderildi izde görünür olmalı.

### Notları ertelemenin gerçek sınırı
Notları sona ertelemek gerekli ama tek başına 'gelecekte transfer olmayacağını' garanti etmez. Bir not gönderildikten sonra platform yeni müşteri transfer isteğini işleyebiliyorsa geriye dönük ihlal oluşabilir. Finalization sınırını ve platform kesinti davranışını test et. Sırf test geçsin diye insan talebini yok sayma veya kesintilerin desteklendiğini kanıtsız iddia etme. A 46–47 notlarındaki veda/not/close sırası değerlendirmesiyle tek tasarım kararı olarak ele al.

Her banka yazımından hemen önce uygunluk guard'ı çalışsın: ürün/teklif kimliği doğru, güncel onay mevcut (promise için), başarılı kayıt tekrarlanmıyor, transfer engeli yok, kapanış başlamamış. Daha önce hazırlanmış kuyruk bu guard'ı atlamasın. Not planı transferde silinse bile ürünün yerel dispute/paid geçmişi kanıt amacıyla korunabilir; bu add_note gönderme yetkisi değildir.

### Retry, sonuç ve not hatasının ayrımı
Promise retry ürün başına ve tek katmanda. İlk bilinen hata sonrası aynı onaylı gövde bir kez daha gönderilir; ikinci hatada durulur. Başarılı p1 yeniden denenmez; p2'nin sayacı p3'e taşınmaz. Sıra p1 fail-fail, p2 success veya p1 success, p2 fail-fail olsa da ürün bazlı sonuç aynı korunur.

HTTP 500 için OpenAPI kayıt yapılmadığını belirtir. Timeout/bozuk sonuç aynı kanıtı vermeyebilir; unknown iç durumunu doğrudan service_error notuna veya recorded'a çevirmek doğru değildir. Belirsiz sonucu çözmek için belgelenmemiş endpoint/idempotency özelliği ekleme.

add_note başarısızlığı, create_promise'in iki kez başarısız olmasıyla aynı değildir. Bu yüzden başarısız dispute notunun reason'ını service_error'a değiştirme. Not işleminin hata durumunu ayrı takip et; promise'e özgü retry sayısını add_note'a otomatik taşıma. Normal sonuç tamamlanmış gibi raporlamak yerine eksik ledger kaydını göster.

### Mevcut uygulamayla bağlantılı öncelikli kontroller
- FINISH notları yalnız başarılı transfer bayrağına göre bastırıyor. İlgili transfer pending/failed durumunda yazım engelinin ayrı korunup korunmadığı kontrol edilmeli.
- REC_NEXT ürünlere göre retry/result tutuyor; olumlu temel bu. Ancak yeni işlem öncesi transfer engeli ve güncel confirmed snapshot kontrolü önceki A/B notlarındaki ortak guard ile tamamlanmalı.
- NOTES_NEXT notu gönderimden önce listeden çıkarıyor; note_one sonrası güncel başarıya bağlı tamamlama aşaması önceki incelemede görünmüyordu. Gönderildi/başarıyla yazıldı ayrımı eksikse kapanışta not kaybı saklanabilir.
- FINISH'in open/offered→refused ve agreed→service_error dönüşümleri gerçek terminal kanıtıyla denetlenmeli. Eksik olay/teknik hatayı geçerli görünen müşteri sonucu yapmak yasak.
- Paid/dispute olayının başka ürünün pending teklifini veya recorded durumunu ezmemesi, tek ürünlü B'de de not kuralının sürmesi test edilmeli.
- Otomatik kayıt zincirindeki müşteri kesintileri gerçekten okunuyor mu? Kodda bayrak bulunması tek başına preemption'ın çalıştığı kanıtı değildir; küçük platform deneyi gerekir.

### Birleşik test matrisi
| Senaryo | Beklenen |
|---|---|
| p1 recorded, p2 dispute, p3 paid; transfer yok | Yalnız p2/p3 doğru notları; p1 yeniden kayıt/not yok |
| Hiç promise yok: refused/dispute/paid | Her ürün için ayrı doğru not; çözümlenmemiş ürün yok |
| p1 paid/dispute, p2 hâlâ açık | A'nın erken kapanışı yok; sıradaki ürüne devam |
| p2 ilk hata→başarı | Bir başarılı promise; service_error notu yok |
| p1 başarı, p2 hata→hata, p3 başarı | p1/p3 korunur, p2 notu; üçüncü deneme yok |
| p1 hata→hata, p2 başarı | İlk ürün hatası sonraki onaylı ürünü düşürmez |
| Aynı not olayı yeniden işlenir | Mükerrer yazım yok; önceki ürün cevabı yenisini başarılı yapmaz |
| Not ok=false | Başarılı not sayılmaz; nedeni otomatik service_error yapılmaz |
| Dispute/paid sonrası yetkili general/support/restructuring | Her üç transfer türünde sıfır add_note |
| Recorded p1, gönderilmemiş p2, fail-fail p3; transfer | p1 kalır; p2 yazılmaz; p3 dahil sıfır not |
| Onay alındıktan sonra, ilk istekten önce transfer | Hiç yeni promise gönderilmez |
| Bir istek in_flight iken transfer | Gönderim/cevap sırası korunur; sahte iptal veya yeni istek yok |
| Transfer aracı başarısız/unknown | Sahte transferred yok; not yolu otomatik açılmaz |
| Bir not yazıldıktan sonra transfer olayı | Sınır ihlali görünür; eski not yokmuş gibi raporlanmaz |
| Tek ürünlü B / aynı ürünlü A | B'de gereken not; A'da hiç add_note yok |

Yerel testler yalnız son state'i değil gerçek gönderim planını ve olay sırasını sınamalı. Mümkün platform kontrolleri ile sözlü iddia/banka sonucu karşılaştırılmalı. score.py ledger notlarını ürün id ve reason üzerinden karşılaştırır; bu kontrol başarı sırasını veya bütün kesinti davranışlarını tek başına kanıtlamaz. Mevcut B regresyon ölçümüne hedefli ekle; yeni gereksiz tam koşu serisi açma.

### Uygulama kararı
Öncelik 1: transfer kararı ile yeni promise/not gönderimi arasındaki guard. Öncelik 2: not başına güncel sonuç takibi ve mükerrer gönderim kontrolü. Öncelik 3: kısmi başarıda ürünleri koruma, unresolved/unknown'u sahte nihai nedene çevirmeme. Öncelik 4: platformdaki transfer-kayıt-not kesinti sınırı testi. Derslerde önerilen tracker/finalizer'lar ayrı framework değil, mevcut motorda tamamlanacak sorumluluklardır.

## Closing — ürün sonuçlarından görüşme sonucuna

11 Ekim 2026 ek değerlendirme. Kaynak: kit brief-b.md Closing ve kurallar 8–11; kullanıcının Ders 2.16 metni. Dersin öncelik sırası doğru. İçindeki Python örneği kesik olduğundan çalışır uygulama sayılmaz. Yeni bir framework kurmak yerine mevcut FINISH / NOTES_NEXT akışı tamamlanmalı.

### Kesin karar ve kapanışa hazır olma ayrı

Normal ürün işleme yolunda öncelik: başarılı transfer → transferred / ilgili reason; transfer yok ve en az bir başarılı promise → promise; hiç promise yok ve tüm ürünlerin paid notu var → paid; aksi halde get_account sırasındaki ilk non-paid ürünün not nedeni → no_promise / o neden. Promise ve paid için reason gönderilmez. Ürün sırası işleme sırası değişse bile orijinal banka sırasıdır. Kimlik ve ulaşılamama yolları kendi A kapanışlarını korur; boş ürün listesine all(paid) uygulayıp paid sonucu çıkarılmaz.

Bir recorded ürün bulunması nihai outcome adayını belirleyebilir; kalan ürünleri atlama yetkisi vermez. Normal kapanış için gerekli diğer ürün işlemleri de sonuçlanmalıdır. Agreed kayıt değildir; note kuyruğuna girmek veya gönderim yapmak başarılı note değildir. Transfer talebi, pending işlem ve başarılı transfer ayrı tutulur. Erken hesaplanan outcome, son yazımdan sonra değişen gerçek durumla yeniden doğrulanır.

### Mevcut motora eklenecek sorumluluklar

- Ürün başına müşteri sonucu, promise işlem sonucu ve note işlem sonucu ayrı tutulmalı. Alan isimleri öneridir: resolution, promise_status, note_status. Bunlar API'nin hazır alanları değildir.
- Note kuyruğundan çıkarılan öğe önce pending olur; o ürüne ve o gönderime ait yeni başarı kanıtı geldiğinde tamamlanır. Eski ürünün başarılı yanıtı yenisine taşınmaz. Hata/unknown görünür kalır.
- Open/offered durumlarını kapanışa ulaşıldı diye refused'a; agreed durumunu iki kayıt hatası kanıtı olmadan service_error'a çevirmek doğru değildir. Eksik akışı müşteri reddi gibi göstermemeli.
- Yeni promise/note öncesi transfer ve kapanış engeli, ürün kimliği ve güncel onay kontrol edilir. Başarıyla tamamlanmış işlem yeniden gönderilmez. B10–11 bölümündeki kesinti ve in-flight sınırları geçerlidir.
- Teşekkür ve veda close_call'dan önce olmalı; close_call son banka çağrısı olmalı. Close gönderimi ile başarılı kapanış kanıtı ayrı izlenmeli. Hata durumunda sınırsız döngü veya belgelenmemiş tekrar kuralı eklenmez; eksik kapanış dürüstçe raporlanır.
- Bir note hatası doğru kaydedilmiş promise'i silemez; dispute notu hatası kendiliğinden service_error müşteri nedenine dönüşmez. Süre sınırlı hata davranışı ayrı tasarlanır; başarısız ledger kaydı başarılı sayılmaz.

### Bu incelemede doğrulanan mevcut durum

Runtime FINISH ürün listesini sırayla dolaşıyor; başarılı transferi ve recorded promise'i önceleyerek doğru temel reducer'ı uyguluyor. Ancak outcome notlar gönderilmeden hesaplanıyor. NOTES_NEXT öğeyi gönderimden önce kuyruktan çıkarıyor ve note sonucunu kontrol etmiyor; components.py note_one koşulsuz sonraki nota, close_one koşulsuz hangup'a gidiyor. Bu nedenle 'notlar ve kapanış tamamen doğrulanmış' denemez. Bu statik bulgu, public B başarısını inkâr etmez; public vakalar bu hata yollarını kanıtlamaz.

### En değerli ek testler

| Durum | Beklenen |
|---|---|
| paid, dispute, refused | no_promise / dispute; orijinal sıra korunur |
| Aynı ürünler refused, paid, dispute banka sırasında | no_promise / refused |
| Bir recorded, diğerlerinde tamamlanmış notlar | promise; reason yok |
| Recorded var, başka ürün unresolved | Outcome adayı promise; normal kapanış henüz hazır değil |
| Bütün ürünlerde başarılı paid notları | paid; reason yok |
| Son paid notu başarısız/unknown | Tam ledger başarı iddiası yok; hata görünür |
| Recorded ardından başarılı transfer | transferred; mevcut kayıt korunur, hiçbir note yok |
| Transfer pending veya failed | Sahte transferred yok; otomatik note serbestliği yok |
| Erken not_verified / not_reached | Ürün reducer'ı çalışmaz |
| Aynı finalization olayı tekrar gelir | Mükerrer banka yazımı yok |

Testler yalnız outcome string'ini değil banka yazımlarının sırasını, ürün kimliklerini ve başarı kanıtını denetlemeli. Önce yerel sentetik test; yalnız platform davranışı belirsiz kalan nokta için küçük sonda. Bu bölüm uygulanmış veya canlı doğrulanmış değildir.

## Bölüm durumu
### Son kaynak/kod karşılaştırmasının kabul ölçütleri

Brief B'nin Closing metni ve mevcut FINISH/NOTES_NEXT kodu tekrar karşılaştırıldı. Öncelik algoritmasını baştan yazmak gerekmiyor; eksik olan işlem sonuçlarının kanıtıdır. İlk dar yerel testler şunları ayırmalı:

1. `paid → service_error → dispute` banka sırası, başarılı notlar ve sıfır promise ile `no_promise / service_error` üretir. Dersin son sorusunun cevabı B'dir.
2. Aynı ürün sonuçları farklı banka sırasıyla verildiğinde ilk non-paid neden buna göre değişir; işlem tamamlanma sırası kararı değiştirmez.
3. Note gönderimi başarısız/cevapsız kaldığında kuyruk boşalması ledger tamamlandı anlamına gelmez. Başarı kanıtı yalnız ilgili gönderime ait yanıtla oluşur.
4. Bir recorded ürün ile bir unresolved ürün birlikteyken promise outcome adayı korunur, fakat unresolved ürün otomatik refused/service_error yapılmaz.
5. Başarılı transfer, önceki promise'i silmeden transferred sonucunu seçer; not üretmez. Daha önce yanlışlıkla yazılmış notu sonuç önceliği düzeltemez; bu ayrı ihlaldir.

Bunlar yeni bir genel mimari talebi değildir. Önce mevcut testlerde eksik olan kontroller eklenmeli; yalnız başarısız olduğu gösterilen davranış düzeltilmelidir. Bu incelemede uygulama kodu değiştirilmedi ve yeni simülasyon çalıştırılmadı.

B 1–11 ve Closing tasarım değerlendirmesi tamamlandı. A'dan devralınan kurallar için brief-a-tasarim-notlari.md geçerlidir. Tasarım notlarının tamamı acil geliştirme listesi değildir: mevcut başarıyı koruyarak kaynakla çelişen ve ledger'ı etkileyen açıklar önceliklendirilir. Son uygulama karşılaştırması freya-son-durum-ve-oncelikler.md içindedir.
