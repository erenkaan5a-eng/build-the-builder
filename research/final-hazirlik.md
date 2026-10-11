# Final hazırlığı (11 Ekim 2026, 20.00 İstanbul öncesi)

Kaynak: kullanıcının aktardığı final şartları. `https://www.freyavoice.ai/hackathon` bu bulut ortamının ağ politikasında
engelli (proxy 403); sayfa metni buradan **doğrulanamadı**. Builder kodu/mantığı dondurma hükmü bu oturumda hiçbir resmî
metinde görülmedi (sayfa okunamadı; kitteki README'de böyle bir hüküm yok). Kit README'sinin 30 dk/build sınırı korunuyor
(`--budget-min 30` varsayılan); kaldırıldığı doğrulanmadı. Eski pass^3 ve vaat tutarı eşitlik kuralı final kuralı diye sunulmaz.

## Durum: hazır / eksik / erişim gerekiyor
| konu | durum |
|---|---|
| Girdi `python3 builder/build.py {case_folder} {mock_url}` | **hazır** (57d2035): klasör + https mock URL; eski `{brief} {tool_api}` biçimi de çalışıyor |
| Belge okuma: Markdown/txt/JSON/YAML, DOCX (başlık seviyesi, tablolar), XLSX (sayfa = tablo), PDF (pypdf / pdftotext), CSV | **hazır**, sentetik Türkçe belgelerle 15 test |
| Okuma sırası BRIEF.md → README.md → diğerleri; dosya başlığıyla kaynak korunur; "son tarihli kazanır" varsayımı yok | **hazır** |
| Okunamayan belge / BRIEF.md yok | görünür PROBLEM; release kontrolü başarısız sayılır, `--out` yazılmaz |
| Servis sözleşmesi → mock URL | **hazır** klasördeki tek OpenAPI JSON/YAML; birden fazla ya da hiç yoksa açık hata, `--contract FILE` ile seçilir; uç nokta uydurulmaz |
| Sözleşme OpenAPI değilse (yalnız Word/PDF/Markdown) | **eksik**: builder bunu makine-okur sözleşmeye çeviremez; açık hata ile durur. Paket açılınca: mock için sözleşmeyi zaten yazacağız; o JSON `--contract` ile verilebilir (mock sözleşmesinin yazılması ayrı, açıkça istenen iştir) |
| Sözleşmede farklı operasyon adları | **hazır** (295a24b): policy `operations` ile sabit bileşen rollerini (kimlik doğrulama, hesap, söz, not, geri arama, aktarma, kapanış) sözleşmenin adlarına bağlar; bilinmeyen ad / çakışma / iki role tek operasyon = doğrulama hatası (tek onarım çağrısı), tahmin yok. Yeniden adlandırılmış pratik sözleşmesinde ana yol üretildi ve lint'ten geçti (tests/test_role_binding.py, 14 test). Pratik API'de çıktı değişmedi (aynı workflow) |
| `$ref` şemaları, 201 gibi 2xx yanıtlar | **hazır** (295a24b): toolspec, lint ve mock çekirdeği yerel `$ref`'leri çözer (döngü güvenli); ilk 2xx başarı şeması okunur |
| Kalan sözleşme riski | **risk**: rol semantiği farklıysa (ör. kimlik tek çağrıda tüm alanlarla, hesap tek nesne/dizi değil, GET + yol parametresi, bir rolün karşılığı yok) ana yol doğrulamada açık nedenle durur → `--mode auto` yedek yolu (Sonnet ajanı + skill); yedek yol ana yol kadar ölçülmedi |
| Organizatörün başka workspace'i | **hazır** (a2ec5fa): depoya işlenmiş `.freya-agents.json` kimliği o workspace'te yoksa (404/403/400) yeni workflow açılır, eski kayıt `@unreachable` altında saklanır; 5xx'te durur; oluşturma asla tekrar denenmez (çift workflow yok). tests/test_publish_slot.py |
| Türkçe | gün/ay adları policy'den (692df55); konuşma dili policy `language`; tutar/tarih modeli olaylara çeviriyor (modele bağlı) |
| Trace | başlangıç/bitiş, kaynak commit + builder ağacı, her girdi dosyası + hash, her model çağrısı (model, amaç, token), Freya workflow/agent kimliği ve yayın sürümü, düğüm/araç sayıları, testler ve sonuçları, export hash'i (SUMMARY satırı), bilinen açıklar |
| Koşuların birbirini ezmemesi | aday klasörü ve trace dosyası asla yeniden kullanılmaz; `scripts/run_final.sh` terminal günlüğünü zaman damgalı yazar, `pipefail` ile builder'ın çıkış kodunu korur |
| Önceden çıkarılmış policy | final komutu `--reuse-policy` içermez; bu seçenek yalnız geliştirme içindir ve girdi hash'leri tutmazsa reddeder |
| Pratik müşteri verisi | ana yol yalnız verilen klasörü/brief'i ve sözleşmeyi okur; `public-test-set.json` yalnız `--practice` (geliştirme) ile okunur |
| Elle yama yok | düzeltme builder'da yapılır, yeni koşu yeni aday klasörü + trace üretir; `scripts/make_submission.py` export ile trace'in aynı koşuya ait olduğunu, commit'in HEAD olduğunu denetler |
| `submission.json` | **hazır şablon aracı** (`scripts/make_submission.py`): team/members verilmeden yazmaz; isim/e-posta uydurmaz |
| Cloudflare mock | **erişim gerekiyor**: `api.cloudflare.com` ağ politikasında engelli; Cloudflare kimliği ortamda yok. İskelet hazır: workers/bank-mock (README) |
| Temiz checkout | Python 3.10+, `pip install claude-agent-sdk`; belge okuyucular stdlib (XLSX için openpyxl varsa), PDF için `pypdf` ya da `pdftotext`, YAML sözleşme için `pyyaml`. Temiz klonda (a2ec5fa, env.sh yok) denendi: `--help` çalışıyor; sözleşmesiz klasör → görünür PROBLEM, çıkış kodu 2, trace'ler ezilmiyor; kimlik bilgisi yokluğu trace'te yalnız var/yok olarak yazılıyor |

## Final akışı (paket açılınca)
1. `BRIEF.md`, `README.md`, sonra tüm dosyaların envanteri (`python3 -c "import sys; sys.path.insert(0,'builder'); import case_input, json; print(json.dumps(case_input.load_case('<klasör>')['inventory'], indent=1, ensure_ascii=False))"`).
2. Mock: sözleşme + test müşterilerinden `workers/bank-mock` handler'ları; Node testleri; deploy; mock URL'yi örnek istekle doğrula.
3. `scripts/run_final.sh <klasör> <mock_url>` (gerekirse `--contract FILE`). Gerekirse genel hata düzeltmesi → commit → yeni koşu (yeni aday + trace).
4. Seçilen koşu: `python3 scripts/make_submission.py candidates/final-<slot>/<zaman> --team ... --member ... --repo ... --mock-url ...`; export + trace + submission.json commit/push.

## Ölçülmüş adaylar (dokunulmadı)
loc-a v3 `1b567c6fe1f24904` (canlıda yayınlı değil; v4 yayında, doğrulanamadı), loc-ab v2 `e1d03845876722e3` (canlıda yayınlı). research/baseline-manifest.json. 39 koşuluk public ölçüm final hazırlığı nedeniyle başlatılmadı; kullanılan simülasyon: 10/60.
