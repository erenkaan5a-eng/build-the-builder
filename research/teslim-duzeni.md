# Teslim düzeni ve yerel projeye aktarma

Bu belge son organizatör talimatı yerine geçmez. Kit README'sinin söylediği: her final brief için builder bir kez,
elle adım olmadan çalıştırılır; teslim edilenler (1) `freya.export_workflow(...)` ile alınmış ajan dosyası, (2) builder
kodu, (3) o çalıştırmanın trace'i. Başka bir teslim kanalı (GitHub, form, e-posta) organizatör tarafından ayrıca
bildirilmedikçe varsayılmadı. Bu oturumda final teslim, main'e merge veya dışarıya mesaj YAPILMADI.

## Final brief başına beklenen dosyalar
| Dosya | Üreten | Not |
|---|---|---|
| `submission/hidden-N.workflow.json` | `build.py --out` (yalnız release checks PASSED ise) | puanlanan dosya; `candidates/<slot>/<time>/export.json` ile aynı |
| `traces/hidden-N.log` | `tee` | çalıştırmanın tam çıktısı |
| `traces/<slot>-<time>.log` | builder | model çağrıları, Freya nesneleri, testler, açıklar |
| `candidates/<slot>/<time>/{policy.raw.json, policy.json, workflow.json, support_boundary.json, export.json, manifest.json}` | builder | manifest: workflow/agent id, yayın sürümü, test edilen = export edilen hash, destek sınırı |
| builder kodu | git commit | aşağıdaki kaynak kimliği ile |

Giriş komutu (README_SUBMISSION.md):
```
python3 builder/build.py <brief> <tool_api> --out submission/hidden-N.workflow.json 2>&1 | tee traces/hidden-N.log
```
Bulut oturumunda anahtarlar proxy'deyse başına `FREYA_AUTH_VIA_PROXY=1` eklenir. `--practice` finalde KULLANILMAZ.

## Kaynak sürümü ↔ sonuç eşlemesi
Önceki `84894192a420329c` kimliği yeniden üretilemedi (yöntem belgelenmemiş). Bu oturumdan itibaren tekrar üretilebilir
kimlik: commit SHA + `git rev-parse <commit>:builder` (builder ağacının git hash'i).

| Kaynak | builder ağacı | Ne ölçüldü |
|---|---|---|
| a5de722 (yerel 11 Ekim düzeltmeleri, buluta gelen hâl) | a4c98a04ab393525 | yalnız yerel testler (bu oturumda yeniden koşuldu) |
| 59e0ba2 | fc7d2e3618ca86c4 | cl-a v1 / cl-ab v1 — platformda çöken motor; geçersiz (yalnız chat C2/C3 kanıtı) |
| c8de7c9 | c2d52b8ce679151c | **cl-a v2 / cl-ab v2 — ölçülen adaylar** (29 simüle koşu, cloud-progress.md) |
| 503d996 (güncel) | e426c5630ba6940b | c8de7c9 + kimlik istemi değişikliği; ÖLÇÜLMEDİ |

n6 canlı skorları (A 29/30, B 9/9) `1a5910570bcf9fe0` etiketli eski koda aittir; bu oturumun adaylarına taşınmaz.

## Bulut değişikliklerini yerel bilgisayara alma
Yerel kopya kendiliğinden güncellenmez. Windows'taki proje klasöründe (env.sh ve yerel `results/` korunur, git-ignored):
```
git fetch origin claude/lucid-fermat-vxp9u7
git status                      # yerelde commit'lenmemiş değişiklik varsa önce onları commit'le veya stash'le
git checkout claude/lucid-fermat-vxp9u7      # ya da kendi dalında: git merge origin/claude/lucid-fermat-vxp9u7
python3 tests/test_negotiation.py; python3 tests/test_negotiation_regress.py; python3 tests/test_date_tool.py; python3 tests/test_generator_structure.py; python3 tests/test_api_binding.py
```
- `.freya-agents.json` bulutta yeni slotlar (cl-a, cl-ab, …) aldı; yerelde de aynı dosya kullanılırsa bu slotlar aynı workflow'ları günceller. Yerelde farklı bir slot adı kullanmak eski adayları korur.
- `.personas.json` bulutta yeniden oluşturuldu ve git-ignored; yerel dosya etkilenmez.
- Bulutta üretilen ham simülasyon çıktıları `research/cloud-runs/` altında commit'lidir (yerel `results/` ignore edildiği için).
- Yerelde `FREYA_AUTH_VIA_PROXY` tanımlı değilse davranış eskisiyle aynıdır (env.sh'tan anahtar okunur).
