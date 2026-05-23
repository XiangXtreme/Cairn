---
name: "cairn-headless-browser"
description: "Use for browser-driven crawling, request capture, dynamic page inspection, screenshots, form discovery, and analysis of headless crawl artifacts."
---

# Cairn Headless Browser

Use this skill when static HTTP probing is insufficient and the target needs Chrome-based exploration or request capture.

## Workflow

1. Confirm the target URL and whether anonymous browsing is enough.
2. Use a headless browser or crawler to capture reachable pages, scripts, requests, forms, and redirects.
3. Inspect generated request/response artifacts before drawing conclusions.
4. Group findings by path area such as `/admin`, `/api`, `/login`, `/static`, and `/docs`.
5. Feed high-value entry points back into Cairn as facts or focused intents.

## What To Preserve

- Discovered URLs and methods.
- Interesting forms, JSON payloads, or submitted fields.
- Response headers, cookies, redirects, and content types.
- Dynamic routes and scripts that reveal hidden API paths.

## Boundaries

- Do not switch into interactive login unless the current task explicitly requires it.
- If authentication, SSO, CAPTCHA, or MFA blocks coverage, record that as a coverage gap.
