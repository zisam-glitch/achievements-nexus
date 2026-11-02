#!/usr/bin/env python3
"""
Galaxy Brain Q&A Finder
Scans top open-source repositories with GitHub Discussions enabled for open,
unanswered questions in the Q&A category.
"""

import subprocess
import json
import sys

TARGET_REPOS = [
    "honojs/hono",
    "vercel/next.js",
    "vitejs/vite",
    "fastify/fastify",
    "trpc/trpc",
    "biomejs/biome",
    "tailwindlabs/tailwindcss",
    "shadcn-ui/ui",
]

GRAPHQL_QUERY = """
query($queryStr: String!) {
  search(query: $queryStr, type: DISCUSSION, first: 5) {
    discussionCount
    nodes {
      ... on Discussion {
        title
        url
        createdAt
        category {
          name
        }
        answer {
          id
        }
        comments {
          totalCount
        }
      }
    }
  }
}
"""

def scan_repo(repo):
    query_str = f"repo:{repo} is:open category:Q&A"
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
        # Filter for discussions without an accepted answer
        unanswered = [n for n in nodes if n.get("answer") is None]
        return unanswered
    except Exception:
        return []

def main():
    print("=" * 60)
    print("  GALAXY BRAIN Q&A DISCOVERY SCANNER")
    print("=" * 60)
    
    found_any = False
    for repo in TARGET_REPOS:
        print(f"\n[Scanning] {repo} ...")
        unanswered = scan_repo(repo)
        if not unanswered:
            print("  No recent open Q&A candidates.")
            continue
            
        found_any = True
        for item in unanswered:
            comments = item.get("comments", {}).get("totalCount", 0)
            print(f"  * {item.get('title')}")
            print(f"    Comments: {comments} | URL: {item.get('url')}")
            
    print("\n" + "=" * 60)
    print("Scan complete. Post answers in these threads to unlock Galaxy Brain!")
    print("=" * 60)

if __name__ == "__main__":
    main()
