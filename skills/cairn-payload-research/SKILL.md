---
name: "cairn-payload-research"
description: "Use for payload crafting, bypass research, encoding transformations, and signal design when a vulnerability hypothesis already has an input point."
---

# Cairn Payload Research

Use this skill after reconnaissance or fuzzing has identified a plausible input point and you need to refine payloads without expanding into blind testing.

## Focus Areas

- Locate where user input enters the application and which parser consumes it.
- Identify filters, WAF behavior, canonicalization, and blocked characters.
- Try encoding transformations: URL encoding, double encoding, HTML entities, Unicode, case changes, null bytes when relevant.
- Define observable success and failure signals before running heavier tests.

## Starter Payload Families

- XSS: `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, `<svg onload=alert(1)>`
- SQLi: `' OR '1'='1`, `' UNION SELECT NULL--`, time-delay probes appropriate to the backend.
- SSTI: `{{7*7}}`, `${7*7}`, `<%= 7*7 %>`
- Command injection: `; id`, `| id`, `` `id` ``, blind timing probes such as `; sleep 5`

## Rules

- Keep payloads tied to one hypothesis.
- Preserve prerequisites and expected signals with each payload.
- If a payload fails, record whether it failed due to filtering, parser behavior, context mismatch, or target instability.
