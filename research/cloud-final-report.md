# Bulut oturumu — ayrıntılı kanıt raporu (11 Ekim 2026)

Kısa özet ve sonraki adım sohbet mesajındadır; burası kanıt dosyasıdır. Canlı sonuçlar yalnız adı geçen aday/sürüme aittir.
Yerel test geçişi canlı başarı, public başarı gizli brief başarısı değildir. Başarı garantisi yoktur.

## 1. Zaten tamamlanmış olan (buluta gelen kaynak a5de722)
- 11 Ekim yerel düzeltmeleri dosyalarda mevcuttu: parçalı tutar/tarih koruma, tam paket onayı + iki onay yolunun ortak kontrolü, REC_NEXT guard'ı, not sonuç izleme, FINISH "hazır değil", close_check, hardship_go, `--local-only`, regresyon/yapı testleri.
- Testler bulutta yeniden koşuldu: müzakere 53 kontrol (günlükteki "54" = `check(` sayımı, `def` dahil), regresyon 24, tarih 14, yapı 18; 0 hata.
- Kaynak kimliği `84894192a420329c` yeniden üretilemedi (yöntem belgelenmemiş); içerikle doğrulandı. Yerel `results/` (ham n6 sonuçları) bulutta yok.

## 2. Ne değişti ve neden (commit sırasıyla)
| commit | değişiklik | neden / kanıt |
|---|---|---|
| e2c1369 | opt-in bulut proxy modu (`FREYA_AUTH_VIA_PROXY=1`), kit dosyaları değişmeden | `score.py` anahtar yoksa KeyError; proxy başlıkları ekliyor (düşük etkili GET'lerle doğrulandı) |
| e2c1369 | A32: zorluk + gönüllü tarih/tutar aynı mesajda → öneri bekletilir, empati+destek teklifi tek sahip (kod), teklif cevaplanınca öneri tarih/tutar kurallarıyla işlenir; `offer_named` ile yönlendirme; zorluk sonrası ikna yok (`hs`); `all` olayları destek teklifi bekleyen ürünlere ulaşır; answer alanı zorluk turunda düşer; rec_next blocked → neg_flag temizlenir | 8 yeni yerel test eski motorda başarısız (research/cloud-evidence/regress-new-tests-on-old-engine.txt): çift empati, "işimi kaybettim, ödeyemem" tek mesajda destek teklifi cevapsız kapanış, `all` kapsam hatası, bayat `record` bayrağı |
| 0e344fc | A45 sayacı policy'den (`stop_statements_to_close`; yoksa eski davranış) | motor ilk "konuşmak istemiyorum"da kapatıyordu; A45 "iki kez" diyor |
| 59e0ba2 | manifest'e destek sınırı (kod / model / kodla desteklenmeyen) | eski trace'ler kodun uyguladığı kuralları da "modelde" listeliyordu |
| c1d0646 | release davranış kontrolüne yalnız platform 5xx için bütçe içinde sınırlı tekrar; recheck aracı | 01:49–01:53 UTC chat 503/502 release'i düşürdü; finalde elle adım gerekmesin |
| 23f0227 | zorluk tüm açık ürünleri kapsar; anlaşılmış ürün tarihini korur | çıkarımın kaydettiği yorum ("hardship tüm çağrı") ile motor uyumu |
| c8de7c9 | **platform çökmesi düzeltmesi**: üretilen kodda `global` yok; test düzeneği kodu platform gibi fonksiyon içinde çalıştırır; lint `global/nonlocal` ve fonksiyon içinde derlenmeyen kodu reddeder; kırpılan ürünün deadline notu ayrı cümle | chat C2 (cl-a v1): motorun zorluk yolu her turda hata cümlesine düştü (NameError). Yerel düz `exec()` bunu gizliyordu |

## 3. A/B notları
Tam tablo: research/ab-kural-tablosu.md. Uygulanan / reddedilen / ertelenen özeti:
- Uygulandı (bu oturum): yukarıdaki A32, A45, B10 (blocked bayrağı), B kapsam düzeltmeleri; platform-benzeri test.
- Bilinçli olarak değiştirilmedi: A26/A30 "too much" = deneme 1 yorumu (kaynak metni destekliyor, PUB-06 bu yorumla 3/3 geçti; notlardaki alternatif uygulanmadı).
- Ertelendi (kalan risk): ortak tarih kökeni (`len(scope)>1`), `min(amt, full)` kırpması, 0.005 tolerans, float para, aynı tutarlı ürünlerde practice kontrolü, B1 kardinalite, callback sınırları ve tekrar sayısı (model), kimlik/ret/insan-isteği sayaçları (model), A22 this/next (model + takvim tablosu).

## 4. Yerel testler (son kod, c8de7c9 ve sonrası)
| dosya | kontrol | sonuç |
|---|---|---|
| tests/test_negotiation.py | 54 | 0 hata (T21b yeni iki-tur sırasına göre güncellendi; özellik daha sıkı) |
| tests/test_negotiation_regress.py | 48 | 0 hata (G1–G12, H1–H9, I1–I3 bu oturumda) |
| tests/test_date_tool.py | 14 | 0 hata |
| tests/test_generator_structure.py | 22 | 0 hata |
| tests/test_api_binding.py | 6 | 0 hata |
Motor testleri artık kodu platform gibi bir fonksiyon içinde çalıştırır. Bu yerel taklittir; banka yanıtları sayaç taklididir.

## 5. Adaylar ve canlı sonuçlar
| aday | kaynak | koşular | sonuç |
|---|---|---|---|
| cl-a v1 (b2601999470a02c7) | 59e0ba2 | chat C2 | motor zorluk yolunda çöktü → GEÇERSİZ, ölçülmedi |
| cl-ab v1 (3390a84c8ad3f3ee) | 59e0ba2 | chat C3 | kısmi onay kayıt açmadı; tam onay → doğru 2 kayıt (kanıt geçerli, aday aynı hata nedeniyle emekli) |
| **cl-a v2** (233c8dfe1a7d9d91) | c8de7c9 | PUB-05, PUB-06, PUB-10 × 3; PUB-04, PUB-08 × 1 | **11/11 koşu**; PUB-05/06/10 pass^3 3/3 (bu alt kümede) |
| **cl-ab v2** (8abfb3c856c81f25) | c8de7c9 | PUB-11, PUB-12, PUB-13 × 3 | **9/9 koşu**; pass^3 3/3 |
| cl-a v2 varyasyon: zorluk + "Cuma 300" | c8de7c9 | × 3 | 2/3 (aşağıda) |
| konuşma tarzları (tek tekrar) | c8de7c9 | 5 | (aşağıda) |
- Simülasyon kimlikleri ve ham çıktılar: research/cloud-runs/*.json|log (call id'ler dahil).
- Gecikme: en yavaş tur medyanı 3–17 s; 17 s ve 24 s'lik koşularda run_cases "yavaş model" uyarısı; kapatan müşteri 0.
- n6 skorları (A 29/30, B 9/9) eski koda aittir; burada birleştirilmedi. Bu oturumda A'nın 10 vakasının yalnız 5'i ölçüldü (PUB-01/02/03/07/09 yeni kodla ölçülmedi).

## 6. PUB-05 ve gönüllü öneriyle zorluk
- PUB-05 × 3 (cl-a v2): üçü de geçti. Zorluk yönlendirmesi her koşuda borç bildiriminden sonraki ilk müşteri mesajında (`hardship_go`); empati + destek teklifi tek cümle, bir kez; destek reddi → `no_promise/hardship`. Müşteri iki koşuda zorluğu kimlik aşamasının hemen sonunda da söyledi; unutulmadı.
- Kalan risk (judge'a bağlı): destek reddi + "indirim?" turunda diyalog modeli olay aracını çağırırken kendi metnini de söyledi: 1. tekrarda "I cannot offer a discount. Would you like to make a payment for your personal loan?" (zorluk sonrası ödeme sorusu), 2–3. tekrarda kendi vedası. Judge kabul etti. Yapısal öneri: destek teklifine cevabı neg_relay'de çıkarımla deterministik yönlendirmek (model o turda konuşmaz). Build bütçesi bittiği için uygulanmadı/ölçülmedi.
- Zorluk + "Cuma 300" varyasyonu (experiments/variations/hardship-own-offer.json; beklenen değer brief'ten bağımsız türetildi): 2/3. Başarılı iki koşu tam tasarlandığı gibi: [proposes, hardship] → empati+destek teklifi → ret → "personal loan: 300.00 on Friday 16 October. Do you confirm?" → kayıt + SMS cümlesi. Başarısız koşuda simüle müşteri üç mesajı yarım gönderdi ("…but I", "…transferred,"); tutar/tarih hiç söylenmedi; ajan aldığı girdiyle A32'ye uygun kapattı. Sınıf: persona kesilmesi / değişken sonuç; dayanıklılık açığı: ajan yarım kalan cümlenin devamını istemiyor.
- Chat C2 (cl-a v1) bu yolu platformda kırık gösterdi; v2 düzeltmesi chat ile değil, bu varyasyonla platformda doğrulandı.

## 7. Yeni onay ve kapanış yollarının kanıtı
- Kısmi onay: chat C3 (cl-ab v1, onay kodu v2 ile aynı) — "Yes, for the credit card" → yalnız "Do you confirm?", kayıt yok; "Yes, I confirm both" → kart 300/30 Eki, kredi 900/23 Eki; ledger close promise.
- Tam paket + ürün başına kayıt + B notları: PUB-11 (3 promise), PUB-12 (1 promise + 2 refused not), PUB-13 (2 promise, farklı deadline) × 3 = 9/9.
- Kayıt hatası + tek tekrar: PUB-10 × 3 (create_promise iki kez, tek promise).
- close_check / "hazır değil": close_check her müzakere kapanışında çalışıyor (C3 düğüm yolu: close_one > close_check > hangup). "Hazır değil" yolu normal akışta tetiklenemez (yalnız REC_NEXT istisnasında); yerel testlerle (X3, H6) sınırlı ve döngüsüz olduğu gösterildi; platformda tetiklenmedi.
- "Evet ama değiştir": yerel (B3, T7, T17b); platformda ayrıca denenmedi (chat bütçesi).

## 8. Genelleme deneyleri
- Memo (experiments/memo-late-deadline): **çalıştırılmadı** — 4 builder çalıştırmasının ikisi, platformda bulunan çökme nedeniyle yeniden üretime gitti. Hazır olanlar: girdiler, vaka dosyası, bağımsız hesaplanmış beklenen tarih 2026-10-21 (15, 16, 19, 20, 21 Ekim), PUB-10 kontrolünün geçerliliği. Bir sonraki build hakkıyla çalıştırılmalı.
- API yeniden adlandırma: deterministik yarı **çalıştırıldı** (tests/test_api_binding.py 6/6 + negatif kontrol): eski bağ yeni API'ye karşı doğrulamada reddediliyor (onarım çağrısına gider); yeni adlara bağ verildiğinde üretici yalnız onları kullanıyor ve lint temiz. Çıkarım adımının yeni adları bulması (model çağrısı) **çalıştırılmadı**.
- Destek sınırı: her yeni adayın manifest'inde `support_boundary` (kod / model / kodla desteklenmeyen extra_rules).

## 9. En güvenilir mevcut aday ve doğrulanmamış kapsam
- A: cl-a v2 (workflow 0800b57a…, v2, hash 233c8dfe1a7d9d91). B: cl-ab v2 (workflow 06d2cae1…, v2, hash 8abfb3c856c81f25). Export'lar: candidates/cl-a/20261011-021737/export.json, candidates/cl-ab/20261011-021934/export.json.
- Doğrulanmamış: A'nın PUB-01/02/03/07/09'u yeni kodla; üçüncü kişi/callback, kimlik reddi, insan isteği, A45 iki kez ret, transfer kesintisi; memo ve API çıkarımı; gizli brief biçimleri.

## 10. Teslim
- Düzen ve yerel aktarma: research/teslim-duzeni.md. Giriş komutu: README_SUBMISSION.md. Final teslim, main'e merge, dış mesaj yapılmadı.
- Eksikler: organizatörün son teslim talimatı (kanal) bilinmiyor; final koşusu için Claude erişimi ve Freya anahtarlarının finalde kullanılacak ortamda doğrulanması gerekiyor (bulutta proxy ile çalıştı).

## 11. Kullanım
Bkz. research/cloud-progress.md "Kullanım sayacı". Ölçülemeyen: Claude abonelik kotasındaki yüzde etkisi (5 Opus çağrısı + bu oturum), Freya kredi bakiyesi değişimi (bakiye uç noktası kullanılmadı).
