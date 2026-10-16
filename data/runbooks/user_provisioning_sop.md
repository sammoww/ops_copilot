---
document_id: SOP-SEC-204
title: Enterprise User Identity Provisioning, SCIM Integration & Break-Glass Access SOP
category: Identity & Access Management (IAM)
security_classification: Confidential / Internal Only
last_updated: 2026-10-12
compliance_frameworks:
  - SOC2 Type II
  - ISO/IEC 27001
  - FedRAMP Moderate
author: Cloud Security & Governance Team
---

# Enterprise User Identity Provisioning, SCIM Integration & Break-Glass SOP

## 1. Scope & Architectural Overview
This Standard Operating Procedure (SOP) specifies the end-to-end lifecycle management of employee, contractor, and service accounts across corporate cloud infrastructure.

Identity synchronization relies on the **SCIM 2.0 (System for Cross-domain Identity Management)** protocol integrated between our central Identity Provider (IdP: Okta / Microsoft Entra ID) and downstream microservices.

---

## 2. Role-Based Access Control (RBAC) Matrix

Account roles are assigned automatically based on Active Directory security groups:

| RBAC Role Name | Target Scope | Session TTL | MFA Requirement | Approval Workflow |
| :--- | :--- | :--- | :--- | :--- |
| `dev-readonly` | Staging / Non-prod clusters | 12 Hours | TOTP or FIDO2 WebAuthn | Auto-provisioned on hire |
| `dev-engineer` | Read/Write Staging, Read-only Prod | 8 Hours | Hardware Key (YubiKey) | Engineering Manager |
| `sre-oncall` | Production telemetry, deployment, pods | 4 Hours | Hardware Key + Biometric | SRE Lead + Security Ops |
| `infra-admin` | Full cloud root, KMS keys, VPC routing | 1 Hour | 2-Person Quorum + YubiKey | VP Engineering + CISO |

---

## 3. Automated SCIM Synchronization & Common Faults

All provisioning calls pass through our ingress SCIM Gateway (`https://idp-bridge.internal.corp/v2/scim`).

### Common SCIM Error Codes & Triage Steps

| HTTP Status / Error Code | Root Cause Description | Immediate Remediation Action |
| :--- | :--- | :--- |
| `ERR_401_SCIM_TOKEN_EXPIRED` | Bearer token TTL (90 days) exceeded | Rotate SCIM secret in HashiCorp Vault path `secret/idp/scim-bearer` |
| `ERR_409_USER_CONFLICT` | Duplicate email or collision in UPN (User Principal Name) | Run deduplication query in PostgreSQL directory table |
| `ERR_422_UNPROCESSABLE_USER` | Missing mandatory Department or Cost-Center attribute | Update HR Workday record to populate required schema fields |
| `ERR_403_ELEVATION_DENIED` | User attempted privilege escalation without ticket approval | Log security audit alert to SIEM / Datadog Security |

### Step 3.1: Re-synchronizing a Failed User Profile
If a user fails automated provisioning:
```bash
curl -X POST https://idp-bridge.internal.corp/v2/scim/Users/sync \
  -H "Authorization: Bearer $(vault kv get -field=token secret/idp/scim-bearer)" \
  -H "Content-Type: application/json" \
  -d '{
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
    "filter": "userName eq \"alex.chen@internal.corp\""
  }'
```
Expected response: `HTTP 200 OK` with JSON payload `{"status": "SYNCHRONIZED", "groups_mapped": 4}`.

---

## 4. Break-Glass Emergency Privilege Escalation

During severe P1/P0 outages where normal SSO authentication is unavailable (e.g., Okta outage or Cloudflare access proxy down), authorized engineers may invoke the **Break-Glass Emergency Protocol**.

### Conditions for Invocation:
1. P1/P0 incident actively open in incident management system.
2. Central SSO service is unreachable for > 10 minutes.
3. Two senior engineers (one SRE and one Security Engineer) are physically or virtually present.

### Step 4.1: Retrieve Break-Glass Credentials
Emergency root credentials are split into two halves stored in dual-control physical safes and AWS Secrets Manager with KMS multi-party encryption:
```bash
aws secretsmanager get-secret-value \
  --secret-id prod/break-glass/sre-root \
  --version-stage AWSCURRENT \
  --query SecretString \
  --output text
```

### Step 4.2: Audit Logging & Time-Boxed Revocation
- The break-glass session is strictly time-boxed to **60 minutes**.
- All commands typed during a break-glass session are automatically mirrored to an immutable S3 audit bucket (`s3://corp-audit-immutable-logs/break-glass/`) with object lock enabled.
- Immediately upon incident resolution, the break-glass password must be rotated using the emergency rotation script:
```bash
/opt/security/bin/rotate_breakglass_creds.sh --cluster prod-primary
```

---

## 5. Account Deprovisioning & Offboarding Protocol

When an employee or contractor terminates employment:
1. Workday emits an offboarding webhook event within **15 minutes** of HR action.
2. SCIM Gateway sends `PATCH` with `"active": false` to revoke all active JWT tokens across all microservices immediately.
3. Active SSH keys from `~/.ssh/authorized_keys` across all production bastion hosts are pruned within **300 seconds** via Ansible pull.
