"""
Vendor Risk & Compliance Monitoring - Synthetic Data Generator
KPMG-style Risk Advisory portfolio project

Generates a realistic vendor risk dataset:
- Vendors (master data, certifications, KYC)
- Transactions (12 months of spend)
- Compliance Checks (periodic reviews)
- Audit Findings (issues raised, remediation status)
"""

import random
import sqlite3
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

N_VENDORS = 500
N_TRANSACTIONS = 6000
N_AUDIT_FINDINGS = 180

CATEGORIES = ["IT Services", "Logistics", "Professional Services", "Manufacturing",
              "Facilities", "Marketing", "Raw Materials", "Software Licensing"]

COUNTRIES_RISK = {
    # country: baseline geo risk weight (0-1)
    "India": 0.2, "United States": 0.1, "Germany": 0.1, "United Kingdom": 0.1,
    "China": 0.4, "Russia": 0.7, "Brazil": 0.3, "Nigeria": 0.6,
    "Singapore": 0.15, "UAE": 0.3, "Mexico": 0.35, "Vietnam": 0.4,
    "France": 0.1, "South Africa": 0.35, "Pakistan": 0.55
}

CERTIFICATIONS = ["ISO 27001", "SOC 2 Type II", "ISO 9001", "GDPR Compliant", "PCI-DSS"]
FINDING_TYPES = ["Missing KYC Documentation", "Expired Certification", "Contract Non-Compliance",
                  "Pricing Discrepancy", "Unauthorized Subcontracting", "Data Security Gap",
                  "Late Delivery Pattern", "Conflict of Interest Flag", "Invoice Duplication Risk"]
SEVERITY = ["Low", "Medium", "High", "Critical"]
STATUS = ["Open", "In Progress", "Remediated", "Overdue"]

def gen_vendors():
    vendors = []
    countries = list(COUNTRIES_RISK.keys())
    for i in range(1, N_VENDORS + 1):
        country = random.choices(countries, weights=[1/COUNTRIES_RISK[c]*0.3+0.5 for c in countries])[0]
        onboarded = fake.date_between(start_date="-5y", end_date="-30d")
        kyc_complete = random.random() > 0.12
        n_certs = random.choices([0,1,2,3], weights=[0.15,0.35,0.35,0.15])[0]
        certs = random.sample(CERTIFICATIONS, n_certs)
        cert_expiry = fake.date_between(start_date="-6m", end_date="+18m") if certs else None
        contract_value = round(random.lognormvariate(10.5, 1.3), 2)
        vendors.append({
            "vendor_id": f"V{i:04d}",
            "vendor_name": fake.company(),
            "category": random.choice(CATEGORIES),
            "country": country,
            "onboarded_date": onboarded.isoformat(),
            "kyc_complete": int(kyc_complete),
            "certifications": ";".join(certs) if certs else "None",
            "cert_expiry_date": cert_expiry.isoformat() if cert_expiry else None,
            "annual_contract_value": contract_value,
            "geo_risk_weight": COUNTRIES_RISK[country],
            "is_critical_supplier": int(contract_value > 200000 and random.random() > 0.5)
        })
    return vendors

def gen_transactions(vendors):
    txns = []
    vendor_ids = [v["vendor_id"] for v in vendors]
    start = datetime.now() - timedelta(days=365)
    for i in range(1, N_TRANSACTIONS + 1):
        vid = random.choice(vendor_ids)
        date = start + timedelta(days=random.randint(0, 365))
        amount = round(random.lognormvariate(8.5, 1.4), 2)
        # inject a small % of anomalies: round-number/duplicate-like high invoices
        is_anomaly = random.random() < 0.03
        if is_anomaly:
            amount = round(amount * random.uniform(3, 6), 2)
        txns.append({
            "transaction_id": f"T{i:06d}",
            "vendor_id": vid,
            "transaction_date": date.date().isoformat(),
            "amount": amount,
            "payment_status": random.choices(["Paid","Pending","Disputed"], weights=[0.85,0.1,0.05])[0],
            "flagged_anomaly": int(is_anomaly)
        })
    return txns

def gen_compliance_checks(vendors):
    checks = []
    cid = 1
    for v in vendors:
        n_checks = random.randint(1, 4)
        for _ in range(n_checks):
            check_date = fake.date_between(start_date="-2y", end_date="today")
            result = random.choices(["Pass","Minor Issues","Major Issues","Fail"], weights=[0.55,0.25,0.13,0.07])[0]
            checks.append({
                "check_id": f"C{cid:05d}",
                "vendor_id": v["vendor_id"],
                "check_date": check_date.isoformat(),
                "check_type": random.choice(["KYC Refresh","Financial Health","Certification Review","On-site Audit","Self-Assessment"]),
                "result": result
            })
            cid += 1
    return checks

def gen_audit_findings(vendors):
    findings = []
    critical_pool = [v["vendor_id"] for v in vendors]
    for i in range(1, N_AUDIT_FINDINGS + 1):
        vid = random.choice(critical_pool)
        raised = fake.date_between(start_date="-540d", end_date="-5d")
        severity = random.choices(SEVERITY, weights=[0.35,0.35,0.22,0.08])[0]
        sla_days = {"Low": 60, "Medium": 30, "High": 14, "Critical": 7}[severity]
        due_date = raised + timedelta(days=sla_days)
        status = random.choices(STATUS, weights=[0.2,0.25,0.45,0.1])[0]
        resolved_date = None
        if status == "Remediated":
            resolved_date = raised + timedelta(days=random.randint(3, sla_days + 20))
        elif status == "Overdue":
            due_date = fake.date_between(start_date="-60d", end_date="-1d")
        findings.append({
            "finding_id": f"F{i:04d}",
            "vendor_id": vid,
            "finding_type": random.choice(FINDING_TYPES),
            "severity": severity,
            "raised_date": raised.isoformat(),
            "due_date": due_date.isoformat(),
            "status": status,
            "resolved_date": resolved_date.isoformat() if resolved_date else None,
            "owner": fake.name()
        })
    return findings

def build_database():
    vendors = gen_vendors()
    transactions = gen_transactions(vendors)
    checks = gen_compliance_checks(vendors)
    findings = gen_audit_findings(vendors)

    conn = sqlite3.connect("vendor_risk.db")
    cur = conn.cursor()

    cur.execute("""CREATE TABLE vendors (
        vendor_id TEXT PRIMARY KEY, vendor_name TEXT, category TEXT, country TEXT,
        onboarded_date TEXT, kyc_complete INTEGER, certifications TEXT, cert_expiry_date TEXT,
        annual_contract_value REAL, geo_risk_weight REAL, is_critical_supplier INTEGER)""")
    cur.execute("""CREATE TABLE transactions (
        transaction_id TEXT PRIMARY KEY, vendor_id TEXT, transaction_date TEXT,
        amount REAL, payment_status TEXT, flagged_anomaly INTEGER)""")
    cur.execute("""CREATE TABLE compliance_checks (
        check_id TEXT PRIMARY KEY, vendor_id TEXT, check_date TEXT, check_type TEXT, result TEXT)""")
    cur.execute("""CREATE TABLE audit_findings (
        finding_id TEXT PRIMARY KEY, vendor_id TEXT, finding_type TEXT, severity TEXT,
        raised_date TEXT, due_date TEXT, status TEXT, resolved_date TEXT, owner TEXT)""")

    cur.executemany("INSERT INTO vendors VALUES (:vendor_id,:vendor_name,:category,:country,:onboarded_date,:kyc_complete,:certifications,:cert_expiry_date,:annual_contract_value,:geo_risk_weight,:is_critical_supplier)", vendors)
    cur.executemany("INSERT INTO transactions VALUES (:transaction_id,:vendor_id,:transaction_date,:amount,:payment_status,:flagged_anomaly)", transactions)
    cur.executemany("INSERT INTO compliance_checks VALUES (:check_id,:vendor_id,:check_date,:check_type,:result)", checks)
    cur.executemany("INSERT INTO audit_findings VALUES (:finding_id,:vendor_id,:finding_type,:severity,:raised_date,:due_date,:status,:resolved_date,:owner)", findings)

    conn.commit()
    conn.close()
    print(f"Database built: {len(vendors)} vendors, {len(transactions)} transactions, {len(checks)} compliance checks, {len(findings)} audit findings")

if __name__ == "__main__":
    build_database()
