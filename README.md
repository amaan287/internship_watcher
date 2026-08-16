# Internship Watcher

Checks Razorpay, Zomato, Zerodha, Swiggy, Zepto, Flipkart, Blinkit, Groww,
PhonePe, Unacademy, and Cars24 for new internship postings on a schedule, and
pushes a phone notification the moment one appears. Runs entirely on GitHub's
free infrastructure — nothing needs to stay running on your own machine.

## How it works

- **Razorpay, Zomato, Groww, PhonePe, Unacademy, and Cars24** are checked via
  their real job-board APIs (Greenhouse and SmartRecruiters respectively) —
  this is reliable, exact, and won't miss anything.
- **Zerodha, Swiggy, Zepto, Flipkart, Blinkit** don't expose a public jobs
  API, so the script falls back to fetching their careers page and looking
  for lines containing "intern". This is best-effort: if a page is a
  JavaScript-rendered single-page app with no content in the raw HTML, the
  script won't see anything on it. Treat these five as "might catch it,"
  not "guaranteed."

Every run is compared against `state.json` (committed back into the repo by
the workflow itself), so you only get notified about genuinely *new*
postings — not the same list every 30 minutes.

## Setup (10 minutes)

1. **Create a new GitHub repo** and push these files to it
   (`companies.json`, `monitor.py`, `README.md`, and the
   `.github/workflows/check-internships.yml` file).

2. **Get a notification channel.** The easiest free option is
   [ntfy.sh](https://ntfy.sh) — no account needed:
   - On your phone, install the ntfy app (Android/iOS) or just open
     `https://ntfy.sh/<pick-a-random-topic-name>` in a browser.
   - Pick a topic name that's hard to guess (e.g. `amaan-intern-alerts-x7f2`)
     since anyone who knows the topic name can see your notifications —
     it's not authenticated.
   - Subscribe to that topic in the app.

3. **Add the topic as a GitHub secret:**
   - In your repo: Settings → Secrets and variables → Actions → New repository secret
   - Name: `NTFY_TOPIC`
   - Value: the topic name you picked (just the name, not the full URL)

4. **Enable the workflow.** It's already set to run every 30 minutes via
   cron, plus you can trigger it manually from the Actions tab to test it
   immediately (`workflow_dispatch`).

5. **Test it once manually:** Actions tab → "Check for new internship
   postings" → Run workflow. Check the logs — first run will report
   everything currently open as "new" (since state.json starts empty), so
   expect an initial burst of notifications. After that, you'll only hear
   about genuinely new postings.

## Adding more companies

Add an entry to `companies.json`:

- If the company uses Greenhouse (`job-boards.greenhouse.io/<token>`), use
  `"type": "greenhouse"` with the board token from that URL.
- If it uses SmartRecruiters (`careers.smartrecruiters.com/<CompanyId>`), use
  `"type": "smartrecruiters"` with that company ID.
- Otherwise use `"type": "html_keyword"` with the careers page URL as a
  best-effort fallback.

## Adjusting the check frequency

Edit the `cron` line in the workflow file. `*/30 * * * *` is every 30
minutes; GitHub's minimum reliable interval is about 5 minutes, though it can
run a bit late during high load on their infrastructure — that's a GitHub
limitation, not something this script controls.
