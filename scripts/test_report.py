import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json
import app

# Build a report from the demo text via internal functions (no HTTP)
text = app.FULL_STARTUP_TEXT
extracted = app.run_extraction(text)
failed = app.run_gap_analysis(extracted)

# Minimal duplication of scoring (reuse endpoint code path is simpler but we inline here)
SECTION_WEIGHTS = app.SECTION_WEIGHTS or {
    'Licensing & Capital': 30,
    'Transaction Monitoring': 25,
    'Digital Consumer Protection': 15,
    'Corporate Governance': 15,
    'AML & KYC': 15
}
CHECK_TO_SECTION = {
    'Capital Shortfall': 'Licensing & Capital',
    'AoA Submission': 'Licensing & Capital',
    'P2P Monitoring Gap': 'Transaction Monitoring',
    'Data Residency Failure': 'Digital Consumer Protection',
    'Data Retention Shortfall': 'Digital Consumer Protection',
    'Compliance Officer Missing': 'Corporate Governance',
    'Fit & Proper Docs Missing': 'Corporate Governance',
    'AML/CFT Policy Gap': 'AML & KYC'
}
section_checks = {}
for chk in app.REGULATORY_CHECKS.keys():
    sec = CHECK_TO_SECTION.get(chk)
    if sec:
        section_checks.setdefault(sec, []).append(chk)

deductions = {sec:0 for sec in SECTION_WEIGHTS}
for gap in failed:
    sec = CHECK_TO_SECTION.get(gap)
    if not sec or sec not in SECTION_WEIGHTS: continue
    checks = section_checks.get(sec, [])
    if not checks: continue
    per = SECTION_WEIGHTS[sec] / len(checks)
    deductions[sec] += per
score = max(0, sum(SECTION_WEIGHTS.values()) - sum(deductions.values()))

breakdown = []
for check_name, details in app.REGULATORY_CHECKS.items():
    sec = CHECK_TO_SECTION.get(check_name)
    checks = section_checks.get(sec, []) if sec else []
    wt = (SECTION_WEIGHTS.get(sec,0)/len(checks)) if checks else 0
    fail = check_name in failed
    breakdown.append({
        'check': check_name, 'status': 'FAIL' if fail else 'PASS', 'weight': wt, 'score_contribution': 0 if fail else wt
    })

recs = app.generate_recommendations(failed)
result = {
    'extracted_data': extracted,
    'readiness_score': round(score),
    'failed_gaps': failed,
    'score_breakdown': breakdown,
    'recommendations': recs
}

pdf = app.build_pdf_from_result(result)
open('sample_report.pdf', 'wb').write(pdf)
print('Wrote sample_report.pdf (bytes:', len(pdf), ')')
