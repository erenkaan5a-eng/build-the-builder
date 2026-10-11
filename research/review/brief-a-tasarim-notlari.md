# Brief A — biriken tasarım önerileri

Son inceleme: `freya-kapsamli-inceleme.md` ve `runtime-sonda-sonuclari.json`. 11 Ekim yerel sondalarında yalnız tutar değişiminde tarihin bugüne dönmesi ve tarih açıklama turunda önerilen tutarın kaybolması yeniden üretildi. Bunlar artık yalnız statik şüphe değildir; canlı görülme sıklığı ölçülmedi. Notlardaki too_much/ikna sayacı yorumu ile mevcut test beklentisi arasında fark var; bağlamlı iki senaryoyla çözümlenmeden çalışan yol değiştirilmemeli. Mevcut testler yeniden çalıştırıldığında sıfır hata verdi; bu, yeni sınır durumlarının kapsandığı anlamına gelmez.

Durum: çalışma notları; uygulanmış veya canlı test edilmiş kabul edilmez. Kullanıcı brief'i çalıştıkça bu belge güncellenecek. Bankaya özgü değerler builder sabitleri değil, bu brief'ten çıkarılan örneklerdir. Kaynak: kit Brief A, ilgili numaralı kurallar. Eklenen araştırma metinleri öneri olarak değerlendirilir.

## Kurallar 1–4: açılış ve kişinin teyidi

Öneri: politika, görüşme durumu ve karar mantığını ayır.

- `party_confirmation.max_asks = 2`: kişinin kendisi olduğunun teyidi. Güvenlik sorularının yanlış cevap hakkıyla karıştırılmaz.
- Kabul edilen anlamlar: yes, that's me, speaking veya müşterinin kendi adı. Birebir kelime eşlemesi tek başına yeterli değildir.
- Durum: sorulan teyit sayısı, party_confirmed ve security_verified ayrı tutulur. Kişinin kendisini teyit etmesi hesap bilgisini açıklama yetkisi değildir.
- Sayaç düğüme girişte değil, ilgili soru gerçekten sorulduğunda artar; aynı olay yeniden işlenirse tekrar artmaz.
- İkinci sorudan sonra belirsizlik sürerse `not_reached / unclear`.
- Açılışta dijital asistan, banka ve çağrı kaydı bildirimi; güvenlik doğrulanmadan borç/ödeme/ürün bilgisi yok.
- Robot/AI sorusuna yanıt verilip devam edilir. Müşterinin sorusu yanıtlandıktan sonra tekrarlanan kişi teyidi ikinci soru sayılır.
- IR yalnızca prompt'a eklenmez; sayaç ve geçiş kararlarını runtime gerçekten bu politikadan üretir.

Durum: fikir olarak korunacak; mevcut stabilizasyon sırasında kontrollü biçimde uygulanabilir. Yeni genel derleyici yazma talimatı değildir.

## Kurallar 5–10: üçüncü kişi ve geri arama

Öneri: doğal dil çıkarımı → politika/durum kontrolü → doğrulanmış eylem. Bunun için düğüm sayısını gereksiz artırma; platformda davranışı ayrıca doğrula.

### Kaynak kurallar
- Üçüncü kişiye arama nedeni ve hesap bilgisi açıklanmaz; müşteriye ne zaman ulaşılabileceği sorulur.
- Yakını güvenlik sorularını yanıtlayamaz; ödeme teklif etmesi bu sınırı değiştirmez.
- Geri arama bugün veya sonraki iş günü, 10:00–19:00 dahil ve `now` anından kesinlikle sonra olmalıdır.
- İlk pencere dışı teklifte bir alternatif sorulur. İkinci pencere dışı teklifte schedule_callback çağrılmadan `not_reached / no_callback` kapanışı yapılır.
- Yanlış numara → `not_reached / wrong_number`.
- Vefat → "I am sorry for your loss."; başka soru yok; `not_reached / deceased`.
- Genel kapanış kuralları da geçerli: vedalaşma önce, close_call tam bir kez ve son banka tool çağrısı.

### IR ve durum önerisi
- Politika alanları: bilgi paylaşımı sınırı, kimlik/ödeme yasağı, callback gün seçenekleri, saat sınırları ve dahil olma bilgisi, strictly_after_now, yeniden sorma hakkı, outcome/reason eşlemeleri, zorunlu ifadeler.
- Durum alanları: third_party_confirmed, invalid_callback_offers, last_processed_offer_id, candidate_datetime, callback_validation ve gerçek callback sonucu.
- Eksik tarih/saat, gerçekten pencere dışı teklif ve API hatası ayrı olaylardır. Eksik bilgiye otomatik olarak geçersiz teklif cezası verme; brief'in belirtmediği davranışı varsayım olarak işaretle.
- Aynı teklifin tekrar işlenmesi sayacı ikinci kez artırmamalı. Aynı mesajdaki düzeltmeyi ayrı iki teklif saymamak için son açık teklif çözümlenmeli.
- Tarih ifadeleri yalnızca çağrıdaki now üzerinden çözülür; banka takvimi kullanılır.
- Callback başarıyla oluşturulmadan başarı iddiası yapılmaz. Hata sonrası retry/kapanış davranışı brief/API'den doğrulanır; ödeme sözü retry kuralı callback'e otomatik taşınmaz.

### Tasarımda dikkat
- Tek enum, "vefat etti ama yarın arayın" gibi çoklu sinyalleri kaybedebilir. Çıkarım ilgili olguları birlikte korusun; kod kaynak kurala göre karar versin.
- Vefat bildirimiyle callback teklifinin birlikte olduğu örnekte kural 9'un 'başka soru sorma' hükmü uygulanır. Bütün çelişkili sinyaller için evrensel deceased > wrong_number sıralaması henüz kabul edilmedi.
- Üçüncü kişi dalında verify_identity/get_account/create_promise bulunmaması koruma sağlar. Global yollar ve geçişler de incelenmeli; araçları gizlemek tek başına kanıt değildir.
- min_confidence=0.8 doğrulanmış eşik değildir. Düşük güven veya boş çıkarımda eski niyet/değerin yeni mesajda yanlış kullanılmasını engelle.
- Gönderilen metindeki Python örneği biçimsel olarak bozuk/eksik; doğrudan çalıştırılabilir kod kabul edilmez.
- Bugün tatil/hafta sonuysa callback için ayrı iş günü şartı otomatik ekleme: kural 6 'bugün veya sonraki iş günü' der. Ödeme tarihinin iş günü zorunluluğu başka kuraldır; yorum belirsizliği kaynakta görünür tutulur.

### Hedef testler
1. Yakın güvenlik cevabı veya ödeme teklif eder: hesap/kimlik/ödeme aracı çağrılmaz.
2. İlk geçersiz teklif → alternatif; ikinci geçersiz teklif → callback yok, doğru kapanış.
3. Eksik saat → açıklama istenir; sayaç sırf düğüme girildiği için artmaz.
4. 10:00 ve 19:00 sınırları; now ile eşit saat geçersiz; now'dan sonraki uygun saat geçerli.
5. Cuma, pazartesi tatil → sonraki iş günü salı.
6. Vefat + callback teklifi → taziye, yeni soru/callback yok.
7. Callback araç hatası → gerçekleşmeyen kaydı başarılı anlatma yok.
8. Bir mesajda düzeltilen teklif ve yeniden işlenen olay → çift sayaç artışı yok.

## Kurallar 11–15: güvenlik doğrulaması

Değerlendirme: önerinin görev dağılımı doğru ve mevcut kimlik döngüsüyle doğrudan ilgili. Öncelik yüksek; ancak iki ayrı güvenlik aşaması mutlaka çok sayıda Freya node'u gerektirmez. Çalışan platform bileşenleri korunarak uygulanmalı. Bu bölüm tasarım önerisidir; yeni uygulama/test yapılmadı.

### Kaynak kurallar ve API anlamları
- Önce doğum tarihi, sonra telefon son dört hanesi; tek tek sor ve her cevabı bankanın verify_identity aracıyla kontrol et. Doğru doğum tarihi, tam doğrulama değildir.
- Sayısal doğum tarihi gün–ay–yıl yorumlanır ve YYYY-MM-DD gönderilir. Son dört hane metin tutulur; baştaki sıfırlar korunur.
- Yanlış cevap hakkı sorular arasında ortaktır; başarılı ilk soru hakkı sıfırlamaz. Bu API'nin wrong_answers_left alanı mevcut olduğunda banka sayacı esas alınır.
- API ok=true: kontrol işlemi çalıştı. verified=true: ilgili cevap doğru. all_verified=true: tam doğrulama. Bu üç anlam birbirinin yerine geçmez.
- day_month_swapped: ayı kelimeyle söylemesini iste; bu açıklama tekrarını yanlış cevap sayma. Müşteri adına otomatik gün/ay değiştirip yeniden deneme yapma.
- Okunamayan tarih için ok=false, yanlış cevap sayılmaması OpenAPI açıklamasında belirtiliyor. Ancak her ok=false aynı biçim hatası değildir; servis hatası ayrıca ayrılmalı.
- Üç yanlışta mobil uygulama veya şubeye yönlendir, borç açıklama, not_verified/failed ile kapan.
- Güvenlik sorusuna cevap vermeyi reddetmede bir kez koruma amacını açıkla; devam eden rette not_verified/declined. Güvenlik cevabı yerine 'arama ne hakkında?' sorulması bu kapsamdadır; açılıştaki her soru otomatik ret değildir.

### Uygulanabilir temsil
- Politika: ordered_questions (alan, soru, normalizasyon), ortak yanlış cevap sınırı, özel ipucu davranışları, ret açıklaması ve sınırı, tam doğrulama koşulu, kapanış eşlemeleri. Mevcut sayılar/alanlar yalnızca Brief A örneğidir; builder'da sabitlenmez.
- Durum: active_question, question_already_asked, partial_answer, pending_request_id/field, last_processed_result_id, verified_fields, wrong_answers_left, protection_explanation_given, refusal_count, security_verified.
- Durum bilgisi çağrıya özeldir; yeni çağrı temiz başlar. Basit mevcut bir temsil bu kavramları karşılıyorsa ikinci bir durum sistemi ekleme.
- Model müşterinin ifadesini ve ret/soru/düzeltme ayrımını çıkarır. Kod biçimi ve sonraki adımı kontrol eder. Cevabın doğruluğuna sadece bankanın yanıtı karar verir.

### Önerilen karar sözleşmesi
1. Sonucu doğru çağrı ve bekleyen soruyla eşleştir. Eski/mükerrer sonucu ikinci kez işleme; yeni istekte eski sonuç bayrağı üzerinden yönlenme.
2. Yanıt zarfını ve belgelenen veri tiplerini normalize et. Python bool('false') kullanma: bu True verir. Eksik/bilinmeyen değer ayrı kalmalı.
3. Taşıma hatası/ok=false/bozuk yanıtı yanlış güvenlik cevabıyla karıştırma. Geçerli yanıt gelmeden sonraki soruya veya hesaba ilerleme.
4. Tutarlı güncel banka sonucunda tam doğrulama varsa security_verified durumunu aç; yalnız verified=true bunun için yetmez. Çelişkili yanıtı if sırasına göre rastgele başarıya çevirmek yerine hata olarak göster.
5. Geçerli day_month_swapped ipucunda açıklama yoluna git; kalan hakkı yerelde azaltma. İpucu ile tüketilmiş hak gibi çelişkilerde API sözleşmesini denetle.
6. Normal yanlış cevapta bankanın kalan hakkına göre aynı soruyu tekrar sor veya failed ile kapat. Geçilmiş soruya dönme.
7. Mevcut soru doğru ama tüm süreç tamamlanmadıysa bir sonraki soruya geç. Ret yolunu yanlış cevap sayacından bağımsız yönet.

### Gerçek fark yaratabilecek ayrıntılar
- **V6 regresyonunu önle:** self-transition olan soru düğümlerinde giriş davranışı tekrar tekrar ilk soruyu başlatmasın. on_enter_first_entry_only veya eşdeğer açık durum mantığı, gerçek konuşmayla doğrulansın. Müşterinin cevap vermesi ilerleme üretmeli.
- **Parçalı cevap:** 'four four' ardından 'seven one' geldiğinde eksik iki haneyi tam cevap diye doğrulatma. Tamamlanan '4471' tek cevap olarak gönderilsin.
- **Düzeltme:** aynı mesajdaki '4821, sorry 4721' son açık cevap olarak işlenir; bir kullanıcı cevabı için gereksiz iki banka çağrısı yapılmaz.
- **Ay açıklaması:** 'April' tek başına her zaman tam tarih değildir. Önceki tarih parçalarıyla tek anlamlı biçimde tamamlanabiliyorsa kullan; aksi hâlde tarihi ayı kelimeyle tam söylet. Örnekteki 03/04 ve swapped ipucuna dayanarak doğum tarihini tahmin etme.
- **Geçmiş sonuç:** isteğe ait olmayan all_verified/hint değerlerinin değişkenlerde kalması başarı veya tekrar döngüsü üretmesin.
- **Ret bağlamı:** 'neden soruyorsunuz?' ile 'arama ne hakkında?' veya açık ret otomatik olarak aynı kabul edilmesin. Hem cevap hem soru içeren ifadeler ayrı sınır vakasıdır; kaynakta olmayan ret politikası icat edilmez.
- **Araç sınırı:** kimlik aşamasında get_account erişimi kapalı olsun; hesap düğümüne tüm girişler tam doğrulama koşulunu taşısın. Bankanın kendi reddetme mekanizması, yanlış çağrıyı yarışmada doğru davranış yapmaz.
- **İletişim:** araç kısıtı, modelin konuşmada bilgi uydurmasını tek başına engellemez. Kimlik öncesi prompt/bağlamda borç bilgisi bulunmamalı; konuşma ayrıca kontrol edilmeli.
- **Üst kurallar:** insan temsilci isteği, robot sorusu ve konuşmayı reddetme gibi doğrulama sırasında geçerli diğer brief kuralları iki ayrı soru node'u içinde kaybolmasın.

### İlk uygulanacak test grubu
1. Doğru DOB → yalnız telefon sorusu → doğru telefon → get_account; soru döngüsü yok.
2. DOB doğru, telefon yanlış: yalnız telefon tekrar sorulur; ilk soru yeniden başlamaz.
3. DOB'de iki yanlış + telefonda bir yanlış: toplam hak biter, get_account yok, failed kapanışı.
4. Gün/ay ipucu ve ay açıklaması: yanlış hak azalmaz; sonuçtan sonra ilerleme var.
5. Okunamayan tarih, servis hatası ve eksik yanıt: birbirinden ayrılır, sahte doğrulama yok.
6. İlk ret → açıklama; ikinci ret/soru → declined. Yeni node'a geçmek açıklama hakkını sıfırlamaz.
7. Başında sıfır olan ve iki turda tamamlanan telefon cevabı; tek doğru API argümanı.
8. Eski/tekrarlı API sonucu ve yeniden node'a giriş: çift işlem/sayaç artışı yok.

Ölçüm: yalnız son mesaj değil; soru sırası, tool field/answer, güncel banka sonucu, geçiş ve final outcome birlikte incelenir. Önce yerel karar testleri ve küçük platform entegrasyonu; sonra ilgili public vakalar ve üç tekrar. Yerel mock başarısı canlı uçtan uca başarı diye sunulmaz.

### Maliyet ve uygulama kararı
İlk kazanım: mevcut kimlik bileşeninde tekrarlı giriş hatasını önlemek ve doğrulama sonucunu açık durumlara bağlamak. Bütün kimlik sistemini veya workflow'u sıfırdan yeniden üretmek gerekmiyor. Ayrı DOB/phone node'ları bir seçenek; esas kabul ölçütü doğru sıra, güncel banka kanıtı ve doğru hata davranışı. Yeni düğümler yalnızca bu kontrolleri basitleştirip ölçülen gecikmeyi kabul edilebilir tuttuğunda eklenir.

## Kurallar 16–17: hesabı alma ve borcu açıklama

11 Ekim 2026 değerlendirmesi. Kaynaklar: briefs/brief-a.md §6, briefs/brief-b.md değişiklik 1–7, tools/openapi.json, docs/tools-and-code.md (pre_actions, response_mapping, flattened variables), builder/components.py. Yalnızca belge ve kod incelendi; bu bölümün eklenmesi uygulama veya canlı doğrulama değildir.

### Karar ve mevcut uygulama
Önerilen doğrulama kapısı → otomatik hesap sorgusu → veri doğrulama → borç açıklaması yaklaşımı uygun. Ancak ilk iki parçayı sıfırdan yazmayacağız: mevcut identity geçişi all_verified alanına bakıyor ve hesap api_request düğümü get_account'ı pre_actions ile zaten çağırıyor. DEAL_CODE ürünleri düzleştirilmiş yanıttan okuyup products_json ve deal_text hazırlıyor. Yeni yatırım, bu bağlantıların doğrulanması ve hazırlanan verinin konuşma/işlem boyunca korunması olmalı.

Statik incelemede görülen açıklar:
- Kimlikten hesaba geçiş doğrudan all_verified alanını denetliyor; güncel yanıtın işlem başarısı ve tutarlılığını aynı kapıda sağladığını ayrıca kanıtlamak gerekiyor.
- DEAL_CODE, hesap yanıtının ok alanını açıkça denetlemiyor. Gerekli sayısal alanları okuyabilmek, başarılı ve güncel hesap sorgusunun kanıtı değildir.
- Eksik ürün kimliği str(None) ile "None" olabiliyor; isim şablonundaki eksik değer Safe ile boş kalabiliyor. Böyle veri sessizce kullanılmamalı.
- int(float(days_late)) kesirli günü sessizce tam sayıya indiriyor. float para için kullanılıyor; sonlu değer ve şema doğrulaması açık olmalı.
- deal_text model için hesap gerçekleri sağlıyor; müşteriye gerekli bilgilerin eksiksiz söylendiğini garanti etmiyor. Özellikle B'de bütün ürünler ilk ödeme sorusundan önce açıklanmalı.

### Uygulanacak veri sözleşmesi
1. Tam doğrulama yalnız bu çağrının güncel ve geçerli banka sonucundan gelir. ok/verified/all_verified ayrılır; platformun belgelenen string boolean değerleri normalize edilir. Ham platform değerine doğrudan `is True` uygulamak string "true" başarısını kaçırabilir; bool("false") da yasaktır.
2. get_account müşteri kimliğini çağrı değişkeninden alır; model yeni customer_id üretmez. Hesap düğümüne bütün girişler ve olası yeniden girişler denetlenir. Yeniden giriş aynı sorguyu gereksiz çalıştırmamalı; kontrollü retry ayrı konudur.
3. Başarısız/yeni sorguda önceki ürün snapshot'ı geçerliymiş gibi kullanılmaz. Yeni çağrı temiz başlar; yanıt ile müşteri/çağrı ilişkisi korunur. API'nin döndürmediği request_id alanı varmış gibi varsayılmaz; gerekiyorsa yerel çağrı sürümü tutulur.
4. Tek doğrulanmış adaptör yanıtı normalize eder. Mevcut çalışan flattened okuma rastgele mapping ile değiştirilmez. data.products mapping'i belge örneğidir; liste/JSON/flattened biçimlerinden hangisinin gerçekten geldiği küçük entegrasyonla doğrulanır. Desteklenmeyen biçim görünür hatadır.
5. Her üründe boş olmayan benzersiz id, kaynak sırası, desteklenen tür, ad şablonunun gereken alanları, sonlu tutar ve tam sayı gecikme günü doğrulanır. Kart son dört hanesi dört ASCII rakamdan oluşan metindir; baştaki sıfırlar korunur. Telefon son dört hanesiyle karıştırılmaz.
6. Tutarın hassasiyeti API/brief sözleşmesine göre korunur; mümkünse Decimal veya belirlenmiş alt birim kullanılır. Sıfır/negatif değer ve ürün sayısı için keyfî banka kuralı icat edilmez: brief kapsamı ve şema uygulanır, kapsam dışı veri raporlanır. Boolean sayısal tutar olarak kabul edilmez.
7. A'da tek ürün sınırı A politikasına aittir; genel runtime'a len(products)==1 gömülmez. B'de 1–3 ürün ve API sırası korunur; tür veya tutara göre yeniden sıralama yok. Aynı türden iki ürün id ile ayrılır.

### Konuşma ve müzakereye aktarım
- Kaynak hesap snapshot'ı ile müzakere durumu ayrılır. Bankadan gelen past_due değişmez; müşteri teklifi ayrı alandadır. Floor, past_due yerine açıklanmaz; 'past-due amount', bütün bakiye diye sunulmaz.
- Kaynaklı ürün adı + past_due + days_late üzerinden müşteriye okunacak kısa borç cümlesi hazırlanır. Collections team ve late payment bildirimi kimlikten sonra yapılır. Para birimi brief/API'de yoksa dolar varsayılmaz.
- İç product_id, deneme hakkı ve teknik hata alanları müşteri cümlesine karıştırılmaz. Runtime'ın hesap gerçekleri ile müşteriye söylenecek metin ayrı tutulur.
- A'da ürün açıklamasından sonra kural 28; B'de her ürün bir cümleyle açıklanır, ardından topluca bugün ödeme sorusu. Ürün başına yeniden bugün sorulmaz.
- Metni hazırlamak ile söylemek ayrı olaylardır. 'debt_stated' bayrağı metin üretildi diye açılmaz. Platformda gerçek asistan mesajı/akış sırası üzerinden doğrulanır; kesinti varsa söylenmeyen ürünler atlanmaz. Hardship/transfer gibi üst kurallar kesinti sırasında kaybolmaz.
- Sabit/metin-temelli çıktı destekleniyorsa kısa borç açıklaması için değerlendir; destek veya değişken çözümleme doğrulanmadan özellik varsayma. LLM okuyorsa transcript ürün/tutar/gün eksiksizliğini test et. Hazırlanan cümle tek başına garanti değildir.
- Eksik/başarısız veriyle borç açıklama veya ödeme kaydı yok. Brief'in hesap sorgusu hatası için belirtmediği kapanış reason'ı 'resmî kural' gibi icat etme. Mevcut fallback'in dayanağını ve belirsizliğini kaydet; API'nin kabul etmesi politika uygunluğu kanıtı değildir.

### Kabul kontrolleri
1. DOB doğru/all_verified=false → hesap sorgusu ve borç açıklaması yok; tam doğrulama → doğru customer_id ile sorgu.
2. ok=false ama eski ürün değişkenleri dolu → eski hesap kullanılmaz. Yeni çağrıda önceki müşterinin bilgisi yok.
3. Kart '0042', telefon '9876' → müşteri kart 0042 duyar; id ve haneler karışmaz.
4. Eksik/tekrarlı id, eksik kart hanesi, bilinmeyen tür, NaN/Infinity, kesirli gün → görünür doğrulama hatası; sessiz düzeltme veya uydurma yok.
5. B'de farklı tutar/gün ve aynı türden ürünler → API sırası ve her ürünün bilgisi korunur; ilk ödeme sorusundan önce hepsi açıklanır.
6. Hesap gerçeği → söylenen borç → onaylanan teklif → gönderilen kayıt zinciri ürün id'siyle izlenebilir. Onaylanan teklif hesabın orijinal tutarını değiştirmez.

Öncelik: çalışan hesap çağrısını koru; küçük veri doğrulama açıklarını kapat; B'nin borç açıklama sırasını ve teklif-kayıt bağını müzakere düzeltmesiyle birlikte tamamla. Yeni genel framework veya uzun araştırma turu gerekmiyor. Bu kontroller puanı artırmaya yönelik önerilerdir; kazanma garantisi değildir.

## Kurallar 18–23: tarih anlamı, banka takvimi ve kayıt sınırı

11 Ekim 2026. Kaynak karşılaştırması: kullanıcının Ders 2.6 metni, briefs/brief-a.md kurallar 18–23 ve 29–35, briefs/brief-b.md değişiklik 3/6/7, builder/runtime/date_tool.py ve tests/test_date_tool.py. Statik inceleme yapıldı; bu notla runtime değiştirilmedi, test veya canlı simülasyon çalıştırılmadı.

### Değerlendirme ve öncelik
Önerinin ana yönü doğru: model tarih ifadesinin anlamını çıkarır; kod takvim hesabını ve politika kararını verir; kayıt yalnız doğrulanmış ve onaylanmış değerleri kullanır. Mevcut tarih yardımcısını yeniden yazmak yerine doğal dil girdisi, konuşma durumu ve kayıt katmanıyla bağlantısı tamamlanmalı. Yerel doğru tarih hesabı, doğru görüşme veya banka kaydı demek değildir: PUB-13'te iki ürün için doğru karar üretilmesine rağmen model tarihleri karıştırdı.

Dersin bazı Python blokları kesik/bitişik metin; çalıştırılabilir üretim kodu olarak kopyalanmaz. Yerleşik date extraction'ın belirsiz ifadeyi nasıl çözdüğüne ilişkin iddia bu incelemede canlı doğrulanmadı. Tasarım, doğrulanmamış platform davranışına bağımlı olmayacak.

### Kaynak kuralların kesin karşılığı
- Tek zaman referansı çağrıdaki now; bilgisayar saati, modelin bildiği bugün veya testin çalıştırıldığı gün kullanılmaz. now yok/bozuksa sessizce gerçek saate dönülmez.
- A'da pazartesi–cuma iş günü, brief'teki tatiller hariç. Deadline hesabında bugün sayılmaz; sonraki ilk iş günü 1'dir. days_late 1–7 → 12 iş günü; 8–45 → 7 iş günü. Sınırlar dahil.
- Geçerli ödeme tarihi: today <= date <= deadline VE iş günü. Bugün tatilse 'bugün' otomatik geçerli değildir. Bu ödeme kuralı callback kurallarına taşınmaz.
- Kesin tarihte önce geçmiş mi, sonra deadline sonrası mı kontrol edilir; deadline içindeki iş günü olmayan gün için sonraki iş günü önerilir. Deadline sonrası tatili ileri yuvarlama: doğrudan deadline öner. Örnek: now=2026-10-14, late band, müşteri 24 Ekim der → 23 Ekim; 27 Ekim değil.
- 'This weekday' içinde bulunulan takvim haftası, 'next weekday' sonraki takvim haftasıdır. This Monday geçmişe düşerse kendiliğinden gelecek pazartesiye çevrilmez.
- 'Next week', 'end of the month', 'when my salary comes' kesin gün değildir. Bir kez kesin gün sorulur; müşteri hâlâ vermiyorsa deadline önerilir. Öneri, kabul veya kayıt anlamına gelmez.
- Tarih önerisi ret değildir. A'da önerilen deadline'ın açıkça reddi kural 30'a bağlanır; otomatik kapanış veya iki kez sayaç tüketimi yapılmaz. Retle birlikte başka tarih/tutar içeren cevap önce ilgili kurallar açısından çözülür.
- A, geçmiş tarih için hangi yeni tarihin teklif edileceğini 18–23'te açıkça belirlemiyor. Geçersizliği kesin; yeniden açıklama isteme gibi seçilen davranış uygulama varsayımı olarak kaydedilir, kaynak hüküm diye sunulmaz.

### Mevcut kodda korunanlar ve açıklar
Korunacak: date_tool.py today değerini now'dan alıyor; iş günü sayımında bugünü hariç tutuyor; deadline sonrası kontrolünü tatil kontrolünden önce yapıyor. Mevcut test dosyası ISO tarihleri, tatili, sınır tarihini, iki ürün deadline'ını ve ardışık vague girdilerini kapsıyor. 'This/next Friday' anlam çözümlemesi testlerde doğrudan sınanmıyor; bu testlerin geçmesi doğal dil tarih yorumlamasının kanıtı değil.

Statik bulgular:
1. ISO biçimine uymayan her girdi, açık 'vague' olmasa bile belirsizlik sayacına giriyor. Boş/bozuk araç argümanı veya çıkarım hatası, müşterinin ikinci belirsiz cevabı sayılmamalı. ISO gibi görünen ama imkânsız gün ayrı exception yoluna gidiyor; hata sınıfları açıklaştırılmalı.
2. date_vague_count her tool çağrısında artıyor; açıklama sorusunun gerçekten sorulmasına ve yeni müşteri cevabına bağlı değil. Mükerrer araç çağrısı ikinci cevap gibi davranabilir.
3. Sayaç anahtarı ürün id'sindeki noktalama işaretlerini '_' yapıyor. p-1 ile p_1 çakışabilir. Orijinal id ile anahtarlanan bir JSON durum sözlüğü gibi kayıpsız temsil kullanılmalı.
4. Bilinmeyen product_id, hesapta tek ürün varsa sessizce o ürüne çevriliyor. Gönderilmiş yanlış id başarısız olmalı; yalnız eksik id için tek üründen çıkarım desteklenecekse bu ayrı ve açık bir sözleşme olmalı.
5. date_product/date_proposed/date_decision tek son sonuç olarak tutuluyor. Bunlar aktarım için kalabilir; iki ürünün doğrulanmış tarihlerini ve teklif sürümünü saklamanın yerini tutmaz.
6. load_products fallback'i genel 'products.<index>.<field>' son eklerini tarıyor. Farklı veya eski yanıt köklerini karıştırmamalı; 16–17'deki güncel, normalize edilmiş hesap snapshot'ı esas alınmalı.
7. Hesap bileşeniyle tarih yardımcısı takvim/deadline hesabını ayrı tutuyor. İki hesap yolunun aynı policy ve aynı now ile aynı sonucu verdiği kontrol edilmeli; uygun yerde küçük ortak saf fonksiyon kullanılabilir. Büyük yeniden tasarım şart değil.
8. Tarih aracı açıklaması müşterinin her tarih ifadesinde çağrılmasını söylüyor. Aynı mesajdaki hardship/transfer gibi öncelikli olaylar sırf tarih de içeriyor diye bastırılmamalı. Tarih relay'inin her kararı zorunlu okuması bu yollarla birlikte sınanmalı.

### Önerilen sözleşme: ifade → karar → teklif → onay → kayıt
Çıkarım, sonucu baştan ISO olarak tahmin etmek yerine anlamı korusun: raw_text, tarih türü (exact_date / weekday_relative / vague_period / unparsed), this/next, weekday, açık tarih parçaları ve hedef ürünler. Bunlar önerilen iç alanlar; mevcut temsil aynı işi yapıyorsa ikincisini ekleme.

- This/next için ISO'yu kod hesaplasın. Eksik ay/yıl, çelişen gün adı ve takvim tarihi, 'this coming Friday' gibi brief'te tanımlanmamış ifadeler keyfî eş anlamlı yapılmasın. Belirsizlik ve bağlam birlikte değerlendirilip gerekli açıklama istensin. DOB'nin gün–ay–yıl kuralı ödeme tarihine otomatik taşınmasın.
- Vague period ile anlaşılamayan/eksik araç girdisi farklı durumlar olsun. Kesin gün sorma hakkı; bekleyen soru, ilgili ürün kapsamı, sorunun iletilmesi ve sonraki müşteri cevabıyla izlenmeli. Yinelenen olay hakkı tüketmesin. Sayaç node'a yeniden girildi diye sıfırlanmasın.
- B'de ortak belirsiz dönem için aynı müşteriye her ürün adına aynı açıklama sorusunu tekrarlama. Ortak teklifin kapsamını koru. Yeni bir teklif dizisinde hakkın sıfırlanma koşulu kaynakta açık değilse varsayımı kaydet ve sınırsız yeniden sorma döngüsü yaratma.
- Karar çıktısı en az ürün id, giriş olayı/teklif sürümü, istenen tarih, çözümlenmiş tarih, deadline, durum ve uygulanan kuralı taşısın. 'Geçerli' karar müşteri onayı değildir. Önerilen alternatif, müşteri kabul edip gerekli read-back onayını vermeden yazılamaz.
- B'nin ortak tarih istisnası: her ürün için ayrı deadline uygulanır, uygun ürünün tarihi korunur. B 6–7 gereği düzeltilmiş ürün tarihlerini tek toplu read-back'te belirtip bir onay al; A'daki ayrı deadline teklif görüşmesini her ürüne zorunlu ekleme. Toplu onay alınmadan kayıt yok.
- create_promise modelin yeniden yazdığı tarih yerine onaylanan teklifin saklanan tarihini kullansın. İşlem sınırında ürün/sürüm/tarih eşleşmesi ve geçerlilik tekrar kontrol edilir; uyuşmazlıkta sessizce farklı tarihe düzeltip yazma, yeniden onay yoluna dön.
- Kayıt sınırı kontrolü, aynı belirsizlik sayacını yeniden artıran konuşma fonksiyonu olmamalı. Saf tarih doğrulama ile konuşma durumu güncellemesini ayır.

### Politika ve yapılandırma kontrolü
İş günü tanımı, tatiller, bantlar, gün sayısı, this/next anlamı ve açıklama hakkı kaynaklı policy değerleri olsun. Brief A sabitleri genel builder koduna gömülmesin; üretilen adayın config'inde bulunmaları normaldir. Çakışan bant, kapsam dışı days_late, imkânsız tatil tarihi, negatif gün sayısı ve hiç iş günü olmayan takvim görünür hatadır; ilk bant sessizce seçilmez. Takvim döngülerinin yapılandırma hatasında sonsuza gitmesini önle. Genel motorun desteklemediği yeni kuralı mevcut şemaya zorlayarak başarı sayma.

### Puan kaybını hedefleyen test paketi
Önce yerel testler; beklenen değerler runtime fonksiyonundan yeniden hesaplanmaz, brief'ten bağımsız çıkarılır.

| Senaryo | Beklenen |
|---|---|
| now=14 Ekim 2026, days_late=7 / 8 | Deadline sırasıyla 2 Kasım / 23 Ekim |
| days_late=1 ve 45; kapsam dışı/kesirli değer | Dahil sınırlar doğru; kapsam dışı sessiz banda sokulmaz |
| Deadline günü / ertesi gün | İlk gün geçerli; sonraki gün deadline önerisi |
| 26 Ekim, early band / late band | Early: 27 Ekim öner; late: 23 Ekim öner |
| 24 Ekim, late band | 27'ye yuvarlama yok; 23 Ekim |
| Bugün iş günü / bugün tatil; geçmiş this Monday | İş günü şartı korunur; geçmiş gün geleceğe kaydırılmaz |
| This/next Friday; now cuma ve pazar; ay/yıl geçişi | İçinde olunan/sonraki takvim haftası semantiği |
| Aynı metin, farklı now; makine saati farklı | Sonuç yalnız çağrıdaki now'a bağlı |
| İki gerçek vague cevap | Bir açıklama sorusu, sonra deadline önerisi |
| Aynı vague olay tekrar işlenir; boş argüman | İkinci müşteri cevabı sayılmaz |
| p-1 ve p_1; tek üründe yanlış id | Durumlar çakışmaz; yanlış ürün sessizce seçilmez |
| Ortak 30 Ekim, early kart ve late kredi | Kart 30, kredi 23; tek toplu onaydan sonra ayrı doğru kayıt |
| Ürün sırası/id/tutarı değiştirilmiş aynı örnek | Karar konuma veya public id'ye değil ürün politikasına bağlı |
| Tarih onaydan sonra değişir; eski tool sonucu gelir | Eski onay/sonuçla yazma yok |
| Geçerli tarih + hardship/transfer aynı mesajda | Tarih yardımcı akışı üst kuralı bastırmaz |

Canlı kontrol sırası: anlam çıkarımı→tarih kararı→müşteriye söylenen teklif→onay→gerçek banka argümanı. Önce PUB-07 ve PUB-13 ile ilgili küçük kontroller, ardından mevcut regresyon programı. ISO girişli yerel test, tarih aracının kendiliğinden çağrıldığı veya doğru tarihin kaydedildiği kanıtı diye raporlanmaz. Mevcut toplam test planıyla birleştir; aynı vakaları iki ayrı plan yüzünden gereksiz tekrarlama.

### Uygulamaya aktarım kararı
En yüksek öncelik: onaylanan ürün-tarih listesini kayıt sınırına bağlamak; sonra yanlış ürün/vague olay ayrımını düzeltmek ve this/next anlamını kodla çözmek. Çalışan takvim aritmetiğini koru. Yeni düğüm ve model çağrısı sayısını yalnız gerekiyorsa artır; tarih kontrolünün gereksiz tekrarları konuşma gecikmesini büyütmesin. Bu bölüm Claude'un hesap/müzakere devam planına tamamlayıcıdır, ikinci bir bağımsız mimari değildir.

## Kurallar 24–27: tutar, minimum teklif ve teklif geçmişi

11 Ekim 2026. Kaynaklar: kullanıcının Ders 2.7 metni; Brief A 24–27, ilgili 29–36; Brief B ürün başına politika ve toplu onay hükümleri; mevcut builder/components.py ve builder/runtime/negotiation.py. Bu ek belge değerlendirmesidir; kod değiştirilmedi, yeni canlı test yapılmadı.

### Güncellik ve karar
Kod incelemesi sırasında yeni negotiation.py mevcut: ürün başına full/floor, teklif geçmişi, ikna sayacı, agreed durumları ve engine-run kayıt bağlantısı eklenmiş. Önceki bölümlerdeki 'müzakere tamamen modelde' ifadesi eski sürüm bulgusudur; bugünkü uygulamaya aynen taşınmamalı. Kodda bulunması canlı doğruluk kanıtı değildir. Öncelik artık yeni durumu sıfırdan kurmak değil, geçiş anlamlarını ve kayıt sınırını doğrulamaktır.

Dersin ana fikri doğru: model tutar ifadesini anlar; banka verisi ve policy izin verilen tutarı belirler; kayıt doğrulanmış/onaylanmış değerden yapılır. Ancak örnekteki `floor_offer_made` tek bayrağı ile `amount < floor` durumunda otomatik ret üretmek yeterli değildir. Müşterinin hangi teklife hangi cevabı verdiği de bilinmeli. Kabul edilebilir tutar ile müşteri tarafından onaylanmış ödeme sözü ayrı kavramlardır.

### Kural sözleşmesi
- İlk talep tam past_due; agent 'ne kadar ödeyebilirsiniz?' veya aynı anlamdaki açık uçlu pazarlığı başlatmaz. Müşterinin kendiliğinden önerdiği uygun tutar buna rağmen işlenir.
- Floor: A'da kart için minimum_payment, kişisel/taşıt kredisi için instalment_amount. Bunlar policy/API eşlemeleridir; örnek tutarlar veya alan adları genel runtime'a gömülmez.
- Müşteri önerisi floor <= amount <= past_due ise kabul edilebilir. İki sınır dahil. Müşteri '420 çok fazla ama 200 öderim' diyorsa 200 değerlendirilir; otomatik 126'ya indirilmez, ret sayılmaz.
- Yalnız tam tutarın fazla olduğunu söylüyorsa floor bir kez teklif edilir; kalanın gecikmede kalacağı açıklanır. Floor'u kabul etmezse kural 30 yolu uygulanır. Geç bantta attempt 2'nin floor/deadline teklifi ayrıca izinlidir; 'floor sadece bir kez telaffuz edilir' yasağı üretme.
- Floor altında müşteri teklifinde bunun kaydedilemeyeceği söylenir ve floor bir kez sunulur. Floor henüz önerilmeden müşterinin düşük tutarı otomatik flat refusal değildir. Teklif tekrarında hangi cevabın hangi pending offer'a karşılık geldiği kontrol edilir.
- Kural 26'nın floor teklifi ile kural 30 ikna adımı aynı şey değildir. Salt 'too much' olayını ilk ikna hakkını tüketen flat refusal gibi işleme; olay bağlamını ve 29–30'u birlikte uygula. B'de toplu bugün reddi sonrasında ürünlerin attempt 1'den başlaması ayrı hükümdür.
- Tutar önerisi, uygun tarih ve son read-back onayı olmadan create_promise izni değildir. Floor teklifine 'evet' de tek başına son onay yerine geçmez.

### Ders önerisini iyileştiren ayrımlar
1. **Sayısal kontrol saf olsun:** parse_amount/validate_amount, sayaç veya teklif geçmişini değiştirmeden uygun/altında/üstünde/belirsiz/hatalı sonuç versin. Diyalog geçişi bu sonucu ve bekleyen teklifi birlikte işlesin. Kayıt öncesi aynı kontrolü yeniden yapmak ikna hakkını tüketmesin.
2. **Çoklu anlam korunsun:** full_amount_too_high, önerilen tutar, tarih ve ürün kapsamı birlikte taşınsın. Tek enum seçip diğer bilgiyi atma. Aynı cümlenin `too_much` ve `proposes` olarak sırayla işlenmesi önce gereksiz floor teklifi sonra başka teklif üretmemeli; önce olay birleşimi çözülmeli.
3. **Teklif geçmişi türüyle saklansın:** ürün id, tutar, tarih, teklif amacı (initial/floor adjustment/ladder), teklif sürümü, sunulma ve cevap durumu. Floor kuralı ile ikna sayacı ayrı olsun ama iki bağımsız bayrak aynı floor teklifini farklı adlarla tekrar ettirmesin. 26/27'nin ortak kapsamı belirsizse seçilen yorum kaynaklarla kaydedilsin; yeni teklif hakkı icat edilmesin.
4. **Kısmi güncelleme kayıpsız olsun:** müşteri sadece tutarı değiştiriyorsa önceki geçerli tarih korunur; sadece tarihi değiştiriyorsa önceki tutar korunur. İlgili ürünün eski onayı iptal edilir, güncel teklif tekrar doğrulanır ve gerekli read-back yenilenir. Diğer ürünlerin değerleri değişmez.
5. **Tutar kapsamı belli olsun:** B'de 'toplam 300 öderim' her ürüne 300 uygulanması veya keyfî paylaştırma değildir. Teklifin ürün başına mı toplam mı olduğu korunur; belirsizliğe yönelik ürün açıklaması istenir. Bu, yasaklanan 'ne kadar ödeyebilirsiniz?' pazarlığına dönüştürülmez. Aynı ürüne iki taksitli yeni plan icat edilmez.
6. **Tutar üst sınırı sessiz kırpılmaz:** past_due üstü miktar için brief ayrı konuşma prosedürü tanımlamıyor. Uygulama varsayımı olarak tam gecikmiş tutarı açıkça önerip onaylatmak veya anlamı açıklığa kavuşturmak seçilebilir; üst miktarı habersiz tam borca dönüştürme. Yeni bir resmî outcome/reason oluşturma.
7. **Kalan borç doğru anlatılsın:** 'rest stays overdue' kural 26'da gerekli. Kalanın sayısını söylemek şart değil; söylenecekse past_due - önerilen tutar kodla hesaplanmalı ve gelecekteki ödemeye bağlı anlatılmalı. Ödeme sözü alınması borcu bugün azaltmış gibi sunulmaz; yeni ödeme planı/faiz affı çıkarılmaz.

### Mevcut kodda hedefli inceleme bulguları
Bunlar statik kod bulgusudur; yeni canlı koşularda görülmüş hata diye raporlanmaz. Claude düzeltmeden önce dosyanın güncel hâlini tekrar karşılaştırmalı.

- `propose()` tutarı `min(amt, p['full'])` ile sessizce azaltıyor. Bu işlem açık karar/teklif ve onay yoluna çevrilmeli.
- Alt sınır `amt < floor - 0.005` ile kontrol ediliyor. Brief tolerans tanımlamıyor; yarım kuruş eşiğiyle floor altı tutarı kabul edip kayıtta yuvarlama yapılmamalı. Para hassasiyeti sözleşmesine göre kesin karşılaştırma kullanılmalı.
- `too_much` dalında `used == 0` iken `used = 1` yapılıp ilk ladder tarihi seçiliyor. Salt tutar itirazının ikna hakkını tüketmesi ve tarihi değiştirmesi 26/29/30 bağlantısıyla sınanmalı; kod yazılmış olması bu yorumu doğrulamıyor.
- `floor_offered` ve `below_offered` ayrı tutuluyor. Aynı görüşmede iki yolu arka arkaya tetiklemek floor'un gereksiz tekrarına yol açabilir; teklif geçmişiyle birlikte denetlenmeli.
- `amount_only` yolu tarihi bugün/sonraki iş gününe alıyor. Özellikle read-back sırasında yalnız tutar değiştirildiğinde önceden kabul edilmiş tarihin kaybolması riski var.
- Tutar ile vague tarih aynı olayda gelince ilk açıklama yolunda tutar bekleyen aday olarak saklanmıyor; sonraki kesin tarih cevabında current_amount tam tutara dönebilir. '200 next week' → 'Friday' zincirinde 200 korunmalı.
- Alt-floor tutar + geçersiz/ileri tarih, erken return nedeniyle tarih önerisini kaybedebiliyor ve yerine bugün koyabiliyor. İki alan birlikte normalize edilip önerinin hangi parçalarının değiştiği açıkça anlatılmalı.
- Teklif miktarları float, para metni iki ondalık ve kayıt pre-hook'u float kullanıyor. Kanonik Decimal metni veya sözleşmeye uygun alt birim tutulmalı; son API serileştirmesi dahil konuşma/onay/ledger değer eşitliği sınanmalı. Yalnız ekranda iki hane göstermek hassasiyet koruması değildir.

### Veri doğrulama ve genelleme
Eksik floor, bilinmeyen ürün eşlemesi, NaN/Infinity, boolean tutar, bozuk sayı veya floor > past_due ile normal müzakereye girme. Sıfır/negatif için brief/API kısıtlarını esas al; dersin `floor <= 0` koşulunu kaynak doğrulaması olmadan bütün brief'lere evrensel banka kuralı yapma. Sayı metnindeki ayraçları keyfî silme; para birimi veya küsurat belirsizse açıklığa kavuştur. Para birimi ve basamak sayısı kaynaklı olmalı. 'Digits only' araç açıklaması küsuratlı meşru tutarları kaybettirmemeli.

Kullanıcı 200 dedi diye 200'ün doğru ürün için, doğru para biriminde ve tek ödeme sözü olarak çıkarıldığı varsayılmaz. Ürün/teklif sürümüyle bağlantı korunur; API öncesinde tutar, tarih, onay ve kayıt durumu birlikte doğrulanır. Aynı başarılı promise yeniden yazılmaz; müşteri değişiklik isterse kural 36 uygulanır.

### Hedef testler ve kabul ölçütü
Örnek 420/126 değerleri yalnız test fixture'ıdır. Aynı özellikler farklı tutar ve ürün sıralarıyla da kontrol edilmeli.

| Senaryo | Beklenen |
|---|---|
| 126, 200, 420 önerisi | İki dahil sınır ve ara değer kabul edilebilir; henüz kayıt yok |
| 125.99 önerisi | Floor altı; açık floor teklifi; yuvarlayarak kabul yok |
| '420 çok fazla ama 200 cuma öderim' | 200 ve cuma birlikte korunur; floor'a indirme/ret sayma yok |
| Yalnız 'çok fazla' | Floor + kalan gecikme açıklaması; bağlamsız ikna hakkı tüketimi yok |
| Floor teklifi reddi | Bir kez ret işleme; ilgili ladder; aynı olaydan çift sayaç yok |
| Floor önce too_much sonra düşük teklif yolunda | Gereksiz floor döngüsü yok; attempt 2 istisnası korunur |
| '200 next week', sonra kesin gün | 200 kaybolmaz; tarih netleşir |
| Onay aşamasında sadece tutar/tarih değişir | Diğer alan korunur; eski onay geçersizleşir |
| Full üstü teklif | Sessiz min()/kırpma yok; seçilen açıklama politikası görünür |
| floor == full | Aynı miktar sanki indirimmiş gibi anlatılmaz; tekrar teklif geçmişi kontrol edilir |
| B'de bir ürün too_much, diğeri uygun teklif | Durum ve sayaçlar ürünler arasında taşınmaz |
| Toplam tutar, belirsiz ürün kapsamı | Keyfî paylaştırma veya bütün ürünlere aynı tutarı yazma yok |
| Eksik/bozuk tutar; gerçek küsurat | Uydurma yok; meşru hassasiyet korunur |
| Onaylanan 200, API isteğinde başka tutar | Kayıt sınırı engeller; sadece transcript testiyle yetinilmez |

Önce saf tutar testleri ve olay dizisi testleri; sonra güncel otomatik builder adayıyla PUB-06 ve B'nin ilgili vakaları. Mevcut canlı test planına birleştir, ikinci bağımsız simülasyon serisi başlatma. Yerel başarı, gerçek konuşma ve ledger başarısı ayrı raporlanmalı. Özellikle konuşmanın 'ne kadar ödeyebilirsiniz?' anlamına kaymadığını ve remaining-overdue açıklamasını kontrol et.

### Rekabet açısından uygulama kararı
Puan hedefi için en yüksek değer: müşterinin geçerli ara tutarını kaybetmemek, floor'u gereksiz önermemek, tutar itirazıyla ret hakkını karıştırmamak, kısmi düzeltmede diğer teklif alanını korumak ve kesin tutarı onaydan banka kaydına taşımak. Tüm eski mimariyi değiştirme veya yeni amount aracı zorunluluğu yok; mevcut müzakere motorunda küçük saf doğrulama ve açık geçiş düzeltmeleri tercih edilir. Daha yüksek tahsilat hedefi hiçbir zaman kurala aykırı baskı, onaysız tutar veya gereksiz tekrar için gerekçe değildir.

## Kurallar 28–33: ikna sırası, ret bağlamı ve hardship önceliği

11 Ekim 2026. Kaynaklar: kullanıcının Ders 2.8 metni, Brief A 28–33 ve çapraz kurallar 18–27/34–46, Brief B 4–10, güncel builder/runtime/negotiation.py ve builder/components.py. Salt okunur karşılaştırma; aşağıdaki kod bulguları yeni bir canlı test sonucu değildir. Önceki bölümlerle birlikte mevcut müzakere motoruna hedefli düzeltme olarak uygulanmalı.

### Değerlendirme
Dersin modelden anlam çıkarıp politikayı kodla uygulama önerisi doğru. Ancak tek bir öncelik fonksiyonu ve kullanılan hak sayacı yeterli değil: müşteri hangi soruya cevap veriyor, cümlede birden fazla sinyal var mı, teklif gerçekten sunuldu mu, hardship sonraki turlarda devam ediyor mu soruları da açık duruma bağlanmalı. Her kavram için ayrı workflow düğümü yaratmak gerekmiyor.

### Kaynak sözleşmesi ve önemli ayrımlar
- A'da ilk ödeme sorusu 'Can you make this payment today?' ve başlangıç tutarı tam past_due. B'de bütün ürünler açıklandıktan sonra toplu bugün sorusu; olumsuz cevap sonrası API sırasıyla ürün başına attempt 1, her ürün için bugün sorusunu yeniden sorma yok.
- Müşterinin tarih VEYA tutar önerisi, geçersiz olsa da önce 18–27'ye gider. 'No, next Friday' düz ret değildir; 'No, 50 on Friday' de önce tutar/tarih değerlendirmesidir. Bağlamdaki diğer sinyalleri kaybetme.
- Ödeme teklifine düz ret veya cevap vermeme ikna politikasını tetikler. 'Hayır' hangi soruya cevap? Destek transferine hayır, ödeme teklifine hayır ve read-back değişikliği aynı olay değildir.
- Early için bir, late için iki ikna adımı. Attempt 1 full veya önceden full-too-much bilgisi varsa floor; tarih bu haftanın son iş günü, bugün o günse sonraki haftanın son iş günü. Attempt 2 yalnız late: floor ve deadline.
- Son ikna teklifi sunulur sunulmaz çağrıyı kapatma: müşterinin cevabı hâlâ işlenmelidir. Hak kalmaması yeni agent iknasını yasaklar; son teklife kabul veya yeni gönüllü öneri gelirse doğru doğrulama yolunu atlama. Son ret sonrası yeni teklif yok.
- Daha önce reddedilmiş teklif tekrar sunulmaz. Teklif kimliği yalnız tutar değil ürün+tutar+tarih ve bağlamdır. Farklı tarihte floor, otomatik olarak aynı teklif değildir. Aynı koşulları sırf etiketini 'attempt 2' yaparak yeniden sunma; 26/31 kesişimi özel bir belirsizlik oluşturuyorsa kaynak yorumunu açık kaydet.
- Hastalık, ailede ölüm veya iş kaybında kısa taziye/empati ve destek seçeneği; normal ikna yok. Destek kabul edilirse support transferi; reddedilirse A'da no_promise/hardship. 32, 30 ve 41'den önceliklidir.
- Hardship ile gönüllü tarih/tutar birlikteyse teklif doğrulanabilir; otomatik transfer edilmez, ödeme iknasına da dönülmez. Empati gereği unutulmaz. Destek teklifinin bu karma cevapta hangi sırayla yapılacağı açıkça tasarlanıp transcript'te sınanmalı; basit 'VALIDATE_PROPOSAL' dönüşü geri kalan iletişim yükümlülüklerini silmez.
- İndirim, af, taksit planı veya brief dışı şartlar önerilmez. Minimum ödeme, kalan borcun silindiği anlamına gelmez. Müşterinin böyle bir şart sorması agent'a yetki vermez.

### Durum ve geçiş tasarımı
1. **Bekleyen soru:** pending_question_kind (initial_payment / offer / exact_date / support / readback), ilgili ürünler ve teklif sürümü tutulur. Evet/hayır önce bu bağlamda anlamlandırılır. Modelin verdiği 'confirms' etiketi tek başına banka yazma yetkisi değildir.
2. **Bir turu birlikte değerlendir:** tarih, tutar, affordability, hardship, transfer talebi ve düzeltme sinyallerini önce topla. Sonra kaynak önceliklerine göre tek tutarlı eylem veya açık sıralı eylem listesi üret. Kelimelerin sırasıyla 'refuses' sonra 'hardship' çalıştırıp aynı yanıtta önce ödeme baskısı sonra empati üretme.
3. **Sayaç anlamları ayrı:** next_ladder_step / tüketilen politika adımı, gerçekten sunulan ikna sayısı, bekleyen teklif ve son işlenen müşteri olayı ayrı kavramlardır. 30 ret olayını adım tetikleyicisi yapar; engine'in aynı olayı tekrar işlemesi ikinci adımı tetiklememeli. Atlanan mükerrer aday, müşteriye sunulmuş teklif sayılmaz; ancak daha önce tüketilmiş adımı yeniden kullanılabilir de yapmaz.
4. **Sunulma kanıtı:** teklifi hesaplamak, konuşmada sunmak ve cevap almak ayrı aşamalardır. Platform sesin gerçekten duyulduğunu göstermiyorsa bunu kanıtlamış gibi yazma; gözlenebilen asistan mesajı/akış olayı kullanılmalı ve kesinti sınırı belgelenmeli. Sayaç artışını yalnız düğüm girişine bağlama.
5. **Hardship kalıcı kısıt:** hardship_detected ile support_offer_handled ayrı. Teklif doğrulandı veya destek bir kez konuşuldu diye ikna tekrar açılmaz. Gönüllü teklif başarısız/uygunsuz çıkarsa doğrudan normal ladder'a dönme; 18–27 kapsamında açıklama/düzeltme ve 32 kapsamında destek yolu birlikte ele alınır. Belirsiz kesişimde yeni baskı politikası icat etme.
6. **B kapsamı:** ürün başına sayaç, teklif ve ret geçmişi; kişisel hardship'in kapsamı yalnız aktif ürüne daraltılmamalı. Hangi ürünleri etkilediği kaynak/ifade bağlamıyla tutulmalı. Genel iş kaybı sonrası sonraki üründe otomatik iknaya dönmek öncelik kuralını bozar. Paid/dispute gibi ürün olayları diğer ürünleri kendiliğinden kapatmaz.
7. **Transfer yetkisi:** support için bekleyen destek teklifi ve kabulü; restructuring için uygun talep ve hardship önceliği; human için kural 42 bağlamı. Transfer tool'unun erişilebilir olması kaynak koşulunun yerine geçmez. Banka başarı sonucu olmadan 'transferred' iddiası yok. B'de transfer öncesi/sonrası not yasağı ve kaydedilmiş promises korunur.

### Ders örneklerinde güçlendirilmesi gereken noktalar
- İlk örnekte tarih varsa hemen dönmek tutarı atlayabilir; bu sadece öğretim örneğidir, üretimde iki alan birlikte doğrulanır.
- Örnek `first_attempt_date` fonksiyonu `result <= today` ile hafta sonunu da gelecek haftaya kaydırıyor. Brief'in açık ifadesi 'today is that day' yani eşitliktir. Bugünün haftanın son iş gününden sonra olması için bu genişletme uygulama yorumu olarak kaydedilmeli; resmî kural diye sunulmamalı. Hiç iş günü olmayan hafta veya deadline dışı teklif de sessizce düzeltilmez, kaynak çelişkisi görünür kılınır.
- Non-answer ile sessizlik/ASR boşluğu, araç gecikmesi veya kesinti aynı değildir. Özel kuralla cevaplanacak robot/scam sorusu da otomatik ret sınıfına atılmamalı. Ödeme sorusuna gerçekten cevap vermeme kuralı uygulanır; platform hatası müşterinin hakkını tüketmez.
- `persuasion_used < limit` kontrolü tek başına yetmez. Aynı teklifin reddedilmiş olması veya hardship, hak kalsa bile yeni iknayı engelleyebilir.

### Güncel kodda hedefli riskler
- `next_attempt()` used sayısını teklif üretmeden ve mükerrerlik kontrolünden önce artırıyor. Atlanan ladder adımı ile konuşmada sunulan teklif ayrılmıyor. İşlenmiş olay ve sunum kanıtıyla birlikte sınanmalı; sayacı basitçe sona taşımak da tek başına çözüm değildir.
- `next_attempt()` çıkışında üretilen tarihin genel tarih/tutar doğrulayıcısından geçtiği görünmüyor. ladder_offer bugünle eşitlik yerine <= kullanıyor; bunun kapsamı yukarıdaki kaynak ayrımıyla belgelenmeli.
- Hardship için `hardship_handled` bir kez true olunca otomatik öncelik kontrolü devreden çıkıyor. `next_attempt()` içinde kalıcı hardship engeli yok. Gönüllü tekliften sonra ret gelmesi veya başka ürüne geçilmesi yeniden ikna riski oluşturuyor.
- `events` müşteri ifade sırasıyla tek tek işleniyor. 'No + hardship + proposal' aynı turda çelişkili metin ve durum üretebilir; önce tur düzeyinde politika çözümü gerekli.
- `too_much` dalının used=1 yapması 24–27 notlarındaki riskle aynı; ikinci ayrı düzeltme işi oluşturma, tek geçiş tablosunda çöz.
- Transfer aracı konuşma modeline açık; queue model_field ile seçiliyor ve esas kısıt prompt. Support kabulü veya hardship/restructuring önceliği işlem sınırında doğrulanmış değil; guard ve entegrasyon kanıtı gerekli.
- `stop` olayı ilk kez geldiğinde ürünleri refused yapabiliyor; açıklama 'does not want to continue'. Kural 45'in iki kez konuşmayı reddetmesiyle farkı kontrol edilmeli. Ödeme reddi, görüşmeyi reddetme ve destek reddi üç ayrı bağlamdır.
- Mükerrer olay anahtarı tur sayaçlarının toplamı+pid+type+değerlerden üretiliyor. İç node hareketi aynı müşteri mesajının kimliğini değiştiriyorsa çift tüketim; iki gerçek mesaj aynı anahtara düşüyorsa cevap kaybı olabilir. Canlı platform olaylarıyla sınanmalı, desteklenmeyen message_id varmış gibi davranılmamalı.

### Yüksek değerli test dizileri
| Dizi | Beklenen |
|---|---|
| A early: bugün hayır → attempt 1 hayır | Bir ikna, sonra refused; attempt 2 yok |
| A late: bugün hayır → attempt 1 hayır → attempt 2 evet | İki ikna; son cevabı bekle, doğrulama/read-back; erken kapanış yok |
| A late: bugün hayır → iki ikna da hayır | Üçüncü teklif yok; doğru kapanış |
| 'No, 200 next Friday' | Tarih+tutar korunur; ikna sayacı değişmez |
| Aynı ret olayını iki kez işle | Tek adım; iki gerçek ayrı ret birbirinden ayrılır |
| Daha önce reddedilen aynı tutar+tarih | Yeniden sunma yok; farklı tarihli izinli floor istisnası korunur |
| Hardship + gönüllü teklif aynı mesaj | Empati, teklif doğrulama; ikna ve otomatik transfer yok |
| Hardship → gönüllü teklif → değişiklik/ret | Normal ladder yeniden açılmaz |
| İş kaybı + yeni plan talebi | 32'nin 41 önceliği; otomatik restructuring yok |
| Destek teklifine hayır / evet | Hardship sonucu / uygun support transferi; ödeme reddi sayılmaz |
| B toplu bugün hayır | API sırası, ürün başına attempt 1; yeniden bugün sorusu yok |
| B ürün 1 hardship, ürün 2'ye geçiş | Geçerli hardship kapsamı kaybolmaz; sayaçlar karışmaz |
| Bir kez konuşmak istememe, sonra ikinci kez | Kural 45 bağlamı; tek stop olayından yanlış erken kapanış yok |
| 'Scam mı?' + tarih önerisi | Kaynaklı kısa cevap ve teklif kontrolü; gereksiz ret yok |
| İndirim/taksit talebi | İcat edilmiş şart yok; ilgili özel kural ve hardship önceliği |
| Bugün son iş günü; hafta tatille kısalmış | Takvime uygun attempt 1; geçerlilik kontrolü; sabit cuma varsayımı yok |

Yerel olay dizisi testlerinde her adım sonrası sayaç, pending offer, hardship engeli ve sonraki eylem kontrol edilir. Ardından mevcut ölçüm planına PUB-05/06/12 ve gerekli küçük karma-sinyal konuşmaları eklenir. Aynı sınıflandırıcıdan hem olay hem beklenen sonuç üreterek testin kendini doğrulaması önlenir. Sabit olaylarla runtime testleri ve gerçek müşteri metninden olaya dönüşüm testleri ayrı tutulur. Hatalar transcript + durum geçişi + banka kaydıyla sınıflandırılır; yalnız son outcome yeterli değildir.

### Uygulama önceliği
1. Karma sinyallerde tur düzeyinde karar ve pending-question bağlamı.
2. Kalıcı hardship ikna engeli ile transfer uygunluğu kontrolü.
3. Ürün başına ladder/sunum/ret geçmişi ve mükerrer olay doğrulaması.
4. B sırası ve son ikna cevabının doğru işlenmesi; mevcut onay/kayıt akışıyla regresyon kontrolü.

Başarı ölçütü daha fazla ısrar değil, izin verilen doğru teklifi doğru anda ve tekrarlanabilir biçimde sunmaktır. Çalışan bileşenleri koru; yeni genel framework veya gereksiz model çağrıları ekleme. Kaynakların açıklamadığı kesişimleri not et, başarılı public koşu gördün diye bunları kesin kural ilan etme.

## Kurallar 34–38: güncel onay, kayıt yetkisi ve banka sonucu

11 Ekim 2026. Kaynaklar: Ders 2.9; Brief A 34–38; Brief B 6–11 ve kapanış hükümleri; tools/openapi.json /create_promise; güncel negotiation.py (CONFIRM, REC_NEXT, FINISH) ve components.py (neg_relay, neg_confirm, record_one). Bu bölüm statik inceleme ve tasarım önerisidir; kod değiştirilmedi ve yeni canlı test yapılmadı.

### Karar: doğru yaklaşım, daha güçlü işlem sınırı gerekli
Dersin teklif / açık onay / banka sonucu ayrımı yerinde. Güncel kod zaten engine-run create_promise, saklanan agreed değerleri, teklif sürümü ve tek runtime retry katmanı içeriyor. Bunları yeniden kurma. Eksik olan, bütün kayıt yollarının güncel onaya dayanmasını ve banka cevabının doğru ürün/denemeye ait olmasını açıkça doğrulamak. Dört boolean ile can_record sonucu almak, bu boolean'ların hangi tekliften geldiği belli değilse yeterli değil.

### Kaynak hükümler
- A: ürün, tutar, tarih read-back'i ve 'Do you confirm?' sorusundan sonra açık evet gerekir. Önceki ödeme isteğine evet, nihai read-back onayı değildir.
- Değişiklik varsa ilgili alanı yeniden doğrula, değişmeyen alanı koru, güncel teklifi tekrar oku ve yeni onay al. 'Yes, but change the amount' değişikliktir; önce yes'i işleme.
- Bir ürüne en fazla bir başarılı promise; kaydedildikten sonra aynı çağrıda değişiklik/iptal yok, mobil uygulama yönlendirmesi var. Bu, ilk çağrı başarısızsa izin verilen retry'ı yasaklayan 'tool yalnız bir kez çağrılır' kuralı değildir.
- Başarı ancak bankanın ilgili işlem için ok=true sonucu. İlk bilinen başarısızlıktan sonra bir retry; ikinci başarısızlıkta A no_promise/service_error. Çağrı düzeyinde değil ürün başına sayılır.
- Başarı sonrası tam cümle: 'You will receive a text message confirming this promise.' Başarısız/henüz sonuçlanmamış ürün için SMS veya kayıt başarısı iddia edilmez.
- B: bütün vaatler tek read-back ve bir onayla, sonra ürün başına kayıt. Bir ürün başarısızsa diğer başarılı kayıtlar korunur; başarısız ürüne service_error notu. En az bir başarılı promise kapanışta promise kazandırır, transfer istisnası saklıdır. Transferde hiçbir not yok; kaydedilmemiş anlaşmalar sonradan yazılmaz.

### Onayı somut veriye bağlayan sözleşme
Teklif listesi için değişmez bir snapshot üret: çağrı/müşteri bağlamı, ürün id'leri, kanonik tutarlar ve ISO tarihler; kaynak ürün sırasını koru. İçerik kimliği/sürümü bu listeye bağlı olsun. Hash kullanmak bir uygulama seçeneği, tek başına güvenlik kanıtı değildir.

Asgari aşamalar: validated → readback_presented → confirmed → in_flight → recorded / failed / unknown. Bunlar ayrı node olmak zorunda değil.

1. readback_version yalnız metin hazırlandı diye 'müşteriye sunuldu' kanıtı sayılmaz. Gerçek asistan mesajı/akış olayıyla ilişkilendir; sesin tamamının duyulduğu platformda gözlenemiyorsa sınırı dürüstçe belirt. Kesilen read-back'ten gelen belirsiz cevapla kayıt yok.
2. confirmed_version yanında onayın hangi yeni müşteri cevabından ve hangi read-back'ten geldiğini tut. Eski extraction alanı yeni turda geçerli kalmamalı. Eşit version ile rb_version sadece metnin güncel olduğunu gösterebilir; müşteri onayının kanıtı değildir.
3. Son cevabı bir bütün olarak işle: açık onay, değişiklik, ret, koşullu cevap veya belirsizlik. 'Yes, if you waive the rest' onay sayılmaz. 'Yes, is this recorded?' gibi değişiklik içermeyen sorulu onayların da anlamı ayrı değerlendirilir; bütün soru içeren cevapları reddetme.
4. B'de yalnız bir ürünü onaylama veya bir ürünü listeden çıkarma, tüm listeye blanket onay değildir. Kapsamı güncelle, güncel vaat listesini gerekli biçimde tekrar onaylat. Reddedilen ürünü eski toplu onayla yazma.
5. Kayıt sınırında current_snapshot == presented_snapshot == confirmed_snapshot, doğru müşteri/ürün, geçerli tutar/tarih, recorded değil, aynı ürün için başka işlem beklemiyor, transfer/terminal durum yok ve retry hakkı var kontrolleri çalışsın.
6. İstek gövdesi onaylanan snapshot'tan üretilsin. Gönderilen customer_id/product_id/amount/date ile snapshot eşitliğini gerçek araç kaydında doğrula. Guard eksik veriyi sessizce değiştirmesin veya başarısızlıkta gönderime devam etmesin.
7. Bir deneme başlatıldığında ürün, teklif sürümü, istek gövdesi ve deneme numarası bağlansın. Sonuç bu pending işlem üzerinden tüketilsin; geç gelen/mükerrer sonuç başka ürünü recorded yapmasın.

### Retry ve belirsiz sonuç: yarışma sözleşmesini bozma
OpenAPI /create_promise HTTP 500 için hiçbir kayıt yapılmadığını ve çağrının tekrarlanabileceğini açıkça söylüyor. Bu bilinen başarısızlıkta Brief A'nın bir retry şartını uygula. Taşıma başarısı veya HTTP 200, gövdedeki ok=false sonucunu başarı yapmaz.

Timeout, bozuk cevap veya yalnız function_call_error etiketi tek başına 'bankaya hiçbir şey yazılmadı' kanıtı değildir. Hangi olayın sözleşmedeki 500'e karşılık geldiğini kontrol et. Belirsiz sonuç için recorded demek de kesin kaydedilmedi demek de kanıtsız olabilir. unknown ayrı iç durumdur; bankanın kabul etmediği yeni outcome/reason icat edilmez, çözülemeyen final davranışı bilinen eksik olarak raporlanır.

API'de belgelenmemiş idempotency anahtarı veya sorgu endpoint'i ekleme. Yerel recorded_products kontrolü, bankanın yazıp yanıtının kaybolması halinde tek başına tam 'exactly once' garantisi vermez. Belirsiz sonuçları başarı sayarak veya açık başarısızlık retry'ını kaldırarak public skoru düzeltme.

Tekrar tek katmanda: runtime sayıyorsa platform retry=0 ve ayrıca modelden tekrar yok. Retry aynı onaylı gövdeyi kullanır; yeni tutar/tarih üretmez. Sayaç aynı node'a dönüşte sıfırlanmaz. Başarılı yanıt veya tükenmiş hak sonrasında kullanıcı 'tekrar dene' dese de üçüncü çağrı yok. Platform gözlemleyemediğimiz kesinti davranışı ayrıca ölçülmeli.

### Güncel kodda hedefli açıklar
- Olumlu: record_one pre_actions kullanıyor; alanlar rec_product/rec_amount/rec_date'den geliyor; maxRetries=0. REC_NEXT ürün başına rec_attempts tutuyor. Bunlar korunmalı.
- CONFIRM yalnız phase=readback ve rb_version=version denetliyor. Ayrı confirmed snapshot/cevap kimliği yok; rb_answer doğruluğu dış geçişe bırakılmış. REC_NEXT ise phase/confirmed_version kontrolünü tekrar yapmadan status=agreed ürünleri seçiyor. Tüm girişler doğruysa çalışabilir; işlem sınırında doğrudan guard ile güçlendirilmeli.
- İki onay yolu var: neg_relay extraction→neg_confirm ve negotiation_event confirms olayı. İkisi aynı ortak kayıt yetkisi kontrolüne bağlanmalı; birinde daha gevşek koşul kalmamalı.
- rb_answer ancak CONFIRM çalışınca 'consumed' oluyor. Her yeni read-back/teklif değişiminde eski değer temizleniyor mu, boş extraction eski yes'i koruyor mu canlı platformla sınanmalı. min_confidence=0.7 veya dersteki 0.8 doğrulanmış güvence değildir.
- REC_NEXT success_count artışı + flattened ok sonucuyla başarı belirliyor; failure_count okunuyor ama sonuç işleme kapısında artışı şart koşulmuyor. Tamamlanmış yeni sonuç olmadan tekrar giriş, başarısızlık/retry gibi ele alınabilir. Pending denemenin tamamlanması ayrı kontrol edilmeli.
- Aynı record_one düğümü bütün ürünler için kullanılıyor. Önceki ürünün ok/yanıt alanı kalırsa yeni sayaçla yanlış birleşmemesi sınanmalı. promise_id varsa işlem izine alınabilir; API zorunlu kılmıyorsa yokluğu tek başına ok=true başarısını iptal etmez.
- REC_NEXT exception halinde rec_go='done' yazıyor. İç durum/serileştirme hatası, normal bitiş gibi gizlenmemeli; bilinen banka başarısızlığıyla ayrı raporlanmalı.
- record_one pre-hook'u tutarı float'a çevirirken exception'ı pass ile yutuyor. Dönüşüm hatasında istek gönderimini durdurabilen doğrulanmış yol kullanılmalı; yanlış tutarla devam edilmemeli.
- FINISH başarılı ürün varsa genel recorded metni ve SMS cümlesi ekliyor. B kısmi başarısında hangi ürünün kaydedildiği açık olmalı; genel cümle bütün ürünler başarılıymış izlenimi vermemeli. Başarısız ürünün SMS alacağı söylenmemeli.
- Kayıtlar arası passthrough ve son kapanış akışında müşteri değişiklik/transfer söylerse hangi olayların işlenebildiği henüz bu incelemeyle kanıtlanmadı. Özellikle B'nin 'transfer sonrası anlaşılmış ama yazılmamış ürünü kaydetme' hükmü ve A'nın kayıt sonrası mobil uygulama yanıtı için gerçek kesinti testi gerekir.

### Test matrisi: konuşma, istek ve ledger birlikte
| Senaryo | Beklenen |
|---|---|
| Read-back öncesi yes, maybe, sessizlik veya eski rb_answer | Banka çağrısı yok |
| Son read-back'e açık yes | Yalnız güncel onaylı snapshot gönderilir |
| 'Yes, but 250 instead' | 200 veya onaysız 250 yazılmaz; tarih korunur, yeniden read-back/onay |
| Tarih değişimi, ürün çıkarma, B'de kısmi onay | Eski toplu onay geçersiz; doğru liste yeniden sunulur |
| Koşullu 'yes if discount' | Yetkisiz şart veya kayıt yok |
| Aynı confirmation/rec_next olayı yeniden işlenir | Ek banka çağrısı yok; pending işlem korunur |
| İlk açık hata, ikinci başarı | İki aynı istek, bir başarılı promise; sonra tam SMS cümlesi |
| İki açık hata | İki çağrıdan sonra dur; A service_error; başarı/SMS yok |
| HTTP 200+ok=false; ok string; stale ok | İş sonucu normalize edilir; taşıma başarısı tek başına yeterli değil |
| Sonucu belirsiz timeout | Kanıtsız başarı/başarısızlık iddiası yok; sözleşme sınırı raporlanır |
| B ürün 1 başarı, ürün 2 iki hata | İlk promise korunur, ikinci service_error notu, doğru kapanış |
| İlk ürünün cevabı ikinci ürün sırasında tekrar gelir | Yanlış ürün başarıya dönmez |
| Başarı sonrası tutar/tarih değişiklik isteği | Yeni promise yok; mobil uygulama yönlendirmesi |
| Kayıtlar arasında transfer | Önceki başarı kalır; henüz yazılmayan ürün durur; not yok |
| Rec amount/date veya ürün snapshot'tan farklı | Gönderim engellenir; sessiz düzeltip kayıt yok |

Önce yerel guard, olay dizisi ve kontrollü sonuç testleri. Ardından mevcut PUB-10 ve çok ürünlü ölçüm planına birleştir; iki hata yolu public senaryoda yoksa yerel mock başarısını canlı test diye sunma. Ek endpoint veya failure injection desteği varsaymadan platformun mevcut imkânını doğrula. Son adayın transcript, banka istek sayısı/gövdeleri ve ledger sonucu aynı sürüm/hash'e bağlı raporlanmalı.

### Tamamlayıcı kontrol: onay yetkisi ve işlem tamamlanması
- **Onay yetkisi model argümanı değildir:** confirmed_version/snapshot modelin serbest doldurduğu bir alan olmasın. Runtime bunu yalnız güncel read-back'e ait yeni ve değişiklik içermeyen müşteri cevabını işledikten sonra üretir. Model yorumlaması yine hata yapabilir; açık durum kontrolü bu anlamsal riski tamamen ortadan kaldırmış sayılmaz.
- **Bir turdaki bütün sinyalleri önce işle:** aynı mesajdan confirms ve changes çıkarılırsa events listesindeki sıra banka kaydı başlatıp başlatmamayı belirlememeli. 'Yes, actually make it 250' için değişiklik önce çözümlenir ve yeni onay gerekir. Bu koşul iki onay yolunda da aynı olmalı.
- **Retry hakkı ile yeni işlem yetkisini ayır:** ilk gönderimde onaylı snapshot bir pending işlem olarak sabitlenir. İzinli retry bu işlemin aynı gövdesini tekrarlar; yeni teklif oluşturmaz. 'Onay tüketildi' diye gerekli retry engellenmez, retry adı altında yeni tutar/tarih gönderilmez.
- **Bekleyen sonuç olmadan ilerleme yok:** rec_next'e yeniden giriş, yeni banka cevabı geldiği anlamına gelmez. Pending işlem hâlâ sürüyorsa yeni deneme veya yeni ürün başlatma. Platform hangi tamamlanma bilgisini veriyorsa onu doğrula; olmayan request id veya atomiklik garantisi icat etme.
- **Read-back sorusu ile başka soruyu karıştırma:** müşteriye aynı yanıtta hem destek kabulü hem 'Do you confirm?' sorulması yes'in kapsamını belirsizleştirir. Bir seferde hangi karara cevap beklendiği açık olsun; B'nin tek toplu onayı bu ilkeyle uyumludur.
- **Sesli kesinti ölçümü:** yerel state testi read-back'in tamamının seslendirildiğini, müşterinin araya girmesinin işlendiğini veya otomatik kayıt zincirinin durabildiğini kanıtlamaz. Platformda gözlenebilen kesinti/mesaj sırasını küçük entegrasyonla test et; desteklenmeyen davranışı çözülmüş sayma.
- **Başarı cümlesinin kapsamı:** SMS metni A'da aynen korunur. B kısmi başarıda önce başarılı ürünler açıkça adlandırılsın; tek genel SMS ifadesi başarısız ürünlere de söz verilmiş izlenimi yaratmasın. Brief'in belirtmediği 'ürün başına mutlaka ayrı SMS aracı' gibi bir mekanizma ekleme.

Kompakt doğrulama izi: müşteri cevabı/olayı → sunulan teklif sürümü → onaylanan snapshot → gerçek istek gövdesi → deneme numarası → güncel banka sonucu → konuşmada başarı bildirimi. İz yalnız gerekli alanları taşısın; API anahtarı ve güvenlik cevapları bulunmasın. Runtime'da erişilemeyen ledger kanıtı yalnız geliştirme değerlendirmesinde kullanılır; final telefon ajanına ek banka dışı araç bağımlılığı getirilmez.

### Uygulama önceliği ve kazanım
İlk iş mevcut iki onay yolunu ortak commit guard'a bağlamak; ikinci iş yeni banka sonucunu doğru pending denemeye bağlamak; üçüncü iş çift hata, stale yes ve B kısmi başarı/kesinti testleri. Mevcut runtime'ı koruyarak bu boşlukları kapat. Başarının ölçütü 'müşteri evet dedi' değil, müşterinin tam olarak onayladığı geçerli işlemin doğru ürüne bir kez kaydedilmesi ve sonucunun doğru anlatılmasıdır.

Kabul kapısı: (1) onaysız/değişmiş snapshot için sıfır istek, (2) bilinen ilk hata sonrası aynı gövdeyle yalnız bir retry, (3) başarı sonrası aynı üründe yeni kayıt yok, (4) her recorded durumu güncel banka kanıtına bağlı, (5) B kısmi başarı ve transferde doğru ürünler korunuyor. Bu beş maddeyi ilgili yerel test ve platform kanıtlarıyla ayrı raporla; yalnız başarılı tek PUB-10 koşusu bütün kayıt motorunun doğrulandığı anlamına gelmez.

## Kurallar 39–45: özel talepler, itirazlar ve görüşme kontrolü

11 Ekim 2026. Kaynaklar: kullanıcının Ders 2.10 metni, Brief A 39–45 ve 1/15/32/36/46, Brief B 8–11 ve kapanış hükümleri; güncel negotiation.py ve components.py. Statik inceleme yapıldı; uygulama değişikliği veya yeni canlı test yapılmadı. Önceki modüllerdeki aynı sorunları ikinci kez iş listesine eklemek yerine bu bölümdeki koşullarla tamamla.

### Değerlendirme ve ders önerisinde düzeltmeler
Özel müşteri ifadelerini açık olaylara ve kontrollü eylemlere bağlama önerisi doğru. Ancak her istisna için yeni node veya ikinci bir router sistemi kurmak gerekmiyor: mevcut müzakere kararına ortak bir olay/öncelik katmanı eklenebilir. Bu katman kimlik öncesi ve sonrası gereken aşamalarda erişilebilir olmalı; ödeme aşamasına özgü olmamalı.

- Önerilen extraction örneğindeki identity_verified LLM'den çıkarılacak bir müşteri niyeti değildir. Yalnız bankanın doğrulama sonucu ve güvenilir çağrı durumu bunu belirler. Müşteri 'zaten doğrulandım' diyerek kapıyı açamaz.
- Örnek if zinciri evrensel öncelik tablosu değildir. Brief açıkça 32'nin 30/41'e önceliğini söylüyor; human/scam/paid/dispute arasında bütün birleşimler için sıralama vermiyor. Bir soru erken return ile aynı cümledeki işlem talebini yutmamalı.
- paid müşteri beyanına göre seçilen görüşme sonucudur; bankanın ödemenin geldiğini doğruladığı anlamına gelmez. 'Ödemeniz sistemde görünüyor' veya bakiyeyi sıfırlama sonucu çıkarılmaz.
- Kural 45'i her aşamada körlemesine no_promise/refused'a çevirmek doğru değil: daha önce gerçek promise varsa 46'nın sonuç tablosu ve B'nin öncelikleri birlikte değerlendirilir. Bu kesişimin uygulanma yorumu açık tutulmalı; önceki başarılı kayıt silinmez.

### Kaynak kuralların eylem sözleşmesi
| Olay | Konuşma ve işlem |
|---|---|
| Mevcut gecikmiş tutarın ödendiği beyanı | Bir iş gününe kadar yansıma süresi açıklaması; A'da yeni promise yok, paid kapanışı |
| Ürün/borç reddi veya geçmişte tamamen kapatıldığı iddiası | Tartışma/ikna yok; A no_promise/dispute; yeni promise yok |
| Yeni ödeme planı veya düşük taksit talebi | Plan tarif etme; hardship önceliğini kontrol et, uygunsa restructuring transferi |
| İlk insan talebi | Bir kez kendisinin yardımcı olup olamayacağını sor; bu ödeme ikna denemesi değildir |
| Yardım teklifinden sonra insan talebinde ısrar | general transferi; yeni yardım/ikna döngüsü yok; kimlikten önce de geçerli |
| Scam kaygısı | Banka müşteri hizmetlerini arayarak doğrulama yolu; numara veya gizli hesap bilgisi uydurma yok |
| Araç/brief'te cevabı olmayan soru | Bilginin mevcut olmadığını söyle; tahmin edilmiş oran, tutar veya gerekçe yok |
| İki ayrı konuşmama bildirimi | Kimlik öncesi not_verified/declined; sonrası 45 ve gerçek kayıt durumuna uygun kapanış; insan talebiyle karıştırma |

Paid/dispute ayrımında takvimde ne kadar zaman geçtiğinden çok beyanın konusu önemlidir: 'bu gecikmiş taksiti geçen hafta ödedim' hâlâ 39 olabilir; 'krediyi tamamen kapattım' 40 kapsamıdır. Her 'paid' veya 'last year' kelimesi tek başına karar verdirmez. Kısmi ödeme, belirsiz 'onu ödedim' veya başka ürüne ait ödeme, otomatik tam paid kabul edilmez; eksik olan ürün/ödeme kapsamı açıklığa kavuşturulur. Müşteri açık bir iddia verdiyse tekrar tekrar kanıt istemek veya brief'te olmayan makbuz süreci eklemek yok.

### Durum ve kapsam önerisi
- Olay: payment_claim_kind, ilgili product_ids, human_request, restructuring_request, hardship, refuses_to_talk ve sorular birlikte korunur. Alan adları öneridir; mevcut temsile uyarlanır.
- Güvenilir durum: bankadan identity_verified; çağrı genelinde human_help_offered, pending_question, talk_refusal_count, son işlenmiş müşteri olayı; ürün başına disposition ve recorded bilgisi. Node/ürün değişiminde insan talebi hakkı veya konuşmama sayacı sıfırlanmaz.
- Bir cümledeki 'istemiyorum, gerçekten istemiyorum' tekrarını iki ayrı görüşme olayı sayma. Aynı event'in yeniden işlenmesi de sayacı artırmaz. Güvenlik reddi, ödeme reddi ve görüşmeyi reddetme farklı sayaçlardır; aynı cevap ilgili birden çok kuralı tetikliyorsa eylem tek ve kaynaklı olsun.
- 'Bir botla konuşmak istemiyorum, insan istiyorum' insan talebini korur; sırf olumsuz kelime var diye görüşmeyi kapatma. İlk yardım teklifine 'hayır, insan istiyorum' ısrardır; üçüncü kez talep etmesini bekleme.
- İnsan talebi yardım teklifini kabul ederek devam ettikten sonra yeniden gelirse görüşme boyunca daha önce yardım önerildiği unutulmaz. Daha önce verilmiş yardım teklifinin gerçekten sunulması ile yalnız hazırlanması ayrılır.
- İlk konuşmama bildiriminde kimlik öncesi güvenlik açıklaması yalnız güvenlik sorusuna ret bağlamında kural 15'e dayanır; her aşamadaki ilk ret için aynı açıklama zorunlu değildir. Kimlik sonrası dersin 'uygun biçimde devamı anla' önerisi bir uygulama tercihidir, brief'te verilmiş zorunlu cümle değildir.

### Özel olayın mevcut teklife etkisi
Paid/dispute, aynı ürün için kaydedilmemiş anlaşmayı ve eski onayı kayıt kuyruğundan çıkarmalı. Yalnız status değiştirip geçerli onay snapshot'ında bırakmak yeterli değil. 'Yes, but I already paid that one' cevabında önce yes'i işleyip banka çağrısı başlatma.

Önceden başarıyla recorded olmuş ürün için sonradan gelen beyan, bankadaki kaydı geri almış gibi davranamaz. Kural 36, müşteri bilgilendirmesi ve final outcome birlikte ele alınır; bu çelişkili geç olay kaynakta açık değilse yorum kaydı gerekir. Belirsiz kesişim için yeni banka aracı veya iptal yetkisi icat etme.

B'de paid/dispute yalnız ilgili ürünü sonuçlandırır, diğer ürünlerle API sırasına göre devam edilir. Bir üründeki anlaşmazlık bütün ürünlere yayılmaz. Notlar transfer olmayacağı kapanış aşamasına kadar yerelde bekler: herhangi bir transferde hiç add_note yok. Başarılı promise varsa korunur; hiçbir promise yoksa bütün ürünler paid olduğunda paid, aksi hâlde API sırasındaki ilk paid olmayan ürünün nedeni geçerlidir. Olayların konuşmada geliş sırası ile API ürün sırasını karıştırma. A hiçbir add_note çağırmaz.

### Transfer ve bilgi soruları için işlem sınırı
Queue'yu enum ile sınırlamak yalnız yazım hatasını önler; general/support/restructuring arasından politika açısından yanlış olanı seçmeyi önlemez. Kod güncel olay ve durumdan transfer niyeti üretmeli; destek kabulü, insan ısrarı veya uygun plan talebini kanıtlamalı. Customer_id çağrı durumundan gelir. Başarılı transfer sonrası yeni banka işlemleri için kapanış dışında yol açılmamalı; transfer sonucu bilinmiyorsa kesin başarı iddiası yok. Brief'in belirtmediği transfer hata/retry davranışı ayrı eksik olarak gösterilir.

Scam veya bilinmeyen bilgi sorusu mümkünse kısa cevaplanır ve aynı pending göreve dönülür: identity yeniden DOB'dan başlamaz, ödeme teklifi kaybolmaz, read-back sorusu ile yeni soru karışmaz. Kimlik öncesi borcu doğrulayan cevaba dönüşmez. 'Müşteri hizmetleri numarası nedir?' sorusunda kaynakta numara yoksa üretme; resmî banka kanalından bulabileceğini belirten kaynakla uyumlu yönlendirme değerlendirilebilir. Harici arama/API veya yeni bilgi tabanı bu yarışma akışına eklenmez.

### Güncel kodda dikkat gerektiren açıklar
- negotiation.py paid/dispute durumları var; fakat insan talebine ait yardım-teklifi sayacı olay motorunda görünmüyor. components.py transferi hâlâ modelin kural yorumuna bırakıyor. 'Tüm özel durumlar artık deterministik' iddiası doğru olmaz.
- stop olayı, ayrı iki-bildirim sayacı olmadan open/offered ürünleri refused yapıyor. Kural 45 için erken kapanış riski; 28–33 bölümündeki aynı bulguyu burada çağrı geneli durumla çöz.
- paid/dispute dalı açıkça belirtilen ürünün önceki durumuna bakmadan status atıyor. recorded ürünün sonradan paid/dispute ile ezilmesini önleyen koşul bu dalda görünmüyor; erişilebilirlik ve kayıt sonrası müşteri mesajı ayrıca sınanmalı.
- transfer kuyruğu model_field; yeni API enum eşlemesi doğru olsa bile kaynak koşulu guard'ı ayrıca gerekiyor. Aşamalar arası insan talebi sürekliliğini ve hardship + restructuring birleşimini kontrol et.
- Serbest soru yanıtı alanı, yalnız metin temizleme/uzunluk sınırıyla doğrulanmış bilgiye dönüşmez. Scam için kısa kaynaklı şablon ve bilinmeyen bilgi için açık yanıt tercih edilir. Sayı içermemesi bile uydurma gerekçeyi engellemez.
- Özel olaylar yalnız negotiate node'unda ele alınırsa read-back/identity/relay sırasında kaçabilir. Her müşteri mesajı alınabilen aşama için hangi olayların desteklendiği küçük kapsam tablosuyla gösterilmeli; terminal veya otomatik API aşamalarının kesinti desteği varsayılmamalı.

### Hedef test paketi
| Dizi | Beklenen |
|---|---|
| 'Bu gecikmiş tutarı ödedim' / 'krediyi yıllar önce kapattım' | paid / dispute; ikisine aynı cevap verilmez |
| Belirsiz ödeme veya kısmi ödeme beyanı | Kapsam açıklaması; otomatik tüm borç paid yok |
| İlk insan isteği kimlik öncesinde, ikinci başka node'da | Bir yardım teklifi; general transfer; borç açıklama yok |
| 'Bot istemiyorum, insan istiyorum' | Stop kapanışı yerine insan talebi süreci |
| İki gerçek konuşmama olayı / aynı olayın tekrarı | İlkinde uygun kapanış; ikincisinde çift sayma yok |
| İş kaybı + düşük taksit isteği | 32 önceliği; doğrudan restructuring yok |
| '200 öderim' / 'aylık taksiti 200 yapın' | Gönüllü ödeme teklifi / yeni plan talebi ayrımı |
| Scam sorusu + ödeme tarihi | Kaynaklı yanıt ve tarih işleme; teklif kaybolmaz |
| Bilinmeyen faiz oranı veya telefon numarası | Uydurma bilgi yok; bilinmiyor sıfır sayılmaz |
| B kart paid, kredi dispute, üçüncü üründe promise | Yalnız ilgili ürün sonuçları, doğru notlar ve promise kapanışı |
| B dispute sonrası transfer | Hiç not yazılmaz; kaydedilmemiş vaatler yazılmaz |
| Read-back sırasında 'onu zaten ödedim' | İlgili ürün kayıt kuyruğundan çıkar; eski onayla yazılmaz |
| Başarılı kayıttan sonra itiraz/değişiklik | Kayıt silinmiş gibi status ezilmez; kaynaklı yönlendirme |
| Transfer aracı hata verir | Başarılı transfer iddiası yok; açık hata politikası/eksik kaydı |

Önce sentetik cümle çiftleriyle anlam çıkarımını, ardından olay dizileriyle runtime kararını ayrı test et. Sadece intent etiketini elle verip başarılı runtime çalıştırmak gerçek konuşma doğruluğu değildir. Kimlik öncesi, müzakere ve read-back bağlamlarında aynı ifadeyi sınayarak kapsam kaçağı ara. Sonra mevcut ilgili public ölçüm grubuna ekle; bağımsız ikinci test kampanyasıyla gereksiz kullanım yapma.

### Uygulama kararı
Öncelik: çağrı genelinde insan talebi/konuşmama durumunu tutmak; paid-dispute kapsamını ve bekleyen kayıt iptalini doğru yapmak; transfer koşullarını işlem sınırına almak; bilgi sorularından doğru aşamaya dönmek. Brief'e dayanmayan evrensel niyet sıralaması kurma. Kaynak tetikleyicisi → kapsam → öncelik → durum değişikliği → konuşma → banka eylemi → kanıt zinciriyle ilerle. Başarı hedefi, bu özel olayları puan kaybettiren yanlış promise veya yanlış kapanışa dönüştürmemektir.

## Kurallar 46–47: tek kapanış, gerçek sonuç ve son işlem sırası

11 Ekim 2026. Kaynaklar: Ders Closing; Brief A kapanış tablosu ve 46–47; Brief B kapanış ve transfer hükümleri; tools/openapi.json /close_call; tools/score.py; negotiation.py FINISH/NOTES_NEXT ve components.py t_close/close_one/finish_say/wrap_up. Statik inceleme; kod değişikliği veya yeni simülasyon yapılmadı.

### Değerlendirme
Ortak kapanış denetimi doğru yaklaşım. Ancak 'tek node var' veya 'close_started=true' tek başına her çağrıda tam bir banka kapanışı garantisi değildir. Bütün normal, erken çıkış, hata, transfer ve maksimum tur yolları aynı yetki/sıra kontrollerinden geçmelidir. Çalışan akışı kökten değiştirmek yerine ortak karar fonksiyonu ve gönderim guard'ı mevcut yollara uygulanabilir; tek node'a birleştirme uygulama seçeneğidir.

Üç olayı ayır: veda mesajı, bankaya close_call ve Freya telefon oturumunun sonlanması. Bunların yalnız biri başarılı diye bütün görüşme başarıyla kapanmış sayılmaz.

### Kaynak sözleşmesi
- Teşekkür ve veda close_call'dan önce. close_call tam bir kez ve son banka aracı. Ardından platformun sessiz end_call işlemi olabilir; bu banka aracıyla aynı şey değildir.
- promise için en az bir gerçek başarılı kayıt gerekir; yalnız müşteri onayı yetmez. transferred için güncel başarılı transfer sonucu gerekir; aktarım niyeti veya seçilen queue yetmez. callback sonucu da başarılı callback kaydına dayanmalı.
- paid müşteri beyanı kaynaklı olabilir; bankadan ödeme teyidi icat edilmez. not_verified/not_reached/refused gibi sonuçlar kaynaklı olay ve sayaçlarla belirlenir. Her outcome için banka yazma sonucu aramak da yanlıştır: kanıt türü kurala göre değişir.
- Başarılı transfer, önceden başarılı promise olsa da transferred sonucunu belirler; promise kaydı korunur. A'da add_note hiçbir yolda yok.
- B'de transfer yoksa en az bir başarılı promise → promise. Hiç promise yoksa bütün ürünlerin paid olması → paid; aksi hâlde API ürün sırasındaki ilk paid olmayan sonucun nedeni → no_promise. Not/olay geliş sırası sonuç önceliği değildir.
- promise ve paid için reason alanını istek gövdesinden çıkar; 'none', boş metin veya keyfî null ile ikame etme. Diğer outcome/reason çiftleri brief tablosuyla doğrulanır. API'nin reason'ı serbest string kabul etmesi yeni banka nedeni uydurma yetkisi değildir.

### Önerilen kapanış sözleşmesi
1. **Kanıta dayalı sonuç hesabı:** saf finalize kararı doğrulama/ulaşılma durumunu, ürün sonuçlarını, gerçek transfer/kayıt/callback sonuçlarını ve terminal nedeni okur. Açık ürün durumunu otomatik refused'a çevirmek, gerçek müşteri reddi kanıtı değildir. Çözülmemiş işlem varsa normal finalizasyona sessizce geçilmez.
2. **İzinli çift + doğru anlam:** outcome/reason tablosunda bulunması gerekli ama yeterli değil. Örneğin no_promise/refused geçerli çifttir, fakat müşteri hiç reddetmediyse yanlış kayıttır. Karara kaynak kural ve kanıt referansı eşlik etsin.
3. **Durum aşamaları:** finalizing, farewell_issued, close_in_flight, close_succeeded/failed/unknown ve session_ended ayrı tutulur. Bunlar yeni node sayısı zorunluluğu değildir. Veda metninin hazırlanması söylenmesi değildir; platformun gözlediği mesaj/ses sırası esas alınır ve gözlenemeyen ses tamamlanması garanti edilmez.
4. **Tek gönderim sahibi:** close_call erişen her yol ortak bir guard'dan geçer. Aynı olay/yeniden giriş ikinci istek oluşturmasın. Outcome, reason ve customer_id gönderim anında değişmez bir kapanış snapshot'ından gelsin; model yeniden sonuç seçmesin.
5. **Kapanış kilidi:** close_call başladıktan sonra yeni promise, note, callback veya transfer başlatılamasın. Öncesindeki kesinti penceresinde işlenen bir transfer/teklif değişikliği varsa eski kapanış snapshot'ı geçersizleşsin. Platformun gerçek kesinti desteği ölçülmeden bu davranış sağlanmış sayılmaz.
6. **B notları:** transfer ihtimali değerlendirilmeden not gönderme. Terminal aşamada gerekli notların tamamlanması izlenir; planlanmış not ile başarılı not ayrı. Başarısız notu kuyruğun başından çıkardık diye başarı sayma. Not hatası için kaynakta olmayan retry/kapanış hükmü icat etme.
7. **Sonuç ve telefon:** close yanıtını kontrol et. Telefonun kapandığı gözlemi bankanın kapanışı kabul ettiği kanıtı değildir. Sınırlı hata yolunda oturumun nasıl sonlandırılacağı açıkça kaydedilir; başarısız banka kapanışı raporda görünür kalır.

### Veda, not ve transfer sırası
A için tipik sıra: gereken başarı/başarısızlık açıklaması → teşekkür/veda → close_call → sessiz end_call.

B'de notlar close_call'dan önce olmalı; 47, vedanın tüm banka araçlarından önce olmasını istemiyor. Mevcut veda→notlar→close sırası bu nedenle tek başına kural ihlali değildir. Fakat not gecikmesinde müşteri vedadan sonra telefonu kapatabilir. Notlar→veda→close seçeneği de notlar sonrasında yeni transfer talebi işlenirse 'transferden önce de hiç not yok' hükmüyle çatışabilir. Bu tradeoff gerçek platform kesinti davranışıyla test edilmeli; gelişigüzel sıra değiştirme veya 'atomik kapanış' garantisi ilan etme. Gereksiz müşteri turu eklemeden kapanış zincirini kısa tut, işlem gecikmesini ölç.

### Hata ve exactly-once sınırı
OpenAPI, close_call HTTP 500 için kayıt yapılmadığını ve tekrar edilebileceğini söyler; Brief A ise tam bir close_call ister. Bu iki ifade başarısız deneme sayımında belirsizlik oluşturur. Ödeme sözüne özel bir-retry kuralını close_call'a kopyalama. Resmî açıklama/test kanıtı yoksa mevcut otomatik retry=0 korunarak bu sınır görünür raporlanmalı; ne tek başarılı kayıt ne de tek deneme yorumu kesinleştirilmiş gibi sunulmalı.

Timeout'ta bankanın işleyip işlemediği bilinmeyebilir. Belgelenmemiş idempotency anahtarı veya sorgulama endpoint'i ekleme. Yerel guard tekrarlı yürütmeyi azaltır, yanıt kaybında dağıtık exactly-once garantisi vermez. failed/unknown iç durumları yeni outcome/reason değildir. Hata yolunu keyfî refused'a çevirerek yeşil sonuç üretme.

### Güncel kodda somut kontrol noktaları
- Müzakere dışı identity/third_party/account_error/wrap_up yollarında t_close var; müzakere sonunda close_one var. Merkezi kapanış henüz bütün yolları tekleştirmiş değil. Ortak guard her iki mekanizmayı kapsamalı.
- close_one, yanıt sonucu ayrımı olmadan hangup'a geçiyor. close_succeeded ayrı kaydedilmeli; otomatik telefon kapanışı banka başarısıyla karıştırılmamalı.
- FINISH open/offered ürünleri refused, agreed ürünleri service_error'a dönüştürüyor. Bu dönüşüm, gerçekten reddedilmemiş veya iki başarısız deneme yaşamamış üründe hatayı yanlış sınıflandırabilir. Kaynaklı terminal olaya ve gerçek işlem sonucuna dayanmalı.
- FINISH exception halinde teknik fallback sonucu seçiyor. Eksik state veya yazılım hatası normal banka olayı gibi gizlenmemeli; kaynak dayanağı ve iç hata ayrı görünmeli.
- NOTES_NEXT notu gönderimden önce kuyruktan çıkarıyor; note_one sonucunu kontrol eden açık bir başarı aşaması görünmüyor. Zorunlu not eksikliği final kontrolünde yakalanmalı.
- t_close preSpeech veda içeriyor; wrap_up da modele veda etmesini söylüyor. Tekrar veda/ek gecikme olup olmadığı transcript'te kontrol edilmeli. preSpeech'in varlığı ses sırasının canlı kanıtı değildir.
- close_one reason pre-hook'u boş/çözülmemiş değeri kaldırıyor; reason gerekli bir outcome için de eksik değer gizlenmemeli. Önce outcome/reason çifti doğrulanmalı, sonra yalnız gerekçesiz sonuçlarda alan kaldırılmalı.
- max_node_turns→wrap_up yolu modelden sonuç istiyor; tur limiti müşteri reddi değildir. Sonsuz döngüyü durdurmak için gereken teknik çıkış ile doğru politika sonucu ayrılmalı.

### Değerlendirme kapsamını genişletmeden tamamlayan testler
tools/score.py outcome/reason, kayıtlar ve son banka çağrısının close_call olmasını kontrol ediyor. Son çağrı kontrolü tek başına çağrı sayısının bir olduğunu veya vedanın önce söylendiğini kanıtlamaz. Organizatör scorer'ını değiştirme; ayrı geliştirme invariant kontrolüyle eksik ölçümleri tamamla.

| Senaryo | Kabul ölçütü |
|---|---|
| A'nın bütün terminal nedenleri | Kaynaklı doğru çift; promise/paid reason alanı yok |
| Promise başarı → transfer başarı | Promise korunur, tek transferred kapanışı |
| Transfer isteği var fakat araç başarısız | Sahte transferred yok; hata/belirsizlik görünür |
| B bir promise + başka ürün service_error | Promise kapanışı; gereken ürün notu; doğru sözlü açıklama |
| B hepsi paid / mixed paid-dispute-refused | Paid / API sırasındaki ilk paid olmayan neden |
| Aynı kapanış olayı iki kez, node yeniden girişi | İkinci close isteği yok |
| Kimlik/üçüncü kişi ve wrap_up çıkışları | Aynı kapanış kontrolleri; borç açıklama yok |
| Close sonrasında başka banka tool'u | Kontrol başarısız; normal workflow'da engellenir |
| Veda hazır ama söylenmeden close | Kontrol başarısız; mesaj sırası kanıtı gerekir |
| Close HTTP 200 + ok=false / timeout | Banka başarısı ilan edilmez; raporda başarısız/unknown ayrımı |
| B zorunlu not başarısız | Kuyruk boş diye bütün notlar başarılı sayılmaz |
| Kapanışa yaklaşırken insan talebi | Desteklenen kesinti penceresinde güncel sonuç; eski promise outcome ile yarış yok |
| Tur limiti veya bozuk state | Keyfî refused üretme yok; teknik neden görünür |

Kanıt: gerçek banka araç çağrılarında close sayısı ve son araç; outcome/reason gövdesi; veda mesajının sırası; banka kapanış sonucu; platform ended durumu; B not/transfer kayıtları. Yerel sentetik olay testleri, platform sıra kontrolleri ve mevcut public tekrarları ayrı raporlanır. Çalışan aday korunarak mevcut test kampanyasına eklenir; bütün testleri gerekçesiz yeniden koşma.

### Brief A tasarım turunun tamamlanması ve uygulamaya aktarım
1–47 tasarım incelemesi tamamlandı. Bu, bütün kuralların uygulandığı veya canlı doğrulandığı anlamına gelmez. Önceki statik bulgular zaman damgalı aday tespitleridir; Claude kodu değiştirmişse uygulanmış düzeltmeyi yeniden yazma.

Belgeyi uygularken kısa bir kural matrisi üret: kaynak kural → mevcut bileşen → kalan açık → test kanıtı → durum (öneri/uygulandı/yerel test/platform testi). Aynı açık birden çok bölümde anlatılmışsa tek iş kalemi olsun. İlk öncelikler onay-kayıt bağı, çok ürünlü durum, hardship/transfer önceliği ve bütün yollarda ortak kapanış kontrolüdür. Sonra hedefli test → ilgili A/B regresyonları → sabit builder ile bağımsız üretim → seçilen adayın yayın/test/export eşleşmesi ve teslim provası. Uzun notların varlığı değil, bu zincirin ölçülen doğruluğu yarışma performansını artırır.

## Sonraki bölüm
Brief B ayrı bir tasarım turu olarak incelenebilir. Yukarıdaki B çapraz kontrolleri, bütün B değişikliklerinin bağımsız incelemesinin tamamlandığı anlamına gelmez.
