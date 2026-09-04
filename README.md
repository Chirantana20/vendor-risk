# Vendor Risk & Compliance Monitoring System
*A Risk Advisory analytics project*

## Project Summary
An end-to-end vendor risk and compliance monitoring solution simulating a Risk Advisory engagement: ingesting vendor master data, transaction history, compliance check records, and audit findings into a relational database, computing a composite risk score per vendor, and surfacing the results through a Power BI dashboard, an Excel remediation tracker, and a documented automation workflow.

## Architecture
```
generate_data.py   → synthetic dataset (500 vendors, 6000 transactions,
                      1200+ compliance checks, 180 audit findings)
        ↓
vendor_risk.db (SQLite)  →  4 normalized tables
        ↓
risk_engine.py     → composite risk scoring (4 weighted dimensions)
        ↓
   ┌────────────┬─────────────────┬──────────────────────┐
   ↓            ↓                 ↓                       ↓
exports/*.csv   Excel Tracker    Power BI data model     SQL showcase
(Power BI       (findings        + DAX measures           queries
 source)        remediation      + build guide
                 workflow)
```

## Risk Scoring Methodology
Composite score (0–100) = weighted blend of:
- **Compliance Risk (35%)** — KYC completion, certification coverage/expiry, recent compliance check results
- **Financial/Concentration Risk (25%)** — spend concentration, payment disputes, transaction anomalies
- **Geographic Risk (20%)** — country risk weighting
- **Audit History Risk (20%)** — open/overdue findings, severity-weighted

Tiers: Critical (≥45) / High (≥33) / Medium (≥20) / Low. Current run: 5 Critical, 37 High, 211 Medium, 247 Low vendors.

## Files in this delivery
| File | Purpose |
|---|---|
| `generate_data.py` | Synthetic data generator (reproducible, seeded) |
| `risk_engine.py` | Risk scoring engine (pandas) |
| `vendor_risk.db` | SQLite database — all 5 tables |
| `sql_query_showcase.sql` | 7 validated MIS/risk SQL queries |
| `exports/*.csv` | Flat files for Power BI / Excel |
| `exports/Vendor_Audit_Findings_Tracker.xlsx` | Advanced Excel tracker — formulas, conditional formatting, pivot summary (zero formula errors) |
| `exports/powerbi/DAX_Measures.md` | DAX measures reference |
| `exports/powerbi/PowerBI_Build_Guide.md` | Page-by-page dashboard build spec |
| `exports/powerbi/Power_Automate_Workflow_Design.md` | Documented alert automation flow |
