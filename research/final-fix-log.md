# Final sonrası builder düzeltme kaydı (20.00 İstanbul sonrası)

Her builder düzeltmesi için bir satır. Bu kayıt yasak bir değişikliği izinli hâle getirmez: finalden öğrenilen kural,
değer, isim veya alan adı reusable builder koduna, prompt'una, skill'ine ya da talimat dosyalarına elle eklenmez.

| zaman | commit | genel hata (belirti + hangi koşu/trace) | neden finale özel değil | doğrulayan test |
|---|---|---|---|---|
| 2026-10-11 20:17 İst. | (bu commit) | Builder'ın SDK model çağrıları ayrı tam oturum kaydı bırakmıyordu: Claude Code içinden başlatılan alt süreç `CLAUDE_CODE_SESSION_ID`'yi devralıp kaydını çağıran geliştirme oturumunun JSONL'ine yazıyordu (prova koşusu 16:06'da ayrı JSONL yok; Haiku denemesinde session_id = geliştirme oturumu). Teslim, coding-agent koşusunun tam oturum günlüğünü istiyor. Düzeltme: her SDK çağrısına yeni session id + SDK `session_store` yansıtması → `traces/<koşu>.sessions/<id>.jsonl` (istem, model yanıtı, araç çağrıları/sonuçları, alt ajanlar), gizli değer maskeleme, trace'te dosya/girdi sayısı/sha256 | Banka kuralı, değer, isim veya alan adı içermez; her koşu ve her belge için aynı kayıt altyapısı; final paketinden hiçbir bilgi kullanılmadı | `traces/selftest-session-20261011-171641.*`: koşu oturumu ayrı dosyada (20 girdi, istem ve yanıt var), işaret dizgesi geliştirme oturumunda 0 kez, sahte gizli değer 3 kez maskelendi / 0 açık; tüm testler 0 hata |
