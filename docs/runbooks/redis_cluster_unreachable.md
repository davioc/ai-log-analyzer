# Runbook: Redis Cluster Unreachable
**Target Services:** cache-service, auth-gateway

## Symptom
Log shows "Redis cluster unreachable" or 503 errors.

## Immediate Mitigation Steps
1. Verify network security group rules between app subnets and ElastiCache/Redis host.
2. Ping Redis node IP and check cluster node health status.
3. Fail over to secondary Redis replica if primary node is unresponsive.
4. Temporarily bypass cache read-through in application flags if cache is non-critical.