#!/usr/bin/env python3
"""
Achievements Nexus - Automated Milestone Engine
Automates pull request creation and merging with co-author trailers
to unlock Pair Extraordinaire (all tiers up to Gold) and Pull Shark (up to Gold).
"""

import subprocess
import time
import sys
import os

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_DIR)

REPO = "zisam-glitch/achievements-nexus"
CO_AUTHOR_1 = "projectkaizen-hash <projectkaizen461@gmail.com>"
CO_AUTHOR_2 = "zisam shaikh <128255158+zisam-glitch@users.noreply.github.com>"

def run(cmd, check=True):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"Error executing: {cmd}")
        print(f"STDERR: {res.stderr.strip()}")
        raise RuntimeError(res.stderr)
    return res

def get_current_pr_count():
    res = run(f"gh pr list --repo {REPO} --state all --limit 1000 --json number", check=False)
    if res.returncode == 0:
        import json
        try:
            prs = json.loads(res.stdout)
            return len(prs)
        except Exception:
            return 0
    return 0

def run_single_iteration(iteration_num):
    branch = f"milestone/step-{iteration_num}"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    
    # 1. Checkout new branch
    run(f"git checkout -b {branch}")
    
    # 2. Update log
    log_file = "nexus.log"
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] Milestone Iteration #{iteration_num} verified.\n")
    
    # 3. Commit with co-authors
    commit_msg = (
        f"feat(milestone): automated sync #{iteration_num}\n\n"
        f"Verified milestone event #{iteration_num}.\n\n"
        f"Co-authored-by: {CO_AUTHOR_1}\n"
        f"Co-authored-by: {CO_AUTHOR_2}\n"
    )
    
    run(f"git add {log_file}")
    
    # Write commit msg to temp file to preserve formatting
    with open(".commit_msg.tmp", "w") as f:
        f.write(commit_msg)
    run("git commit -F .commit_msg.tmp")
    if os.path.exists(".commit_msg.tmp"):
        os.remove(".commit_msg.tmp")
        
    # 4. Push branch
    run(f"git push origin {branch}")
    
    # 5. Create PR via gh
    pr_title = f"feat(milestone): iteration #{iteration_num}"
    pr_body = f"Milestone progress sync #{iteration_num} with verified co-authorship metadata."
    create_res = run(f"gh pr create --repo {REPO} --title \"{pr_title}\" --body \"{pr_body}\" --base main --head {branch}")
    pr_url = create_res.stdout.strip()
    
    # 6. Merge PR
    run(f"gh pr merge \"{pr_url}\" --repo {REPO} --merge --delete-branch")
    
    # 7. Switch back to main and pull
    run("git checkout main")
    run("git pull origin main")
    
    print(f"[{iteration_num}] Merged PR successfully: {pr_url}")

def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    print(f"Starting Achievement Automation Engine...")
    print(f"Target PRs in this batch: {target}")
    
    for i in range(start, target + 1):
        try:
            run_single_iteration(i)
            # Brief pause to stay gentle on rate limits
            time.sleep(1)
        except Exception as e:
            print(f"Failed at iteration {i}: {e}")
            run("git checkout main", check=False)
            time.sleep(5)
            
    print(f"\nBatch completed up to iteration {target}!")

if __name__ == "__main__":
    main()
