#!/usr/bin/env python3
"""
Pair Extraordinaire Gold Runner (x4 Target)
Automates creation and merging of PRs where projectkaizen-hash is commit author
and zisam-glitch is co-author to reach the 48-PR threshold for Gold tier.
"""

import urllib.request
import urllib.error
import json
import subprocess
import base64
import time
import sys
import os

REPO = "zisam-glitch/achievements-nexus"
API_BASE = f"https://api.github.com/repos/{REPO}"

CO_AUTHOR_LINE_1 = "Co-authored-by: zisam shaikh <zisamshaikh7@gmail.com>"
CO_AUTHOR_LINE_2 = "Co-authored-by: zisam shaikh <128255158+zisam-glitch@users.noreply.github.com>"

def get_token():
    env_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if env_token:
        return env_token.strip()
    return subprocess.check_output("gh auth token", shell=True).decode().strip()

TOKEN = get_token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "PairExtraordinaireGoldEngine/1.0"
}

def api_call(url, data=None, method="GET", max_retries=5):
    body = json.dumps(data).encode() if data is not None else None
    backoff = 2
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 204:
                    return None
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()
            if e.code in [403, 429]:
                print(f"[Rate Guard] Pausing {backoff}s...", flush=True)
                time.sleep(backoff)
                backoff *= 2
            elif e.code in [405, 409, 500, 502, 503, 504]:
                print(f"[HTTP {e.code}] Sync lag, retrying in {backoff}s...", flush=True)
                time.sleep(backoff)
                backoff *= 1.5
            else:
                print(f"API Error [{e.code}]: {err_msg}", flush=True)
                raise
        except Exception as ex:
            print(f"[Network] {ex}, retrying in {backoff}s...", flush=True)
            time.sleep(backoff)
            backoff *= 1.5
    raise RuntimeError(f"Max retries exceeded for {url}")

def run_pair_iteration(iteration_num, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        branch = f"pair/gold-{iteration_num}-{attempt}"
        try:
            # 1. Get main ref
            ref = api_call(f"{API_BASE}/git/ref/heads/main")
            main_sha = ref["object"]["sha"]

            # 2. Create branch
            api_call(f"{API_BASE}/git/refs", {"ref": f"refs/heads/{branch}", "sha": main_sha}, "POST")

            # 3. Get existing nexus.log
            file_info = api_call(f"{API_BASE}/contents/nexus.log?ref={branch}")
            old_content = base64.b64decode(file_info["content"]).decode()
            file_sha = file_info["sha"]

            # 4. Commit with projectkaizen author & zisam co-author
            ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            new_line = f"[{ts}] Pair Extraordinaire Gold Milestone #{iteration_num}.\n"
            new_content = base64.b64encode((old_content + new_line).encode()).decode()

            commit_msg = (
                f"feat(pair): collaboration sync #{iteration_num}\n\n"
                f"Pair milestone sync #{iteration_num}.\n\n"
                f"{CO_AUTHOR_LINE_1}\n"
                f"{CO_AUTHOR_LINE_2}"
            )

            api_call(f"{API_BASE}/contents/nexus.log", {
                "message": commit_msg,
                "content": new_content,
                "sha": file_sha,
                "branch": branch,
                "author": {
                    "name": "projectkaizen-hash",
                    "email": "projectkaizen461@gmail.com"
                },
                "committer": {
                    "name": "projectkaizen-hash",
                    "email": "projectkaizen461@gmail.com"
                }
            }, "PUT")

            # 5. Open PR
            pr = api_call(f"{API_BASE}/pulls", {
                "title": f"feat(pair): collaboration milestone #{iteration_num}",
                "head": branch,
                "base": "main",
                "body": f"Automated co-authorship sprint #{iteration_num} targeting Pair Extraordinaire Gold (x4)."
            }, "POST")
            pr_num = pr["number"]

            # Wait 1.5s for mergeability check
            time.sleep(1.5)

            # 6. Merge PR
            api_call(f"{API_BASE}/pulls/{pr_num}/merge", {"merge_method": "merge"}, "PUT")

            return pr_num
        except Exception as e:
            print(f"[Iteration #{iteration_num} Attempt {attempt} Failed]: {e}", flush=True)
            try:
                api_call(f"{API_BASE}/git/refs/heads/{branch}", method="DELETE")
            except Exception:
                pass
            if attempt < max_attempts:
                time.sleep(3.0)
            else:
                raise

def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    print("=" * 60, flush=True)
    print(f" PAIR EXTRAORDINAIRE GOLD SPRINT (x4 TARGET: 48 PRs)", flush=True)
    print(f" Target: {target} | Starting from: {start}", flush=True)
    print("=" * 60, flush=True)

    t0 = time.time()
    for i in range(start, target + 1):
        i_t0 = time.time()
        try:
            pr_num = run_pair_iteration(i)
            elapsed = time.time() - i_t0
            total_elapsed = time.time() - t0
            rate = (i - start + 1) / total_elapsed if total_elapsed > 0 else 0
            rem_m = ((target - i) / rate) / 60 if rate > 0 else 0

            print(f"[{i}/{target}] Merged Pair PR #{pr_num} in {elapsed:.2f}s | Speed: {rate*60:.1f} PR/min | ETA: {rem_m:.1f}m", flush=True)
            time.sleep(2.0)
        except Exception as e:
            print(f"Skipping failed iteration #{i}: {e}", flush=True)
            time.sleep(4.0)

    print(f"\nPair Extraordinaire Gold sprint completed in {(time.time()-t0)/60:.1f} minutes!", flush=True)

if __name__ == "__main__":
    main()
