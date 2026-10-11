# Freya platformu 504 olayı — 11 Ekim 2026 (yerel oturum)

Sınıf: **şüpheli platform hatası** (sonuç değil, gözlem). Ham kayıtlar: `results/loc-a-build1*.log`, `results/platform-probe-1011.log`, `traces/loc-a-*.log`.

| saat (+03) | istek | sonuç |
|---|---|---|
| 13:46:21 | build 1 başlar; Opus çıkarımı 81 s, policy doğrulaması temiz | — |
| 13:47:46 | dry-run `POST /api/v2/workflow` | 60 s sonra 504 → yayın yok |
| 13:50:11 | 1b: `create_workflow` (loc-a, 23150a3a…) | ~2 s'de başarılı |
| 13:50:1x | 1b: `PUT` geçti, ardından `GET /workspaces` | 504 |
| 13:51:21 | sağlık `GET /workspaces` | ok |
| 13:51:39–14:04:44 | 1c: dry-run 504, 504, ok; `GET/PUT /workflow/23150a3a…` 504 ×4 (30/90/180 s beklemeli) | yayın yok |
| 14:06:40, 14:12:40 | sağlık | 504, 504 |
| 14:17:41 | sağlık | ok |
| 14:17:49–14:26:52 | 1d: dry-run ok; `PUT` 504 ×4 | yayın yok |
| 14:28 | eski `cl-a` workflow'u (0800b57a…) için `GET` ve yeni için `GET` | ikisi de 60 s / 504 |
| 14:33:24 | sağlık | ok |
| 14:33:35 | 1e: dry-run ok, `PUT` ~2 s'de geçti, ardından `GET /workspaces` | 504 → süreç durduruldu |
| 14:56:51 | sağlık (son isteğimizden 22 dk sonra) | 504 |
| 15:03:03 | sağlık | **503: "API key validation is temporarily unavailable. Retry shortly."** |

**Hipotezler:** 15:03'teki 503 mesajı platformun anahtar doğrulama servisinin geçici olarak çalışmadığını söylüyor; bu, 1. hipotezi (genel platform kesintisi) güçlendiriyor. 2. hipotez dışlanmadı ama artık zayıf.
1. Genel platform yükü/kesintisi: eski, ölçülmüş `cl-a` workflow'unun okunması da 504 verdi; kesinti ilk dry-run'da (hiçbir yazma yapılmadan önce) başladı; bulut oturumunda da (01:49–01:53 UTC) eski workflow'larla 502/503 görülmüştü; bugün final brief'lerinin yayın günü (yoğun kullanım beklenir).
2. Bizim yeni (180–215 KB, 33 düğüm) workflow'umuzun kaydı sonrası sunucu tarafında uzun süren bir iş: her `PUT` sonrasında platform 10–15 dk yanıtsız kaldı. Kanıt korelasyon düzeyinde; karşılaştırmalı deney paylaşılan platformu yeniden kilitleyebileceği için yapılmadı.

**Alınan önlemler:** dry-run ve mevcut slot güncellemesi için bütçe içi sınırlı 5xx tekrarı (yeni slot oluşturma tekrarlanmaz); 504 sürerken yayın denemesi durduruldu; sağlık kontrolü 5–20 dk aralıklı tek istekle; simülasyon başlatılmadı. Bu süre Claude/Freya kullanımında ek maliyet üretmedi (yalnız 1 Opus çıkarım çağrısı, build 1).
