# web-segment

**Give a website URL, get back a structured business profile.**

A Python service that crawls a business website, pulls out contact details, and uses the OpenAI API plus the
PageSpeed Insights API to infer *who this business is* — name, sport/topic focus, account type, location,
language, and the technical health of the site. Built to feed a CRM automatically instead of having a human
open tabs and read "About Us" pages all day.

```
https://example.com  ──▶  scrape  ──▶  regex contacts  ──▶  LLM segmentation  ──▶  PageSpeed scores  ──▶  JSON / CRM
```

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?logo=openai&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-webhook-000000?logo=flask&logoColor=white)
![Status](https://img.shields.io/badge/status-archived%20internship%20project-lightgrey)

---

## Background

This was built during my **automation internship at CoachIQ ([AthleticOutlook, Inc.](https://coachiq.io))**,
a business-management SaaS for sports coaches and training facilities, where I worked as a 1099 contractor from
September 2023 to April 2024.

The sales team's prospecting loop started with a spreadsheet full of URLs and ended with a human copy-pasting
research into [Zoho CRM](https://www.zoho.com/crm/): what the business is called, what sport they coach, whether
they're a club, a facility, or a college program, where they are, and whether their website is even functional.
That research step was the bottleneck, and it was the same ten questions every time.

`web-segment` was my answer: an endpoint that takes a URL and a CRM account ID and returns a ready-to-import
record. It ended up running as a webhook that enriched prospects on demand and pushed results into Zoho, replacing
the manual pass entirely.

The domain vocabulary in [`openai_segment.py`](web_segment/openai_segment.py) (account types like *"Batting Cages
Only"*, *"7v7 Team"*, *"Prep School"*; areas of focus from *Australian Football* to *Yoga*) comes from CoachIQ's
CRM taxonomy — that's the part that makes the LLM output actually usable downstream rather than free-form prose.

## What it does

| Step | Module | Output |
|---|---|---|
| Crawl the site | [`site_scraper.py`](web_segment/site_scraper.py) | Sitemap discovery (including `sitemap_index.xml`), link-following fallback, per-page text |
| Pull contact data | [`manual_parse.py`](web_segment/manual_parse.py) | Emails, phone numbers, social links via regex |
| Select the pages worth reading | [`openai_segment.py`](web_segment/openai_segment.py) | Keyword match first (`home`, `about`, `contact`, …), LLM page picker when the keyword set is thin |
| Infer business attributes | [`openai_segment.py`](web_segment/openai_segment.py) | `businessName`, `areaOfFocus`, `accountType`, `location`, `language` |
| Audit the site | PageSpeed Insights API | Lighthouse `performance` / `accessibility` / `best_practices` / `seo` + HTTPS |
| Emit a record | [`site_segmentation.py`](web_segment/site_segmentation.py) | JSON to stdout/file, and optionally POSTed to a CRM endpoint |

Two entry points: a CLI for one-off runs, and [`webhook.py`](web_segment/webhook.py) — a Flask app that takes the
request, spawns the work on a thread, and returns `200` immediately so the caller doesn't block on a slow crawl.

## Output

```json
{
  "status": "success",
  "url": "https://example.com/",
  "accountId": "1234567890",
  "contact_info": {
    "emails": "info@example.com",
    "phoneNumbers": "(555) 010-0000",
    "socialMediaLinks": "https://www.instagram.com/example/"
  },
  "segmentation": {
    "businessName": "Example Sports Academy",
    "areaOfFocus": "Basketball",
    "accountType": "Training Facility",
    "location": "Denver, CO"
  },
  "site_analysis": {
    "language": "English",
    "hasSitemap": true,
    "pageCount": 14,
    "lastModified": -1,
    "performance": 0.89,
    "accessibility": 1.0,
    "best_practices": 1.0,
    "seo": 0.92
  },
  "tech_analysis": { "HTTPS": true }
}
```

Failures don't raise — the record comes back with `"status": "failure"` and an `error` message, so a batch run
can log the bad URL and keep going. (One dead subpage shouldn't kill an entire site's result.)

## Quick start

```sh
git clone https://github.com/Sam-Cleveland/web-segment.git
cd web-segment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then fill in your keys
set -a; source .env; set +a
```

Segment a single site from the command line:

```sh
python web_segment/site_segmentation.py https://example.com
python web_segment/site_segmentation.py https://example.com basic   # skip PageSpeed + deep crawl
```

The result is printed and written to `output/<domain>.json`, followed by a token-usage report:

```
Chat token usage: 4213
Chat prompt count: 3
Assistants token usage: 0
```

Run the webhook:

```sh
python web_segment/webhook.py 5000 127.0.0.1 debug
```

```sh
curl -X POST http://127.0.0.1:5000/scrape_site \
  -H "Authorization: $WEBHOOK_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com", "accountId": "1234567890", "send_to_zoho": false}'
```

Deploy it behind a real WSGI server:

```sh
pip install gunicorn
gunicorn -b 0.0.0.0:5000 web_segment.webhook:app
```

> **Note:** everything runs on a background thread with logging to `logs/<domain>_<timestamp>.log`. The endpoint
> returns as soon as the job is queued, so it needs a long-running process (Gunicorn, not a serverless handler).

### Webhook request body

| Field | Default | Meaning |
|---|---|---|
| `url` | *(required)* | Site to segment |
| `accountId` | *(required)* | CRM account to attach the result to |
| `use_openai` | `true` | Skip the LLM segmentation entirely |
| `use_pagespeed` | `true` | Skip the Lighthouse audit |
| `openai_model` | `gpt-3.5-turbo` | Model for the chat-completion calls |
| `save_output` | `false` | Also write `output.json` |
| `send_to_zoho` | `true` | POST the result to `ZOHO_API_URL` |

## Configuration

Read from environment variables — nothing is hardcoded ([`.env.example`](.env.example)).

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | for LLM steps | Standard OpenAI key; read by the SDK |
| `OPENAI_MODEL` | no | Chat model, defaults to `gpt-3.5-turbo` |
| `OPENAI_SUMMARIZER_ASSISTANT_ID` | no | Assistant used to condense scraped text (file upload + thread run). Unset → falls back to a chat completion |
| `ZOHO_API_URL` | no | CRM function endpoint to POST the record to. Unset → export is skipped with a warning |
| `WEBHOOK_API_KEY` | for the webhook | Value expected in the `Authorization` header. Unset → the server refuses requests |

## Design notes

A few things I'd carry into the next version of this:

- **Cost is a design constraint, not an afterthought.** A 40-page site doesn't fit in a prompt, so page selection is
  two-stage: URL keywords catch the obvious candidates (`home`, `about`, `contact`, `learn`), and only when that set
  is thin does an LLM see the URL list and pick up to ten pages. Every call accumulates `chat_tokens_usage` /
  `assistant_tokens_usage`, printed at the end — the intern running a 200-URL batch knew what it cost.
- **Regex where regex is honest.** Emails and phone numbers are cheap and exact; there's no reason to ask a model to
  guess them. The LLM is reserved for the fuzzy judgement calls.
- **Constrain the model to the taxonomy, then repair it.** The prompts demand one of a fixed list of account types
  and areas of focus, and a fuzzy matcher fixes near-misses (`"basketball training"` → `Basketball`) before the
  record is trusted. A malformed JSON response returns nulls rather than crashing the run.
- **A typed downstream schema is unforgiving.** The Zoho function endpoint rejected early payloads outright
  (`INVALID_DATA` on a missing `hasSitemap`), which is why the output object has a fixed, fully populated shape
  with `null` placeholders instead of a sparse or flat structure.
- **Retries where the model is flaky.** The summarizer retries if it returns fewer than 300 characters, and sitemap
  dates fall back to `-1` rather than failing a whole site on a malformed `<lastmod>`.

## Limitations

- Written against the OpenAI API as of early 2024 (`openai==1.9.0`) — the Assistants calls in particular have moved
  on since.
- The taxonomy (`AREA_OF_FOCUS`, account types) is sports-business-specific. Swap those lists for your own domain
  and the pipeline generalizes, but the prompts are tuned for this one.
- No test suite. This was a paid deliverable for a single internal consumer, and the "test" was a batch of real
  prospects landing correctly in the CRM.
- Scraping is polite-but-basic: a single browser User-Agent, no JS rendering, no rate limiting. Heavier sites (or
  anything client-rendered) will yield thin text.

This repo is published as a work sample. The CRM it wrote to and the keys it used were CoachIQ's; those are
configurable now, so it stands on its own.

## Repo layout

```
web_segment/
  site_segmentation.py   # pipeline orchestrator + CLI
  site_scraper.py        # sitemap discovery, page fetching, text extraction
  openai_segment.py      # prompts, page selection, segmentation, token accounting
  manual_parse.py        # regex extraction for emails / phones / social links
  webhook.py             # Flask endpoint (+ Gunicorn deployment)
requirements.txt
.env.example
```

---

Samuel Cleveland · [github.com/Sam-Cleveland](https://github.com/Sam-Cleveland) · smclevel@ucsc.edu
