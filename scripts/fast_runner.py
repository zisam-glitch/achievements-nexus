#!/usr/bin/env python3
"""
Fast Achievement Runner (API-Accelerated)
Utilizes GitHub REST API to create branches, commit co-authored files,
open PRs, merge, and delete branches in ~1.5s per iteration with rate-limit protection.
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
CO_AUTHOR_1 = "projectkaizen-hash <projectkaizen461@gmail.com>"
CO_AUTHOR_2 = "zisam shaikh <128255158+zisam-glitch@users.noreply.github.com>"

def get_token():
    env_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if env_token:
        return env_token.strip()
    return subprocess.check_output("gh auth token", shell=True).decode().strip()

TOKEN = get_token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "FastAchievementEngine/2.0"
}

def api_call(url, data=None, method="GET", max_retries=5):
    body = json.dumps(data).encode() if data is not None else None
    backoff = 2
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 204:
                    return None
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()
            if e.code in [403, 429]:
                print(f"[Rate Limit / Abuse Guard] Pausing for {backoff}s... ({err_msg[:80]})")
                time.sleep(backoff)
                backoff *= 2
            elif e.code in [409, 500, 502, 503, 504]:
                print(f"[HTTP {e.code}] Temporary failure, retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 1.5
            else:
                print(f"API Error [{e.code}]: {err_msg}")
                raise
        except Exception as ex:
            print(f"[Network Error] {ex}, retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= 1.5
    raise RuntimeError(f"Max retries exceeded for {url}")

def get_total_account_prs():
    try:
        res = subprocess.check_output("gh search prs --author zisam-glitch --merged --limit 1000 --json number", shell=True)
        prs = json.loads(res.decode())
        return len(prs)
    except Exception:
        return 0

def run_single_api_iteration(iteration_num):
    # 1. Get latest main SHA
    ref = api_call(f"{API_BASE}/git/ref/heads/main")
    main_sha = ref["object"]["sha"]
    
    # 2. Create branch
    branch = f"milestone/fast-{iteration_num}"
    api_call(f"{API_BASE}/git/refs", {"ref": f"refs/heads/{branch}", "sha": main_sha}, "POST")
    
    try:
        # 3. Get existing log file
        file_info = api_call(f"{API_BASE}/contents/nexus.log?ref={branch}")
        old_content = base64.b64decode(file_info["content"]).decode()
        file_sha = file_info["sha"]
        
        # 4. Append line & commit
        ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        new_line = f"[{ts}] Milestone Iteration #{iteration_num} verified (Fast API Engine).\n"
        new_content = base64.b64encode((old_content + new_line).encode()).decode()
        
        commit_msg = (
            f"feat(milestone): automated sync #{iteration_num}\n\n"
            f"Verified milestone event #{iteration_num}.\n\n"
            f"Co-authored-by: {CO_AUTHOR_1}\n"
            f"Co-authored-by: {CO_AUTHOR_2}"
        )
        
        api_call(f"{API_BASE}/contents/nexus.log", {
            "message": commit_msg,
            "content": new_content,
            "sha": file_sha,
            "branch": branch
        }, "PUT")
        
        # 5. Create PR
        pr = api_call(f"{API_BASE}/pulls", {
            "title": f"feat(milestone): iteration #{iteration_num}",
            "head": branch,
            "base": "main",
            "body": f"Automated milestone synchronization event #{iteration_num} with co-authored metadata."
        }, "POST")
        pr_num = pr["number"]
        
        # 6. Merge PR
        api_call(f"{API_BASE}/pulls/{pr_num}/merge", {"merge_method": "merge"}, "PUT")
        
        return pr_num
    finally:
        # 7. Clean up remote branch
        try:
            api_call(f"{API_BASE}/git/refs/heads/{branch}", method="DELETE")
        except Exception:
            pass

def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 130
    
    print("=" * 60)
    print(f" FAST ACHIEVEMENT ENGINE - PULL SHARK GOLD SPRINT")
    print(f" Target PRs: {target} | Starting from: {start}")
    print("=" * 60)
    
    t0 = time.time()
    for i in range(start, target + 1):
        i_t0 = time.time()
        pr_num = run_single_api_iteration(i)
        elapsed = time.time() - i_t0
        total_elapsed = time.time() - t0
        rate = (i - start + 1) / total_elapsed if total_elapsed > 0 else 0
        remaining_s = (target - i) / rate if rate > 0 else 0
        remaining_m = remaining_s / 60
        
        print(f"[{i}/{target}] Merged PR #{pr_num} in {elapsed:.2f}s | Speed: {rate*60:.1f} PR/min | ETA: {remaining_m:.1f}m")
        # 1.2s delay to respect secondary rate limits
        time.sleep(1.2)
        
    print(f"\nTarget {target} reached successfully in {(time.time()-t0)/60:.1f} minutes!")

if __name__ == "__main__":
    main()
