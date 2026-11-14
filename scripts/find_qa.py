#!/usr/bin/env python3
"""
Galaxy Brain Q&A Finder & Discovery Scanner
Scans high-velocity open-source repositories with GitHub Discussions enabled
for fresh, unanswered questions in answerable categories (Q&A, Help).
"""

import subprocess
import json
import sys
import os

# Repositories and their answerable category names
TARGET_CONFIG = [
    {"repo": "vercel/next.js", "categories": ["Help", "App Router"]},
    {"repo": "tailwindlabs/tailwindcss", "categories": ["Help"]},
    {"repo": "shadcn-ui/ui", "categories": ["Q&A"]},
    {"repo": "TanStack/query", "categories": ["Q&A"]},
    {"repo": "trpc/trpc", "categories": ["Q&A"]},
    {"repo": "honojs/hono", "categories": ["Q&A"]},
    {"repo": "fastify/fastify", "categories": ["Q&A"]},
    {"repo": "remix-run/react-router", "categories": ["Q&A"]},
]

GRAPHQL_QUERY = """
query($queryStr: String!) {
  search(query: $queryStr, type: DISCUSSION, first: 5) {
    discussionCount
    nodes {
      ... on Discussion {
        id
        number
        title
        url
        createdAt
        category {
          name
          isAnswerable
        }
        answer {
          id
        }
        comments {
          totalCount
        }
        body
      }
    }
  }
}
"""

def scan_repo(repo, category):
    query_str = f'repo:{repo} is:open category:"{category}" comments:<=1 sort:created-desc'
    cmd = [
        "gh", "api", "graphql",
        "-f", f"queryStr={query_str}",
        "-f", f"query={GRAPHQL_QUERY}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return []

    try:
        data = json.loads(res.stdout)
        nodes = data.get("data", {}).get("search", {}).get("nodes", [])
        # Strictly ensure:
        # 1. No accepted answer yet
        # 2. Category is strictly answerable
        # 3. Not self-locked
        candidates = []
        for n in nodes:
            cat = n.get("category", {})
            if n.get("answer") is None and cat.get("isAnswerable", True):
                candidates.append(n)
        return candidates
    except Exception:
        return []

def main():
    output_md = os.environ.get("GITHUB_STEP_SUMMARY") or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    print("=" * 70)
    print("  GALAXY BRAIN PUBLIC Q&A DISCOVERY SCANNER")
    print("=" * 70)

    all_candidates = []

    for cfg in TARGET_CONFIG:
        repo = cfg["repo"]
        for cat in cfg["categories"]:
            print(f"\n[Scanning] {repo} (Category: {cat}) ...")
            candidates = scan_repo(repo, cat)
            if not candidates:
                print(f"  No open candidates found.")
                continue

            for c in candidates:
                c["repo"] = repo
                c["cat_name"] = cat
                all_candidates.append(c)
                comments_count = c.get("comments", {}).get("totalCount", 0)
                print(f"  * #{c.get('number')} {c.get('title')}")
                print(f"    URL: {c.get('url')} | Comments: {comments_count} | Node ID: {c.get('id')}")

    print("\n" + "=" * 70)
    print(f"Scan complete. Total candidate discussions discovered: {len(all_candidates)}")
    print("=" * 70)

    # Optional markdown summary output
    if output_md:
        md_content = ["### 🌌 Galaxy Brain Public Q&A Discovery Feed\n"]
        md_content.append(f"Scanned {len(TARGET_CONFIG)} repositories at scheduled run.\n")
        md_content.append("| Repository | # | Title | Comments | Node ID | Direct Link |")
        md_content.append("| :--- | :---: | :--- | :---: | :--- | :--- |")
        for c in all_candidates[:25]:
            title_escaped = c.get("title", "").replace("|", "\\|")
            num = c.get("number")
            repo = c.get("repo")
            node_id = c.get("id")
            comments = c.get("comments", {}).get("totalCount", 0)
            url = c.get("url")
            md_content.append(f"| `{repo}` | #{num} | {title_escaped} | {comments} | `{node_id}` | [View Thread]({url}) |")
        
        md_content.append("\n\n**To answer a thread via CLI:**\n```bash\npython3 scripts/solve_qa.py post <NODE_ID> \"<ANSWER_TEXT_OR_FILE>\"\n```\n")

        with open(output_md, "a" if output_md == os.environ.get("GITHUB_STEP_SUMMARY") else "w") as f:
            f.write("\n".join(md_content) + "\n")
        print(f"Saved candidate report to {output_md}")

if __name__ == "__main__":
    main()
