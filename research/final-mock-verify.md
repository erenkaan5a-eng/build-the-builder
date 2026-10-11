# Final mock: deployed URL verification

- URL: https://bank-mock-final.erenkaan5a.workers.dev (deployed by the user from Windows with scripts/deploy_mock.sh; mock code = commit 836d120, unchanged since)
- First verify, right after the deploy (21:42 İstanbul): 577 of 627 checks got Cloudflare "Error 1042: No Workers script was found" (new workers.dev subdomain not yet propagated; 50 checks already reached the Worker and matched). Record: traces/mock-deploy-20261011-184222.{log,json} on the user's machine, verify=FAIL.
- Re-run of the verification only, a few minutes later (user's output, 21:45 İstanbul):
  `verify https://bank-mock-final.erenkaan5a.workers.dev: 617 stored answers + 8 not-found/invalid + health + unknown path; 0 mismatch(es); 16 s`
- This cloud session cannot reach *.workers.dev (proxy 403), so the verification evidence is the user's run; the phone agent reaches the mock from the Freya platform.
