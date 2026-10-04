# Runbook: High Rate Limiter Triggers (HTTP 429)
**Target Services:** auth-gateway, api-gateway

## Symptom
Log shows 429 status code spikes or "Rate limiter triggered user_id=...".

## Immediate Mitigation Steps
1. Inspect IP address and user_id associated with 429 logs to check for DDoS or misconfigured scraper.
2. Temporarily adjust rate limit thresholds in gateway configuration if traffic is legitimate.
3. Apply IP block rule at WAF level if malicious brute-force attack is identified.