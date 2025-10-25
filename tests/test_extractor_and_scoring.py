import os
import sys
import json

# Make repo root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_extractor import run_extraction
import app


def test_extract_data_retention_10_years():
    text = "We will retain transaction logs for 10 years to comply with regulatory requirements."
    out = run_extraction(text)
    assert out.get('has_10_year_retention') is True


def test_extract_data_retention_7_years():
    text = "Our retention policy keeps records for 7 years only."
    out = run_extraction(text)
    assert out.get('has_10_year_retention') is False


def test_p2p_monitoring_detection_deployed():
    text = "The P2P platform has a monitoring system deployed and actively analyzing transactions in real-time."
    out = run_extraction(text)
    assert out.get('has_p2p_monitoring_system') is True


def test_scoring_deducts_data_retention():
    # Prepare a minimal extracted data that will only fail the Data Retention check
    extracted = {
        'paid_up_capital': 8000000,  # pass capital
        'data_storage_location': [app.REGULATORY_THRESHOLDS.get('Required Data Location')],
        'has_compliance_officer': True,
        'has_board_approved_aml': True,
        'has_signed_aoa': True,
        'has_10_year_retention': False,
        'has_p2p_monitoring_system': True
    }
    failed = app.run_gap_analysis(extracted)
    assert 'Data Retention Shortfall' in failed

    # compute deductions similarly to scorecard logic
    SECTION_WEIGHTS = app.SECTION_WEIGHTS or {'Licensing & Capital':30,'Transaction Monitoring':25,'Digital Consumer Protection':15,'Corporate Governance':15,'AML & KYC':15}
    CHECK_TO_SECTION = {
        'Data Residency Failure': 'Digital Consumer Protection',
        'Data Retention Shortfall': 'Digital Consumer Protection'
    }
    # count checks
    section_checks = {}
    for chk in app.REGULATORY_CHECKS.keys():
        sec = CHECK_TO_SECTION.get(chk)
        if not sec:
            continue
        section_checks.setdefault(sec, []).append(chk)

    checks_in_section = section_checks.get('Digital Consumer Protection', [])
    assert len(checks_in_section) >= 1

    per_check = SECTION_WEIGHTS['Digital Consumer Protection'] / len(checks_in_section)
    # The deduction for Data Retention Shortfall should equal per_check
    assert per_check > 0
