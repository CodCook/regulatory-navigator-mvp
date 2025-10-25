import os
import sys

# Ensure the repo root is on sys.path so imports like `ai_extractor` and `app` work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_extractor import run_extraction
import app
import json

sample_text = (
    "ACME P2P Ltd is building a peer-to-peer payments network. We do not yet have a deployed monitoring system; "
    "Our policy retains certain records for 7 years. Paid-Up Capital: QAR 1,000,000. Data stored in Qatar. "
    "We have a compliance officer and a board-approved AML policy. AoA: signed."
)

print('Running internal validation without HTTP...')
extracted = run_extraction(sample_text)
print('\nExtracted:')
print(json.dumps(extracted, indent=2))

failed_gaps = app.run_gap_analysis(extracted)
print('\nFailed gaps:')
print(json.dumps(failed_gaps, indent=2))

# Reuse the same scoring logic from app.calculate_scorecard but without flask request
SECTION_WEIGHTS = app.SECTION_WEIGHTS or {'Licensing & Capital':30,'Transaction Monitoring':25,'Digital Consumer Protection':15,'Corporate Governance':15,'AML & KYC':15}
REGULATORY_CHECKS = app.REGULATORY_CHECKS

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
for chk in REGULATORY_CHECKS.keys():
    sec = CHECK_TO_SECTION.get(chk)
    if not sec:
        continue
    section_checks.setdefault(sec, []).append(chk)

# compute deductions
section_deductions = {sec:0 for sec in SECTION_WEIGHTS.keys()}
for gap in failed_gaps:
    sec = CHECK_TO_SECTION.get(gap)
    if not sec or sec not in SECTION_WEIGHTS:
        continue
    checks_in_section = section_checks.get(sec, [])
    if not checks_in_section:
        continue
    per_check_deduction = SECTION_WEIGHTS[sec] / len(checks_in_section)
    section_deductions[sec] += per_check_deduction

score_lost = sum(section_deductions.values())
final_score = max(0, sum(SECTION_WEIGHTS.values()) - score_lost)

print('\nSection deductions:')
print(json.dumps(section_deductions, indent=2))
print('\nFinal score:', round(final_score))

# recommendations via app.generate_recommendations
recs = app.generate_recommendations(failed_gaps)
print('\nRecommendations:')
print(json.dumps(recs, indent=2))
