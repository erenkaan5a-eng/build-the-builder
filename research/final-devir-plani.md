# Final devir planı (11 Ekim 2026, İstanbul saati)

Teslim: 23.00'ten önce kullanıcı yavuz@freyavoice.ai adresine üç dosya gönderir (submission.json, export edilen workflow,
üreten koşunun trace'i + tam oturum günlüğü). E-postayı Claude göndermez. Dosyalar bildirilen commit'te bulunur.

## Kontrol noktaları
| zaman | yapılacak | kim |
|---|---|---|
| ~21.00 | Drive klasörü "Build the Builder - Final Case", organizatörün yeni e-postaları ve site (freyavoice.ai/hackathon) yeniden kontrol: yeni/değişmiş belge var mı? Claude: Drive bağlayıcısı klasör içeriğini listeleyemiyor; site bu ortamdan açılmıyor; Gmail bağlayıcısıyla organizatör e-postaları aranabilir. Erişilemeyen kaynak "kontrol edildi" sayılmaz: güncel paketi kullanıcı yükler | kullanıcı + Claude |
| ~22.15 | Teslimden önce aynı kontrol (son belge değişikliği seçilen koşudan sonra mı?) | kullanıcı + Claude |
| ~22.30 | Seçilen koşu, export, trace, oturum günlükleri, submission.json son hâli; kullanıcıya kontrol listesi | Claude |

## Yeni belge gelince
1. Yeni alındı klasörü `final/package/rN-<zaman>/` (orijinaller aynen, değiştirilmez); `RECEIPTS.md`'ye zaman, kaynak, sha256.
2. Önceki alındıyla dosya farkı: eklenen / silinen / hash'i değişen dosyalar (`final/package/rN.diff.md`).
3. Builder en güncel tam klasörde yeniden koşar (`scripts/run_final.sh`); belgeleri builder kendisi işler, ajana elle yama yok.
   Her koşu kendi aday klasörü, trace'i ve `.sessions/` günlüğüyle kalır; hiçbiri ezilmez.
4. Mock'a bağlı bir sözleşme/test müşterisi değiştiyse mock da yeniden yazılır, testlenir, kullanıcı yeniden deploy eder.

## Seçilen koşunun kaynakları
Trace'in `INPUT` satırları (dosya adı + sha256) ve aday klasöründeki `case_inventory.json` hangi alındının hangi dosyalarını
kullandığını gösterir; `make_submission.py` seçilen aday + trace + mock URL + commit eşleşmesini denetler.

## Bekleyen (paket eksik: r1 yalnız BRIEF.md + akış PDF'i)
- Mock: servis sözleşmesi (entegrasyon belgesi bölüm 6) ve test müşterileri gelmeden yazılmaz; uç nokta/alan/müşteri uydurulmaz.
- Builder koşusu: tam paket ve mock URL gelmeden final koşusu yapılmaz.
