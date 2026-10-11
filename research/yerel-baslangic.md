# Yerel devam: başlangıç, kaynak/aday eşleşmesi, düzeltilmiş başlangıç tablosu (11 Ekim 2026)

## Başlangıç
- Yerel klon `builder-dev` (a5de722, temiz). `origin/claude/lucid-fermat-vxp9u7` fetch edildi: `881ea3aca56f3e27d9be8fe1b43eaf201c7c0628` (beklenen commit ile aynı; uzak dal ilerlememiş).
- `builder-dev`, bulut dalının atasıdır; çakışma yok. Devam dalı: `local-hardening` (881ea3a'dan; upstream bağı kaldırıldı, push yapılmadı).
- Korunanlar: `env.sh`, `results/`, `out/`, `.personas.json` (git-ignored; checkout dokunmadı). Aktif python/simülasyon süreci yoktu.
- Kimlik bilgisi: normal `env.sh` yolu (`builder/common.py load_env`); bulut proxy modu kapalı (`FREYA_AUTH_VIA_PROXY` ne env.sh'ta ne ortamda). Değerler okunmadı/yazdırılmadı; build izi yalnız "set/absent" yazar.

## Ham bulut sonuçlarının yeniden sayımı
`research/cloud-runs/*.json` dosyalarının `final` alanlarından (her vaka satırı `passes/runs`):

| dosya | aday (agent) | geçen/koşu |
|---|---|---|
| cl-a-v2-pub04-08-x1 | cl-a v2 (91e04e98) | 2/2 |
| cl-a-v2-pub05-06-10-x3 | cl-a v2 | 9/9 |
| cl-ab-v2-pub11-12-13-x3 | cl-ab v2 (f97de421) | 9/9 |
| **standart hedefli toplam** | | **20/20** |
| cl-a-v2-var-hardship-own-offer-x3 | cl-a v2 | 2/3 |
| cl-a-v2-style-pieces-PUB-06 | cl-a v2 | 0/1 |
| cl-a-v2-style-pieces-PUB-06-rerun | cl-a v2 | 1/1 |
| cl-a-v2-style-in_words-PUB-10 | cl-a v2 | 1/1 |
| cl-ab-v2-style-asks_back-PUB-12 | cl-ab v2 | 1/1 |
| cl-ab-v2-style-corrects-PUB-13 | cl-ab v2 | 1/1 |
| cl-ab-v2-style-talkative-PUB-11 | cl-ab v2 | 1/1 |
| **varyasyon** | | **2/3** |
| **tarzlar** | | **5/6** |
| **toplam** | | **27/29** |

- `research/cloud-progress.md` içindeki "Toplam 29 koşu, 26 geçti" ifadesi **yanlış**; dosyalar 27/29 veriyor (`cloud-final-report.md` §5'in alt toplamları 20/20 + 2/3 + 5/6 de 27 eder).
- 27/29 bir pass^3 skoru değildir ve bütün public setin sonucu değildir: A'nın PUB-01/02/03/07/09'u bu adaylarla hiç koşulmadı; PUB-04/08 tek tekrar; tarzlar tek tekrar; varyasyon public vaka değildir.

## Kaynak → aday → koşu eşleşmesi
| aday | kaynak commit (builder ağacı) | workflow / agent | yayın sürümü | test=export hash | koşular |
|---|---|---|---|---|---|
| cl-a v2 | c8de7c9 (`c2d52b8c…`) | 0800b57a… / 91e04e98… | 2 | 233c8dfe1a7d9d91 | yukarıdaki cl-a satırları |
| cl-ab v2 | c8de7c9 | 06d2cae1… / f97de421… | 2 | 8abfb3c856c81f25 | yukarıdaki cl-ab satırları |

- 503d996 (kimlik istemi: parçaları birleştir, failed yalnız banka sonucuyla) **hiçbir ölçülmüş adayda yok**; canlı ölçülmedi. Bu çalışmada o istem değişikliği, karar yetkisini koda taşıyan 32bd888 ile yerini aldı (istem artık kimlik kararını modele bırakmıyor).
- Eski skorlar (n6, cl-a v2, cl-ab v2) bu çalışmanın yeni koduna atfedilmez. Yeni kodun canlı sonuçları yalnız yeni aday sürümüyle raporlanır (bkz. `research/yerel-olcum.md`).
