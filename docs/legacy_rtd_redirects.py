#!/usr/bin/env python3
"""Configure Read the Docs redirects for the legacy `minicpm-o` project.

Why this script exists
----------------------
The cookbook documentation moved from
    https://minicpm-o.readthedocs.io/
to
    https://opensqz.github.io/MiniCPM-V-CookBook/

This script installs a catch-all *page* redirect on the RTD project so that
every legacy URL — including deep links indexed by search engines — sends a
302 to the new home page. The new site does its own browser-language
detection (zh / en) on the first hop, so a single redirect is enough.

Usage
-----
    # 1. Generate a temporary RTD API token at:
    #    https://app.readthedocs.org/accounts/tokens/
    # 2. Run a dry-run to see what would change (no writes):
    export RTD_TOKEN=<paste your token here>
    python docs/legacy_rtd_redirects.py

    # 3. If the plan looks right, apply it:
    python docs/legacy_rtd_redirects.py --apply

    # 4. Verify the redirect is live:
    python docs/legacy_rtd_redirects.py --verify

    # 5. Revoke the token at the same page:
    #    https://app.readthedocs.org/accounts/tokens/

The script never reads or writes the token to disk; it only reads the
RTD_TOKEN environment variable. It is safe to commit and re-run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://app.readthedocs.org/api/v3"
NEW_SITE = "https://opensqz.github.io/MiniCPM-V-CookBook/"

# `minicpm-o`     — main English project
# `minicpm-o-cn`  — Simplified Chinese translation project (linked from the parent)
# Translation sub-projects in RTD usually inherit the parent's redirects, but
# we configure both to be safe; the script will skip a project if it 404s.
PROJECTS = ["minicpm-o", "minicpm-o-cn"]

# A single catch-all "page" redirect that matches every path on every version
# and language. RTD uses `*` as the wildcard (the older `$rest` placeholder
# was removed in 2024-ish) — the matched suffix is thrown away here because
# the new site does not share URL structure with the old.
REDIRECTS = [
    {
        "type":     "page",
        "from_url": "/*",
        "to_url":   NEW_SITE,
        "force":    True,
    },
]

# URLs to hit during --verify
VERIFY_PROBES = [
    "https://minicpm-o.readthedocs.io/en/latest/",
    "https://minicpm-o.readthedocs.io/zh_CN/latest/",
    "https://minicpm-o.readthedocs.io/en/latest/deployment/vllm.html",
]


# --------------------------------------------------------------------------
# RTD API helpers

def _request(method: str, path: str, token: str, body: dict | None = None) -> tuple[int, dict | str]:
    """Make a request to the RTD API. Returns (status, parsed_body)."""
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", f"Token {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, raw


def list_redirects(project: str, token: str):
    status, body = _request("GET", f"/projects/{project}/redirects/", token)
    if status == 404:
        return None  # project doesn't exist (or token can't see it)
    if status == 401 or status == 403:
        raise SystemExit(
            f"\n[auth] RTD rejected the token for `{project}` ({status}). "
            "Generate a fresh token at https://app.readthedocs.org/accounts/tokens/.\n"
        )
    if status != 200:
        raise SystemExit(f"\n[error] GET /projects/{project}/redirects/ → {status}: {body}\n")
    return body.get("results", [])


def create_redirect(project: str, token: str, redirect: dict) -> dict:
    status, body = _request("POST", f"/projects/{project}/redirects/", token, redirect)
    if status not in (200, 201):
        raise SystemExit(f"[error] POST /projects/{project}/redirects/ → {status}: {body}")
    return body


def delete_redirect(project: str, token: str, redirect_pk) -> None:
    status, body = _request("DELETE", f"/projects/{project}/redirects/{redirect_pk}/", token)
    if status not in (200, 204):
        raise SystemExit(f"[error] DELETE /projects/{project}/redirects/{redirect_pk}/ → {status}: {body}")


# --------------------------------------------------------------------------
# Verification

def verify(probes: list[str]) -> int:
    """Probe each URL (one hop, no auto-follow) and report whether it 3xx-redirects.

    We follow at most one hop manually if RTD does its own language-code
    normalisation first (e.g. /zh_CN/ → /zh-cn/). The probe is a GET with a
    real-looking User-Agent, because Read the Docs sits behind Cloudflare and
    rejects header-less HEAD requests with 403.
    """

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kw):
            return None

    opener = urllib.request.build_opener(NoRedirect())

    def one_hop(url: str) -> tuple[int, str]:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0 (cookbook-rtd-verifier)")
        try:
            with opener.open(req, timeout=15) as resp:
                return resp.status, resp.headers.get("Location", "") or ""
        except urllib.error.HTTPError as e:
            return e.code, (e.headers.get("Location", "") if e.headers else "")

    bad = 0
    for url in probes:
        # Walk up to two hops so RTD's internal /zh_CN → /zh-cn rewrite is
        # transparent.
        chain = [url]
        cur = url
        for _ in range(2):
            code, loc = one_hop(cur)
            if 300 <= code < 400 and loc and loc.startswith("https://minicpm-o.readthedocs.io"):
                cur = loc
                chain.append(loc)
                continue
            break

        ok = 300 <= code < 400 and loc.startswith(NEW_SITE)
        marker = "OK" if ok else "!!"
        print(f"  [{marker}]  {code}  {chain[0]}")
        for link in chain[1:]:
            print(f"          ↪ {link}")
        print(f"          → {loc or '(no Location header)'}")
        if not ok:
            bad += 1
    return bad


# --------------------------------------------------------------------------
# Main

def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--apply",  action="store_true", help="actually create redirects (default: dry-run)")
    p.add_argument("--verify", action="store_true", help="HEAD-check the legacy URLs and report status")
    args = p.parse_args()

    if args.verify:
        print("Verifying redirects on legacy URLs:\n")
        return 1 if verify(VERIFY_PROBES) else 0

    token = os.environ.get("RTD_TOKEN", "").strip()
    if not token:
        print(
            "ERROR: $RTD_TOKEN is not set.\n"
            "  1. Generate a token: https://app.readthedocs.org/accounts/tokens/\n"
            "  2. export RTD_TOKEN=<paste it here>\n"
            "  3. re-run this script\n",
            file=sys.stderr,
        )
        return 2

    print(f"Plan: redirect every legacy URL on each project below to {NEW_SITE}")
    for r in REDIRECTS:
        print(f"   {r['type']:6}  {r['from_url']:14}  →  {r['to_url']}")
    print()

    for project in PROJECTS:
        existing = list_redirects(project, token)
        if existing is None:
            print(f"[skip] project '{project}' not visible to this token (404).")
            continue

        print(f"--- {project} ---")
        if existing:
            print(f"  existing redirects ({len(existing)}):")
            for r in existing:
                print(f"    {r.get('type','?'):6}  {r.get('from_url',''):20}  →  {r.get('to_url','')}")
        else:
            print("  (no existing redirects)")

        for r in REDIRECTS:
            already_perfect = any(
                e.get("from_url") == r["from_url"]
                and e.get("type")     == r["type"]
                and (e.get("to_url") or "").rstrip("/") == r["to_url"].rstrip("/")
                for e in existing
            )
            stale = [
                e for e in existing
                if e.get("from_url") == r["from_url"]
                and e.get("type") == r["type"]
                and (e.get("to_url") or "").rstrip("/") != r["to_url"].rstrip("/")
            ]

            if already_perfect:
                print(f"  [skip] redirect already in place: {r['type']} {r['from_url']}")
                continue

            for s in stale:
                pk = s.get("pk") or s.get("id")
                msg = (
                    f"  [stale] same from_url with wrong to_url: {s.get('to_url')!r}"
                    f" (pk={pk})"
                )
                if not args.apply:
                    print(f"{msg}\n  [DRY-RUN] would delete it first")
                else:
                    delete_redirect(project, token, pk)
                    print(f"{msg}\n  [OK] deleted")

            if not args.apply:
                print(f"  [DRY-RUN] would create: {r['type']} {r['from_url']} → {r['to_url']}")
            else:
                create_redirect(project, token, r)
                print(f"  [OK] created: {r['type']} {r['from_url']} → {r['to_url']}")
        print()

    if not args.apply:
        print("Nothing was changed. Re-run with --apply to create the redirects.")
        print("Then run with --verify to confirm the live URLs return 3xx.")
    else:
        print("Done. Now run:    python docs/legacy_rtd_redirects.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
