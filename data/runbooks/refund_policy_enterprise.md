---
document_id: POL-FIN-108
title: Enterprise Service Level Agreement (SLA) Breach & Credit Refund Policy
category: Commercial Operations & Customer Finance
classification: Internal Business Policy
last_updated: 2026-10-10
governing_bodies:
  - Global Support Operations
  - Corporate Finance & Revenue Ops
version: 3.4.0
---

# Enterprise Service Level Agreement (SLA) Breach & Credit Refund Policy

## 1. Policy Purpose & Scope
This commercial operations document establishes the contractual formula, approval workflow, and ledger adjustment steps for issuing Service Level Agreement (SLA) credits and customer refunds following unexpected platform outages or performance degradation.

This policy applies exclusively to enterprise tier contracts (`Tier-1 Platinum` and `Tier-2 Diamond`) with committed monthly recurring revenue (MRR) exceeding **$10,000 USD**.

---

## 2. Monthly Uptime Commitments & Credit Tiers

Service availability is calculated per calendar month using the following standard formula:

$$\text{Monthly Uptime \%} = \frac{\text{Total Minutes in Month} - \text{Total Outage Minutes}}{\text{Total Minutes in Month}} \times 100$$

*Scheduled maintenance windows (pre-announced with ≥ 7 days written notice) and customer-induced misconfigurations are excluded from downtime calculations.*

### SLA Credit Compensation Grid

| Monthly Measured Uptime | Contract SLA Target | Service Credit Percentage | Maximum Dollar Cap |
| :--- | :--- | :--- | :--- |
| **99.90% – 99.94%** | 99.95% | **10%** of monthly invoice | $5,000 USD |
| **99.50% – 99.89%** | 99.95% | **25%** of monthly invoice | $15,000 USD |
| **99.00% – 99.49%** | 99.95% | **50%** of monthly invoice | $35,000 USD |
| **< 99.00% (Critical Breach)** | 99.95% | **100%** of monthly invoice | $100,000 USD |

---

## 3. Financial Approval Escalation Matrix

Credits are not automatically credited without verified audit approval. Escalation levels are determined strictly by the total credit amount requested:

| Credit Amount Range (USD) | Required Approver | SLA Processing Timeframe | System Approval Code |
| :--- | :--- | :--- | :--- |
| **$1 – $4,999** | Customer Success Team Lead | 2 Business Days | `SLA_CR_TIER1` |
| **$5,000 – $24,999** | Director of Customer Operations | 3 Business Days | `SLA_CR_TIER2` |
| **$25,000 – $74,999** | VP of Customer Experience | 5 Business Days | `SLA_CR_EXEC_VP` |
| **≥ $75,000** | Chief Financial Officer (CFO) | 7 Business Days | `SLA_CR_BOARD_CFO` |

---

## 4. Refund Claim Procedure

Customers must formally submit a request within **thirty (30) calendar days** of the end of the billing cycle in which the breach occurred.

### Step 4.1: Claim Ingestion & Ticket Verification
When a customer logs a ticket categorized as `Billing / SLA Claim`, the support agent must:
1. Verify customer account status is active and in good standing (no invoices overdue > 60 days).
2. Validate ticket against the root cause analysis (RCA) incident ID (e.g., `INC-2026-10-09-DB-FAILOVER`).
3. If downtime duration claimed by the customer exceeds official Datadog synthetic monitor downtime by **> 15 minutes**, reject the discrepancy with reference code `ERR_SLA_DURATION_MISMATCH`.

### Step 4.2: Calculating the Credit Amount
For an account with **$30,000 MRR** experiencing an outage resulting in **99.2%** uptime:
- Credit Rate: **50%**
- Total Credit: `0.50 * $30,000 = $15,000 USD`
- Required Approver: Director of Customer Operations (`SLA_CR_TIER2`).

### Step 4.3: NetSuite Billing Adjustment
Once digital approval is logged:
1. Navigate to NetSuite: `Transactions > Billing > Customer Invoices > Apply Credit Memo`.
2. Enter Memo Item Code: `REV-SLA-CREDIT-OP-01`.
3. Set Memo Effective Date: First day of the subsequent billing cycle.
4. If a direct cash refund is mandated by contract instead of an invoice credit, apply error check code `ERR_REFUND_LIMIT_EXCEEDED` if refund exceeds account quarterly spend.

---

## 5. Exclusions & Limitations

No SLA credits will be disbursed under the following scenarios:
1. Force majeure events (regional power grid failures, submarine fiber cuts).
2. Customer IP whitelisting or customer firewall misconfigurations.
3. Third-party dependency outages where customer opted out of multi-cloud redundancy.
4. Accounts operating under promotional trials, pilot licenses, or open-source tiers.
