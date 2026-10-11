"""tools/run_cases.py with the opt-in cloud proxy mode applied first (see tools/cloud_proxy.py). Same arguments.

    FREYA_AUTH_VIA_PROXY=1 python3 tools/run_cases_cloud.py <agent_id> --brief A --out research/cloud-runs/<name>.json
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cloud_proxy  # noqa: E402

print("cloud proxy mode:", cloud_proxy.apply(), flush=True)
import run_cases  # noqa: E402  (imports score.http after the patch)

if __name__ == "__main__":
    run_cases.main()
