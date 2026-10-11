# Bulut devamı 3 — f075009'dan (11 Ekim 2026)

Eski adayların sonuçları (n6; cl-a v2 / cl-ab v2 27/29; loc-a v3 / loc-ab v2 10/10 tek koşu) buradaki yeni sürümlere
atfedilmez. Her canlı sonuç yalnız yanındaki aday sürümüne/hash'ine aittir.

## Başlangıç
- Dal `claude/lucid-fermat-vxp9u7`, HEAD = `f075009` = `origin/claude/lucid-fermat-vxp9u7`; çalışma ağacı temiz (korunacak yerel değişiklik yoktu). Aynı kapsayıcı: `out/brief-ab.md` (git-ignored) yerinde, Freya erişimi proxy ile çalışıyor.
- Simülasyon bütçesi: toplam 60, kullanılan 10 (bulut devamı 2, loc-a v3 / loc-ab v2) → kalan 50.

## 1. A15 karar kaydı
Brief A kural 15 (tam metin): "If the customer does not want to answer, explain once that the questions protect their
account. If they still decline, close as `not_verified` / `declined`. Asking what the call is about instead of answering
counts as declining. A second refusal or a second such question closes the call."

Okuma ve uygulama (builder/runtime/identity.py, ID_EVENT):
| niyet | olay | sayılır mı | dayanak |
|---|---|---|---|
| açıkça cevap vermeyi reddetme ("söylemeyeceğim", "cevap vermek istemiyorum") | `refuses` | evet | "does not want to answer", "a second refusal" |
| cevap yerine aramanın ne hakkında olduğunu sorma ("bu arama ne hakkında?", "neden arıyorsunuz?") | `asks_purpose` | evet | "Asking what the call is about instead of answering counts as declining" |
| kimlik sorusunun neden gerekli olduğunu sorma ("bunu neden istiyorsunuz?") | `asks_why` | hayır; koruma açıklamasıyla cevaplanır (çağrıda bir kez) | brief yalnız ret ve "arama ne hakkında" sorusunu sayar; açıklama metni "questions protect their account" bu soruyu cevaplar |
| birleşik: "Neden istiyorsunuz? Söylemeyeceğim." | `asks_why` + `refuses` | evet (ret kaçmaz) | açık ret içerir |
- Sayım kimlik aşaması boyunca sürer; ara cevaplar sayacı sıfırlamaz ("a second refusal or a second such question"). Mesaj başına en fazla bir ret sayılır.
- "Instead of answering" yeniden kontrol edildi: önceki kural "aynı mesajda herhangi bir cevap varsa sayma" idi. Daraltıldı: yalnız **sorulan soruya** verilen cevap (parça dahil) reddi geçersiz kılar; başka/önceden doğrulanmış soruya verilen cevap kılmaz.
- Açıklama çağrıda bir kez söylenir (ilk ret/soru ya da ilk "neden").

Örnek olay dizileri (tests/test_identity.py, iki motor kipinde):
| dizi | beklenen | test |
|---|---|---|
| asks_why | açıklama + soru; ret 0 | I12a |
| asks_why → cevap → asks_why | ret 0, açıklama tekrarlanmaz | I12b |
| (asks_why + refuses) → asks_purpose | ret 1, sonra 2 → `not_verified/declined`, banka çağrısı yok | I12c, I12d |
| asks_why → cevap → asks_purpose → cevap (kit asks_back) | hesaba ulaşır, ret 1 | I12e |
| cevap (doğrulandı) → [doğrulanmış alana cevap + refuses] | ret 1 (gizlenmez) | I12f |
| [refuses + sorulan soruya cevap] | ret 0, bir banka çağrısı | I12g |
| refuses → cevap → refuses | `declined`, açıklama tekrarlanmaz | I11h |
| asks_purpose → cevap → asks_purpose | `declined` | I11f |
Kural testi geçirmek için yumuşatılmadı: ara cevapla sıfırlama geri gelmedi; birleşik mesajdaki ret sayılıyor.
Modelde kalan kısım: müşterinin cümlesini bu olaylara ayırmak (dialogue model). Canlıda ölçülecek: PUB-01 `--style asks_back`, CD-2.

## 2. ISO tarih başarısızlığı
- Sınıf: **model ayrıştırma zayıflığı + kontrol aracının gerçek dışı girdisi**. Release practice kontrolü '1991-01-08' gönderdi; diyalog modeli bunu gün 19 / ay 91 / yıl '01-08' parçalarına böldü (chat 8669ea77…, loc-ab v2 build içi). Ajanın tarih parçalarını konuşmadan çıkarması modele bağlıdır; motor parçaları doğrular ve birleştirir.
- Temsilî kontrol: practice kontrolü cevapları kit personası gibi söyler (doğum tarihi kelimeyle). Ayrı regresyon olarak korunanlar:
  - yerel: I13a–e — modelin o gün gönderdiği olaylar birebir (ay 91 → banka çağrısı yok, hak tüketilmez, "okuyamadım" + soru; '04' yıl → yalnız yıl sorulur; 31 Şubat → çağrı yok; düzgün tarih → tek çağrı).
  - canlı: `eval/recheck_release.py --raw-answers` (ISO girdisiyle practice; sonucu aşağıda).
- Geçersiz/eksik parçalar yanlış banka çağrısına veya yanlış cevap hakkı tüketimine yol açmıyor (I13, I1–I2). Açıklama isteme: geçersiz tarihte "could not read" + soru; eksik parçada yalnız eksik parça sorulur.
- Modele bağlı kalan: konuşmadaki tarihi gün/ay/yıl parçalarına ayırmak; yalnız rakamlı tarihlerde (A11 gün-ay-yıl) modelin bölmesi yanlış olabilir. Motor yalnız imkânsız/eksik değeri yakalar; yanlış ama geçerli bir bölmeyi (ör. 6/6/1991) yakalayamaz — o durumda banka yanlış der ve bir hak gider.

## 3. Yeni aday sürümleri
(çalışıyor)

## 4. Ölçümler
(çalışıyor)
