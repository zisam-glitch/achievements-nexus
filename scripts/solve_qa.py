#!/usr/bin/env python3
"""
Galaxy Brain Solver & Submitter
Inspects discussion threads and allows posting verified answers via GraphQL mutation.
"""

import subprocess
import json
import sys
import os

GET_DISCUSSION_QUERY = """
query($owner: String!, $repo: String!, $num: Int!) {
  repository(owner: $owner, name: $repo) {
    discussion(number: $num) {
      id
      title
      url
      body
      category {
        name
        isAnswerable
      }
      comments(first: 5) {
        nodes {
          author {
            login
          }
          body
        }
      }
    }
  }
}
"""

POST_COMMENT_MUTATION = """
mutation($discussionId: ID!, $body: String!) {
  addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
    comment {
      id
      url
    }
  }
}
"""

def parse_discussion_url(url):
    # Format: https://github.com/orgs/<owner>/discussions/<num> or https://github.com/<owner>/<repo>/discussions/<num>
    parts = url.strip().rstrip("/").split("/")
    num = int(parts[-1])
    if "orgs" in parts:
        owner = parts[parts.index("orgs") + 1]
        repo = owner # For org-level discussions, repo is often the org or default discussion repo
        # Alternatively query via gh
    else:
        owner = parts[-4]
        repo = parts[-3]
    return owner, repo, num

def get_discussion_by_id(discussion_id):
    query = """
    query($id: ID!) {
      node(id: $id) {
        ... on Discussion {
          id
          title
          url
          body
          category {
            name
            isAnswerable
          }
        }
      }
    }
    """
    cmd = ["gh", "api", "graphql", "-f", f"id={discussion_id}", "-f", f"query={query}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return json.loads(res.stdout).get("data", {}).get("node")
    return None

def post_answer(discussion_id, answer_body):
    cmd = [
        "gh", "api", "graphql",
        "-f", f"discussionId={discussion_id}",
        "-f", f"body={answer_body}",
        "-f", f"query={POST_COMMENT_MUTATION}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        data = json.loads(res.stdout)
        comment = data.get("data", {}).get("addDiscussionComment", {}).get("comment")
        return comment
    else:
        print("Error posting comment:", res.stderr)
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/solve_qa.py scan")
        print("  python3 scripts/solve_qa.py post <discussion_node_id> <answer_file_or_text>")
        return
        
    cmd = sys.argv[1]
    if cmd == "scan":
        os.system(f"python3 {os.path.dirname(__file__)}/find_qa.py")
    elif cmd == "post":
        if len(sys.argv) < 4:
            print("Error: specify discussion_node_id and answer text/file.")
            return
        disc_id = sys.argv[2]
        ans = sys.argv[3]
        if os.path.exists(ans):
            with open(ans, "r") as f:
                ans = f.read()
        comment = post_answer(disc_id, ans)
        if comment:
            print(f"Successfully posted answer! URL: {comment.get('url')}")
            print("Once the author or maintainer marks this as accepted, Galaxy Brain will unlock!")

if __name__ == "__main__":
    main()
