#!/usr/bin/env python3
"""Check a Facebook user access token for Page-posting capability.

Usage:
    python3 fb_token_check.py <USER_TOKEN>
    # or
    FB_TOKEN=<USER_TOKEN> python3 fb_token_check.py

Optional:
    --post                 Actually create a test post on every postable page
                           (then immediately deletes it). Off by default.
    --api-version v20.0    Graph API version (default: v20.0).
"""

import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request


def _ssl_context():
    """Build an SSL context using certifi's CA bundle if available; otherwise
    fall back to the system default. Some Linux distros ship a stale CA store
    that fails on Facebook's modern cert chain — certifi sidesteps that."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_SSL_CTX = _ssl_context()


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"

OK = f"{GREEN}✓{RESET}"
NO = f"{RED}✗{RESET}"
WARN = f"{YELLOW}!{RESET}"

REQUIRED_PERMS = {
    "pages_show_list": "list managed pages",
    "pages_read_engagement": "read posts/comments/reactions",
    "pages_manage_posts": "create/update/delete posts (REQUIRED to post)",
}
OPTIONAL_PERMS = {
    "pages_read_user_content": "read user-generated content on the page",
    "pages_manage_metadata": "webhook subscriptions & settings",
    "pages_manage_engagement": "moderate comments/reactions",
}


def graph_get(path, token, version, params=None):
    qs = {"access_token": token}
    if params:
        qs.update(params)
    url = f"https://graph.facebook.com/{version}/{path}?{urllib.parse.urlencode(qs)}"
    try:
        with urllib.request.urlopen(url, timeout=20, context=_SSL_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.request.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": {"message": str(e), "code": e.code}}
    except Exception as e:
        return {"error": {"message": str(e)}}


def graph_post(path, token, version, data):
    url = f"https://graph.facebook.com/{version}/{path}"
    body = urllib.parse.urlencode({**data, "access_token": token}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.request.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": {"message": str(e), "code": e.code}}


def graph_delete(path, token, version):
    url = f"https://graph.facebook.com/{version}/{path}?{urllib.parse.urlencode({'access_token': token})}"
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as r:
            return json.loads(r.read().decode())
    except urllib.request.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": {"message": str(e), "code": e.code}}


def section(title):
    print(f"\n{CYAN}── {title} {'─' * max(0, 60 - len(title))}{RESET}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("token", nargs="?", default=os.environ.get("FB_TOKEN"))
    p.add_argument("--post", action="store_true",
                   help="Create and delete a real test post on each postable page.")
    p.add_argument("--api-version", default="v20.0")
    args = p.parse_args()

    if not args.token:
        print(f"{NO} No token provided. Pass as arg or set FB_TOKEN env var.")
        sys.exit(2)

    token = args.token
    ver = args.api_version

    # 1. Identify the token holder
    section("1. Identify token holder")
    me = graph_get("me", token, ver, {"fields": "id,name"})
    if "error" in me:
        print(f"{NO} Token invalid: {me['error'].get('message')}")
        sys.exit(1)
    print(f"{OK} User: {me.get('name')} (id={me.get('id')})")

    # 2. Permissions
    section("2. Permissions granted")
    perms = graph_get("me/permissions", token, ver)
    if "error" in perms:
        print(f"{NO} Could not read permissions: {perms['error'].get('message')}")
        sys.exit(1)
    granted = {p["permission"] for p in perms.get("data", []) if p.get("status") == "granted"}
    declined = {p["permission"] for p in perms.get("data", []) if p.get("status") != "granted"}

    can_post = True
    for perm, why in REQUIRED_PERMS.items():
        if perm in granted:
            print(f"{OK} {perm:<28} {DIM}{why}{RESET}")
        else:
            print(f"{NO} {perm:<28} {DIM}{why}{RESET}")
            if perm == "pages_manage_posts":
                can_post = False

    for perm, why in OPTIONAL_PERMS.items():
        mark = OK if perm in granted else WARN
        print(f"{mark} {perm:<28} {DIM}{why}{RESET}")

    if declined - set(REQUIRED_PERMS) - set(OPTIONAL_PERMS):
        extras = declined - set(REQUIRED_PERMS) - set(OPTIONAL_PERMS)
        print(f"{DIM}Other declined: {', '.join(sorted(extras))}{RESET}")

    # 3. Pages this user manages
    section("3. Pages this user can act on")
    pages_resp = graph_get("me/accounts", token, ver,
                           {"fields": "id,name,access_token,tasks,category"})
    if "error" in pages_resp:
        print(f"{NO} Could not list pages: {pages_resp['error'].get('message')}")
        sys.exit(1)
    pages = pages_resp.get("data", [])
    if not pages:
        print(f"{NO} This user does not manage any Pages.")
        sys.exit(1)

    summaries = []
    for pg in pages:
        tasks = set(pg.get("tasks", []))
        can_create = "CREATE_CONTENT" in tasks
        mark = OK if can_create else NO
        print(f"{mark} {pg['name']} (id={pg['id']}, {pg.get('category', '?')})")
        print(f"   tasks: {', '.join(sorted(tasks)) or 'none'}")
        summaries.append({**pg, "can_create": can_create})

    # 4. Read + optional test write
    section("4. Read / write capability per page")
    overall_ok = False
    for pg in summaries:
        page_token = pg.get("access_token")
        if not page_token:
            print(f"{NO} {pg['name']}: no page token returned (insufficient perms)")
            continue

        # Read test
        recent = graph_get(f"{pg['id']}/posts", page_token, ver, {"limit": "1"})
        if "error" in recent:
            print(f"{NO} {pg['name']}: read failed — {recent['error'].get('message')}")
            read_ok = False
        else:
            read_ok = True
            count = len(recent.get("data", []))
            print(f"{OK} {pg['name']}: read OK ({count} recent post fetched)")

        # Write test (optional)
        if args.post and pg["can_create"] and can_post:
            test_msg = "[fb_token_check.py test — will self-delete in ~1s]"
            posted = graph_post(f"{pg['id']}/feed", page_token, ver, {"message": test_msg})
            if "error" in posted:
                print(f"{NO} {pg['name']}: write failed — {posted['error'].get('message')}")
            else:
                post_id = posted.get("id")
                print(f"{OK} {pg['name']}: write OK (posted {post_id})")
                deleted = graph_delete(post_id, page_token, ver)
                if deleted.get("success") or deleted.get("data", {}).get("success"):
                    print(f"   {DIM}(test post deleted){RESET}")
                else:
                    print(f"   {YELLOW}WARNING: could not auto-delete test post {post_id}{RESET}")
                overall_ok = True
        elif pg["can_create"] and can_post:
            overall_ok = True

    # 5. Verdict
    section("Verdict")
    if overall_ok:
        print(f"{GREEN}✓ This token CAN post to at least one Page.{RESET}")
        if not args.post:
            print(f"{DIM}Re-run with --post to verify with a live test post.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}✗ This token cannot post to any Page.{RESET}")
        if not can_post:
            print("  Missing 'pages_manage_posts' permission — re-auth with that scope.")
        else:
            print("  No page has CREATE_CONTENT task assigned to this user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
