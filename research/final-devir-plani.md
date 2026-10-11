# Final devir planı (11 Ekim 2026, İstanbul saati)

Teslim: 23.00'ten önce kullanıcı yavuz@freyavoice.ai adresine üç dosya gönderir (submission.json, export edilen workflow,
üreten koşunun trace'i + tam oturum günlüğü). E-postayı Claude göndermez. Dosyalar bildirilen commit'te bulunur.

## Kontrol noktaları
| zaman | yapılacak | kim |
|---|---|---|
| ~21.00 | Drive klasörü "Build the Builder - Final Case", organizatörün yeni e-postaları ve site (freyavoice.ai/hackathon) yeniden kontrol: yeni/değişmiş belge var mı? Claude: Drive bağlayıcısı klasör içeriğini listeleyemiyor; site bu ortamdan açılmıyor; Gmail bağlayıcısı 'Forbidden' (11 Ekim 20.20) → e-postaları kullanıcı kontrol eder. Erişilemeyen kaynak "kontrol edildi" sayılmaz: güncel paketi kullanıcı yükler | kullanıcı + Claude |
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

## Teslim adımları (koşu seçildikten sonra)
1. Seçilen koşunun çıktıları (aday klasörü, trace, `.sessions/`, terminal günlüğü, `.freya-agents.json`) commit + push.
2. `python3 scripts/make_submission.py candidates/<slot>/<zaman> --team "<takım>" --member "<Ad Soyad>,<e-posta>" [...] --repo https://github.com/erenkaan5a-eng/build-the-builder --mock-url <mock_url>`
   (takım/üye bilgisini kullanıcı verir; uydurulmaz). Araç: koşu commit'i ile HEAD arasında builder'ı etkileyen değişiklik yok,
   export/trace/oturum günlükleri HEAD'de commit'li, gizli değer yok, mock_url koşununkiyle aynı.
3. `submission.json`, `submission/final.workflow.json`, `submission/final.trace-bundle.zip` commit + push.
4. Kullanıcı bu üç dosyayı 23.00'ten önce yavuz@freyavoice.ai adresine kendisi gönderir.

## Kontrol kaydı
- 21.06 İstanbul (18:06Z): Drive bağlayıcısı: "Build the Builder - Final Case" klasörünün modifiedTime'ı 17:21:15Z; r3 ZIP'i 17:56:43Z'de dışa aktarıldı → klasörün kendisi o zamandan beri değişmedi. Bağlayıcı alt dosyaları listeleyemiyor; alt klasördeki bir dosya değişikliği klasör zamanına yansımayabilir, bu yüzden kesin değil. Yeni yükleme yok (son yükleme ZIP 17:57:40Z). E-posta ve site: buradan erişim yok, kontrolü kullanıcıda.
- 22.22 İstanbul (19:22Z): Drive klasörü modifiedTime hâlâ 17:21:15Z (r3 dışa aktarımı 17:56:43Z'den önce); yeni yükleme yok. Seçilen koşu A, r3 alındısını kullandı; bilinen en güncel alındı r3. E-posta/site kontrolü kullanıcıda (buradan erişim yok).
