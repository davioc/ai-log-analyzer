# Runbook: Database Connection Timeout
**Target Services:** database-service, auth-service

## Symptom
Log shows "Database Connection Timeout on pool acquisition" or 500 status codes during peak loads.

## Immedieate Mitigation Steps
1. Check primary DB host CPU and memory utilization.
2. Verify connection pool max limit in application configuration.
3. Restart connection pool or service instance if pool leak is detected.
4. Scale DB read-replicas if connection count is saturated.