#!/usr/bin/env python3
"""
Internship watcher.

Checks a list of companies for job postings containing "intern", compares
against the last-known state (stored in state.json, committed back to the
repo by the GitHub Action), and sends a push notification via ntfy.sh for
anything new.

Two company types are handled properly via their public JSON APIs:
  - greenhouse       (Razorpay and many others use this ATS)
  - smartrecruiters   (Zomato uses this ATS)

Everything else falls back to "html_keyword": it fetches the page, pulls out
lines containing "intern" (case-insensitive), and diffs that against last
time. This fallback is best-effort — if a career page is a JS-rendered SPA
with no server-side content (some are), it may not see anything. Treat those
entries as a nice-to-have, not a guarantee.
"""

import json
import hashlib
import os
import re
import sys
import urllib.request

STATE_FILE = "state.json"
COMPANIES_FILE = "companies.json"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")  # set as a GitHub Actions secret

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; internship-watcher/1.0)"
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def notify(title, message):
    if not NTFY_TOPIC:
        print(f"[no NTFY_TOPIC set] Would notify: {title} - {message}")
        return
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    req = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        headers={**HEADERS, "Title": title, "Priority": "high", "Tags": "briefcase"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Notify failed: {e}")


def check_greenhouse(company):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company['board_token']}/jobs?content=true"
    data = json.loads(fetch(url))
    jobs = data.get("jobs", [])
    results = {}
    for j in jobs:
        title = j.get("title", "")
        if "intern" in title.lower():
            job_id = str(j.get("id"))
            results[job_id] = {
                "title": title,
                "url": j.get("absolute_url", ""),
            }
    return results


def check_smartrecruiters(company):
    url = f"https://api.smartrecruiters.com/v1/companies/{company['company_id']}/postings"
    data = json.loads(fetch(url))
    postings = data.get("content", [])
    results = {}
    for p in postings:
        title = p.get("name", "")
        if "intern" in title.lower():
            job_id = str(p.get("id"))
            results[job_id] = {
                "title": title,
                "url": f"https://jobs.smartrecruiters.com/{company['company_id']}/{p.get('id')}",
            }
    return results


def check_html_keyword(company):
    html = fetch(company["url"])
    text = re.sub("<[^>]+>", " ", html)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    intern_lines = [l for l in lines if "intern" in l.lower()]
    # Fingerprint the whole intern-related content as a single "job" entry
    # since generic HTML doesn't give us stable per-posting IDs.
    blob = "\n".join(intern_lines)
    if not blob:
        return {}
    fingerprint = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
    return {
        fingerprint: {
            "title": f"Internship-related content changed on {company['name']} careers page",
            "url": company["url"],
            "snippet": blob[:500],
        }
    }


CHECKERS = {
    "greenhouse": check_greenhouse,
    "smartrecruiters": check_smartrecruiters,
    "html_keyword": check_html_keyword,
}


def main():
    with open(COMPANIES_FILE) as f:
        companies = json.load(f)

    state = load_state()
    new_state = {}
    any_new = False

    for company in companies:
        name = company["name"]
        checker = CHECKERS.get(company["type"])
        if not checker:
            print(f"Skipping {name}: unknown type {company['type']}")
            continue

        try:
            current = checker(company)
        except Exception as e:
            print(f"Error checking {name}: {e}")
            # Keep old state for this company so a transient failure
            # doesn't wipe out what we knew and cause false "new" alerts.
            new_state[name] = state.get(name, {})
            continue

        previous = state.get(name, {})
        new_ids = set(current) - set(previous)

        for job_id in new_ids:
            job = current[job_id]
            any_new = True
            print(f"NEW: {name} - {job['title']}")
            notify(
                title=f"New internship: {name}",
                message=f"{job['title']}\n{job.get('url', '')}",
            )

        new_state[name] = current

    save_state(new_state)

    if not any_new:
        print("No new internship postings found.")


if __name__ == "__main__":
    sys.exit(main())
