---
document_id: RB-OPS-042
title: PostgreSQL High Availability & Primary Failover Runbook
category: Infrastructure & Database Reliability
severity_trigger: P1 / Critical
last_updated: 2026-10-14
author: SRE Reliability Engineering Team
target_systems:
  - aurora-pg-cluster-prod
  - pgpool-primary-node
  - patroni-ha-consensus
---

# PostgreSQL High Availability & Primary Failover Runbook

## 1. Overview & Purpose
This operational runbook defines the emergency mitigation procedure when the primary PostgreSQL database node becomes unresponsive, suffers disk corruption, or triggers automated replication desynchronization.

All SRE on-call engineers are authorized to initiate manual failover if automated consensus fails to resolve the primary node heartbeat failure within **180 seconds**.

---

## 2. Trigger Conditions & Alert Thresholds

A P1 incident is declared and this runbook is engaged when any of the following Prometheus/CloudWatch alerts fire:

| Alert Identifier | Threshold / Condition | Severity | Initial Triage Action |
| :--- | :--- | :--- | :--- |
| `ERR_503_DB_TIMEOUT` | Connection pool queue time > 4,500ms for 3 consecutive minutes | Critical | Inspect active connection exhaustion |
| `ERR_08006_CONNECTION_FAILURE` | TCP connection reset or dropped packet rate > 8% | Critical | Verify network mesh & primary health |
| `ERR_PG_REPL_LAG_CRITICAL` | Replication byte lag > 128 MB or wall time > 45 seconds | High | Halt write-heavy background migrations |
| `ERR_DISK_IO_THROTTLE` | Disk IOPS saturation = 100% or storage read queue > 64 | High | Check unindexed full-table scans |

---

## 3. Diagnostic & Pre-Failover Verification

Before taking down the active primary node, the on-call engineer must confirm that replica node 02 (`pg-replica-02.internal`) is synchronous and has not diverged.

### Step 3.1: Check Cluster Replication Status
Execute via the bastion jump-box:
```bash
ssh -i ~/.ssh/ops_bastion.pem ops-admin@bastion.internal
psql -h pg-primary.internal -U postgres -d postgres -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;"
```

**Expected Healthy State:**
- `sync_state`: `sync` (for node `10.0.12.44`)
- `replay_lag`: `< 00:00:02` (under 2 seconds)

If `replay_lag` exceeds **00:00:30** (30 seconds), manual failover will induce data loss. Escalate immediately to the Database Architect Lead before proceeding.

### Step 3.2: Verify Replica Readiness
Verify that PostgreSQL service on the failover target is accepting read queries:
```bash
pg_isready -h pg-replica-02.internal -p 5432 -t 5
```
Expected output: `pg-replica-02.internal:5432 - accepting connections`.

---

## 4. Execution: Manual Failover Steps

### Step 4.1: Isolate the Degraded Primary (Fence / STONITH)
To avoid a split-brain condition where two nodes attempt to accept writes concurrently, revoke the virtual IP address from the degraded primary:
```bash
sudo systemctl stop patroni.service
# Or if node is unresponsive, execute hypervisor power cut:
aws ec2 stop-instances --instance-ids i-0a8947bc12e88102 --force
```

### Step 4.2: Promote Synchronous Replica
Log into `pg-replica-02.internal` and issue the promotion command:
```bash
# Using standard PostgreSQL binary:
/usr/lib/postgresql/16/bin/pg_ctl promote -D /var/lib/postgresql/16/main
```
Verify the server state transition in the log file:
```bash
tail -n 25 /var/log/postgresql/postgresql-16-main.log
```
Look for: `LOG: received promote request` followed by `LOG: database system is ready to accept read-write connections`.

### Step 4.3: Switch Connection Pool Routing (PgBouncer)
Update the PgBouncer upstream host configuration to point write traffic to the newly promoted primary:
```bash
sed -i 's/host=10.0.12.10/host=10.0.12.44/' /etc/pgbouncer/pgbouncer.ini
systemctl reload pgbouncer
```

---

## 5. Post-Failover Verification & Health Check

Confirm application services are recovering from `ERR_503_DB_TIMEOUT`:

1. **Verify Read-Write Capabilities**:
   ```bash
   psql -h pgbouncer.internal -p 6432 -U app_user -d production -c "CREATE TEMP TABLE failover_check (id int); INSERT INTO failover_check VALUES (1); SELECT * FROM failover_check;"
   ```
2. **Inspect Error Rate Metric**:
   Ensure `HTTP 500 / 503` rate drops below **0.05%** across API gateways.
3. **Notify Stakeholders**:
   Post update to `#incident-sev1` Slack channel with timestamp, former primary instance ID, promoted replica instance ID, and estimated data loss window (target: 0ms).

---

## 6. Known Failure Modes & Rollback

- **Split-Brain Emergence**: If former primary comes back online before PgBouncer reload, connection conflicts will throw `ERR_28P01_INVALID_PASSWORD` or transaction rollback aborts. Always ensure old primary remains fenced until reconfigured as a standby.
- **Failback Procedure**: Never attempt failback during peak business hours (08:00–20:00 UTC). Re-seed the old primary as a follower using `pg_basebackup` off the new primary during scheduled maintenance.
