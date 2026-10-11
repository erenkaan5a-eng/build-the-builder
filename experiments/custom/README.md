# Kendi test vakalarımız (geliştirme + dondurulmuş son kontrol)

**Kit kısıtı (doğrulandı, 11 Ekim):** `tools/run_cases.py` bankada practice oturumunu yalnız `{"case": <id>}` ile açar
(`/v1/practice/sessions`); banka olguları (kimlik, ürünler, hatalar) sunucuda vaka kimliğine bağlıdır. `docs/api.md`
ve kitte özel fixture uç noktası yok. Bu yüzden:
- Canlı özel vakalar, **mevcut public practice müşterisinin kimliğini ve olgularını aynen kullanır**; yalnız konuşma
  senaryosu (`script`), yargıç kontrolleri (`checks`) ve buna göre beklenen ledger değişir. `custom_id` bizim etiketimiz;
  bankaya giden `id` her zaman bir PUB kimliğidir. Hayali CUSTOM-01 bankaya gönderilmez.
- Yeni olgular (başka kimlik, ürün, bakiye, hata deseni) yalnız yerel taklitle sınanır:
  `tests/test_identity.py` (banka taklidi `tests/identity_harness.py`), `tests/test_support.py`, `tests/test_negotiation*.py`.
- Simülasyonun persona metni `run_cases.py` içinde case alanlarından üretilir; `source_rules`, `expected_tools`,
  `forbidden`, `reps`, `custom_id` alanlarını kit kullanmaz, değerlendirmede biz okuruz (ledger `calls` + transcript).

**Ne zaman koşulur:** standart public kapısı (A: PUB-01..10 ×3, A+B: PUB-11..13 ×3) ve bilinen kritik regresyonlar
(PUB-06 pieces, PUB-03, PUB-12 pieces) aynı sabit aday çiftinde geçtikten sonra. Öncesinde yalnız yerel testler.

**Setler.** `cases-dev.json` (CD-*) geliştirme setidir: hata ayıklamada kullanılabilir, görüldükçe kod değişebilir.
`cases-frozen.json` (CF-*) dondurulmuş son kontroldür: bu dosya bu commit'ten sonra değiştirilmez; düzeltme gerekirse yeni
sürüm dosyası açılır ve eski sonuç silinmez. İkisi de bizim tasarladığımız ve gördüğümüz vakalardır; **hold-out değildir**.

**Beklenen değerlerin türetilmesi (çalışma zamanı kodundan bağımsız, brief'ten elle; now = Çar 14 Eki 2026):**
- Geç bant (8–45 gün) deadline: 7. iş günü = 15,16,19,20,21,22,**23 Eki**. Erken bant (1–7): 12. iş günü = 15,16,19,20,21,22,23,(26 tatil),27,28,29,30,**2 Kas**.
- Deneme 1 tarihi: bu haftanın son iş günü **Cum 16 Eki** (A30).
- CD-1 (PUB-06, 12 gün geç, floor 637.50): "too much" → floor deneme 1 tarihinde → 637.50 / 16 Eki (A26, A30).
- CD-2 (PUB-01): bugün tam tutar → 420 / 14 Eki (A28). "Why do you need that?" bir ret değildir; cevap gelir (A15 "still decline" yok).
- CD-3 (PUB-07, erken bant): rakamla "12, 5, 1975" → gün 12 ay 5 okunur (A11) → banka `day_month_swapped` (A13, yanlış sayılmaz) → "December" → 1975-12-05. "Week after next" → bir kez kesin gün (A21) → 26 Eki tatil → 27 Eki (A20), 27 Eki ≤ 2 Kas.
- CD-4 (PUB-05): 300 ∈ [260, 780] (A27), Cum 16 Eki ≤ 23 Eki (A19); A32 son cümlesi → kayıt.
- CD-5 (PUB-13): kart erken (2 Kas), kredi geç (23 Eki). Ortak 30 Eki → kart 30 Eki, kredi kendi deadline'ı 23 Eki (B6). Kısmi evet kayıt açmaz (B7). Kredi tutarı 300 = floor (A27 dahil) → yeniden geri okuma (A35), tarih korunur.
- CD-6 (PUB-12): kart yarın 15 Eki ≤ 23 Eki, tam 510; kredi itiraz → not `dispute` (A40, B8); araba ödendi → not `paid` (A39, B8); sonuç `promise` (B Closing).
- CD-7 (PUB-04, geç bant): Cmt 17 Eki iş günü değil → sonraki iş günü Pzt 19 Eki ≤ 23 Eki (A20).
- CF-1 (PUB-08): A43 cevabı, sonra A39 → `paid`.
- CF-2 (PUB-10): parçalı doğum tarihi; ilk create_promise hatası + bir tekrar (A37) → 365 / 16 Eki.
- CF-3 (PUB-11): telefon "22" + "88" → "2288"; üçü 16 Eki (B4, B7).
- CF-4 (PUB-09): kimlik sırasında insan isteği → bir kez yardım teklifi (A42), müşteri devam eder; sonra yeni taksit isteği → `restructuring` (A41).

**Tekrar sayısı:** bütçe (60 simüle koşu üst sınırı) nedeniyle önce 1 tekrar; pass^3 iddiası yalnız 3 tekrarla yapılır.
**Simülatör uyarısı:** persona beklenen bilgiyi hiç söylemediyse vaka ayrıca incelenir; ajan duyduğu bilgiyi kaybettiyse
simülatör suçlanmaz. Hatalı test düzeltmesi yeni test sürümüdür; eski başarısızlık silinmez.
