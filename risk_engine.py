"""
Vendor Risk Scoring Engine
Computes a composite risk score (0-100) per vendor across four weighted dimensions:
  1. Compliance Risk (35%)  - KYC status, cert coverage/expiry, compliance check results
  2. Financial/Concentration Risk (25%) - spend concentration, payment disputes
  3. Geographic Risk (20%) - country risk weight
  4. Audit History Risk (20%) - open/overdue findings, severity

Writes results back to the SQLite DB (new table: vendor_risk_scores) and
exports flat CSVs for Power BI / Excel consumption.
"""

import sqlite3
import pandas as pd
from datetime import datetime

DB = "vendor_risk.db"

def load_tables(conn):
    vendors = pd.read_sql("SELECT * FROM vendors", conn)
    txns = pd.read_sql("SELECT * FROM transactions", conn)
    checks = pd.read_sql("SELECT * FROM compliance_checks", conn)
    findings = pd.read_sql("SELECT * FROM audit_findings", conn)
    return vendors, txns, checks, findings

def compliance_risk(vendors, checks):
    # KYC incomplete -> +40 pts; no certifications -> +20 pts; expired cert -> +25 pts
    today = pd.Timestamp(datetime.now().date())
    df = vendors.copy()
    df["cert_expiry_date"] = pd.to_datetime(df["cert_expiry_date"], errors="coerce")
    score = pd.Series(0.0, index=df.index)
    score += (df["kyc_complete"] == 0) * 40
    score += (df["certifications"] == "None") * 20
    score += ((df["cert_expiry_date"].notna()) & (df["cert_expiry_date"] < today)) * 25

    # worst compliance check result in trailing 12 months
    checks["check_date"] = pd.to_datetime(checks["check_date"])
    recent = checks[checks["check_date"] > today - pd.Timedelta(days=365)]
    result_penalty = {"Pass": 0, "Minor Issues": 8, "Major Issues": 20, "Fail": 35}
    recent = recent.copy()
    recent["penalty"] = recent["result"].map(result_penalty)
    worst = recent.groupby("vendor_id")["penalty"].max()
    df = df.merge(worst.rename("check_penalty"), left_on="vendor_id", right_index=True, how="left")
    df["check_penalty"] = df["check_penalty"].fillna(10)  # no recent check = mild penalty
    score += df["check_penalty"]

    return (score.clip(0, 100)).rename("compliance_risk_score")

def financial_risk(vendors, txns):
    spend = txns.groupby("vendor_id")["amount"].sum().rename("total_spend")
    total = spend.sum()
    disputed = txns[txns["payment_status"] == "Disputed"].groupby("vendor_id").size().rename("disputed_count")
    anomalies = txns.groupby("vendor_id")["flagged_anomaly"].sum().rename("anomaly_count")

    df = vendors[["vendor_id"]].merge(spend, on="vendor_id", how="left") \
                                .merge(disputed, on="vendor_id", how="left") \
                                .merge(anomalies, on="vendor_id", how="left").fillna(0)
    df["spend_share_pct"] = (df["total_spend"] / total * 100)
    # concentration: spend share scaled, capped; disputes and anomalies add risk
    score = (df["spend_share_pct"] * 8).clip(0, 50) \
        + (df["disputed_count"] * 6).clip(0, 25) \
        + (df["anomaly_count"] * 10).clip(0, 25)
    df["financial_risk_score"] = score.clip(0, 100)
    return df[["vendor_id", "total_spend", "spend_share_pct", "disputed_count", "anomaly_count", "financial_risk_score"]]

def geo_risk(vendors):
    return (vendors["geo_risk_weight"] * 100).rename("geo_risk_score")

def audit_risk(vendors, findings):
    sev_weight = {"Low": 10, "Medium": 20, "High": 35, "Critical": 55}
    f = findings.copy()
    f["weight"] = f["severity"].map(sev_weight).astype(float)
    f.loc[f["status"] == "Remediated", "weight"] *= 0.2  # resolved issues count less
    f.loc[f["status"] == "Overdue", "weight"] *= 1.3      # overdue issues count more
    agg = f.groupby("vendor_id")["weight"].sum().rename("audit_risk_raw")
    df = vendors[["vendor_id"]].merge(agg, on="vendor_id", how="left").fillna(0)
    df["audit_risk_score"] = df["audit_risk_raw"].clip(0, 100)
    return df[["vendor_id", "audit_risk_score"]]

def main():
    conn = sqlite3.connect(DB)
    vendors, txns, checks, findings = load_tables(conn)

    comp = compliance_risk(vendors, checks)
    fin = financial_risk(vendors, txns)
    geo = geo_risk(vendors)
    aud = audit_risk(vendors, findings)

    result = vendors[["vendor_id", "vendor_name", "category", "country",
                       "annual_contract_value", "is_critical_supplier"]].copy()
    result["compliance_risk_score"] = comp
    result["geo_risk_score"] = geo
    result = result.merge(fin, on="vendor_id")
    result = result.merge(aud, on="vendor_id")

    result["composite_risk_score"] = (
        result["compliance_risk_score"] * 0.35 +
        result["financial_risk_score"] * 0.25 +
        result["geo_risk_score"] * 0.20 +
        result["audit_risk_score"] * 0.20
    ).round(1)

    def tier(s):
        if s >= 45: return "Critical"
        if s >= 33: return "High"
        if s >= 20: return "Medium"
        return "Low"
    result["risk_tier"] = result["composite_risk_score"].apply(tier)

    result = result.sort_values("composite_risk_score", ascending=False).reset_index(drop=True)

    # write back to db
    result.to_sql("vendor_risk_scores", conn, if_exists="replace", index=False)

    # export flat files for Power BI / Excel
    result.to_csv("exports/vendor_risk_scores.csv", index=False)
    vendors.to_csv("exports/vendors.csv", index=False)
    txns.to_csv("exports/transactions.csv", index=False)
    checks.to_csv("exports/compliance_checks.csv", index=False)
    findings.to_csv("exports/audit_findings.csv", index=False)

    conn.commit()
    conn.close()

    print(result["risk_tier"].value_counts())
    print("\nTop 10 highest-risk vendors:")
    print(result[["vendor_id","vendor_name","category","country","composite_risk_score","risk_tier"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
