"""
Accuracy Measurement Script for AI Extraction Module

This script tests the AI extractor against diverse test cases with ground truth labels
and calculates precision, recall, F1-score, and overall accuracy metrics.
"""

import os
import sys
import json
from typing import Dict, List, Any

# Make repo root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_extractor import run_extraction


# ============================================================================
# TEST DATASET WITH GROUND TRUTH LABELS
# ============================================================================

TEST_CASES = [
    {
        "name": "Al-Ameen Digital (Original Mock)",
        "text": """
        Al-Ameen Digital, LLC: Articles of Association (Excerpt) 
        1.2. Paid-Up Capital: The initial paid-up capital upon incorporation was QAR 5,000,000 (Five Million Qatari Riyals).
        Project Al-Ameen: Peer-to-Peer Investment Platform. Our primary activities are: Facilitation of peer-to-peer financing services. 
        Digital payment systems integration for seamless transactions.
        Al-Ameen Digital: Data Privacy and Customer Consent Policy. All customer data is currently processed and stored within our secure cloud environment, 
        hosted across the AWS regions in Ireland and Singapore. 
        We do not currently have a dedicated Compliance Officer but plan to assign these duties to the Head of Finance.
        Our policy for reporting suspicious transactions is currently under review by our external legal counsel.
        We retain customer transaction records for 7 years as per our internal policy.
        """,
        "ground_truth": {
            "paid_up_capital": 5000000,
            "business_categories": ["P2P Lending (Category 2)", "Payment Service Provider (Category 1)"],
            "data_storage_location": ["Ireland", "Singapore"],
            "has_compliance_officer": False,
            "has_board_approved_aml": False,
            "has_signed_aoa": True,
            "has_10_year_retention": False,
            "has_p2p_monitoring_system": False
        }
    },
    {
        "name": "PayQatar - Compliant Fintech",
        "text": """
        PayQatar LLC - Corporate Documents
        Paid-Up Capital: The company has secured QAR 10,000,000 in initial capital.
        Business Model: We operate as a Payment Service Provider offering digital payment processing and electronic money issuance services.
        Data Infrastructure: All customer data is stored and processed exclusively within data centers located in the State of Qatar.
        Governance: We have appointed Ms. Sarah Al-Thani as our dedicated Compliance Officer, independent from operational management.
        AML/CFT Policy: Our board-approved Anti-Money Laundering and Counter-Financing of Terrorism policy was ratified on March 15, 2025.
        Articles of Association have been signed and submitted to the Qatar Commercial Registry.
        Data Retention: We maintain transaction records for a period of 10 years in compliance with QCB requirements.
        Monitoring: Our transaction monitoring system is deployed and operational, providing real-time surveillance of all payment flows.
        """,
        "ground_truth": {
            "paid_up_capital": 10000000,
            "business_categories": ["Payment Service Provider (Category 1)"],
            "data_storage_location": ["State of Qatar"],
            "has_compliance_officer": True,
            "has_board_approved_aml": True,
            "has_signed_aoa": True,
            "has_10_year_retention": True,
            "has_p2p_monitoring_system": True
        }
    },
    {
        "name": "LendHub - P2P Platform",
        "text": """
        LendHub Qatar: Business Plan Executive Summary
        Initial Capitalization: Paid-Up Capital was QAR 7,500,000 upon establishment.
        Core Business: Peer-to-peer financing services connecting borrowers and lenders directly.
        Technology Stack: Cloud infrastructure hosted on AWS in the Ireland region for optimal performance.
        Compliance Status: We plan to hire a Compliance Officer in Q2 2026.
        Risk Management: AML policy is under development and will be presented to the board for approval next quarter.
        Record Keeping: Customer data and transaction logs are retained for ten years.
        """,
        "ground_truth": {
            "paid_up_capital": 7500000,
            "business_categories": ["P2P Lending (Category 2)"],
            "data_storage_location": ["Ireland"],
            "has_compliance_officer": False,
            "has_board_approved_aml": False,
            "has_signed_aoa": False,
            "has_10_year_retention": True,
            "has_p2p_monitoring_system": False
        }
    },
    {
        "name": "FinTech Innovators - Multi-Service",
        "text": """
        FinTech Innovators W.L.L.
        Capital Structure: Paid-Up Capital: QAR 12,000,000
        Services: We provide payment processing, digital payment systems, and facilitate peer-to-peer financing services.
        Data Compliance: All data is processed and stored within the State of Qatar using local data centers.
        Leadership: Our Compliance Officer, Mr. Ahmed Al-Kuwari, operates independently from business units.
        Policies: Board-approved AML/CFT policy implemented January 2025.
        Articles of Association signed and filed.
        We retain all records for 10 years.
        Real-time monitoring system is implemented and operational for all P2P transactions.
        """,
        "ground_truth": {
            "paid_up_capital": 12000000,
            "business_categories": ["Payment Service Provider (Category 1)", "P2P Lending (Category 2)"],
            "data_storage_location": ["State of Qatar"],
            "has_compliance_officer": True,
            "has_board_approved_aml": True,
            "has_signed_aoa": True,
            "has_10_year_retention": True,
            "has_p2p_monitoring_system": True
        }
    },
    {
        "name": "CryptoDoha - Non-Compliant Startup",
        "text": """
        CryptoDoha Trading Platform
        We started with QAR 2,000,000 in seed funding.
        Our platform enables peer-to-peer cryptocurrency trading and digital asset transfers.
        Infrastructure: Hosted on AWS Singapore for low latency.
        Team: Our CFO handles compliance matters alongside financial reporting.
        We're working on developing an AML policy.
        Data is kept for 5 years per industry standards.
        """,
        "ground_truth": {
            "paid_up_capital": 2000000,
            "business_categories": ["P2P Lending (Category 2)"],
            "data_storage_location": ["Singapore"],
            "has_compliance_officer": False,
            "has_board_approved_aml": False,
            "has_signed_aoa": False,
            "has_10_year_retention": False,
            "has_p2p_monitoring_system": False
        }
    },
    {
        "name": "QatarPay Solutions - Partially Compliant",
        "text": """
        QatarPay Solutions LLC
        Paid-Up Capital: Initial capital of QAR 8,500,000
        Services: Payment Service Provider for digital payment systems and electronic money issuance
        Data: Stored in Qatar and Dubai for redundancy
        We have a dedicated Compliance Officer reporting to the board
        AML policy approved by board in June 2025
        Articles of Association filed
        Transaction records retained for 10 years
        Monitoring system planned for deployment in Q4 2025
        """,
        "ground_truth": {
            "paid_up_capital": 8500000,
            "business_categories": ["Payment Service Provider (Category 1)"],
            "data_storage_location": ["Qatar", "Dubai"],
            "has_compliance_officer": True,
            "has_board_approved_aml": True,
            "has_signed_aoa": True,
            "has_10_year_retention": True,
            "has_p2p_monitoring_system": False
        }
    }
]


# ============================================================================
# EVALUATION FUNCTIONS
# ============================================================================

def evaluate_field(predicted, ground_truth, field_name: str) -> Dict[str, Any]:
    """
    Evaluate a single field extraction.
    Returns dict with correctness, predicted, expected, and error info.
    """
    result = {
        "field": field_name,
        "predicted": predicted,
        "expected": ground_truth,
        "correct": False,
        "error_type": None
    }
    
    if field_name == "paid_up_capital":
        # Exact match for numbers
        result["correct"] = (predicted == ground_truth)
        if not result["correct"]:
            result["error_type"] = "value_mismatch"
    
    elif field_name == "business_categories":
        # Check if all ground truth categories are found
        predicted_set = set(predicted) if predicted else set()
        expected_set = set(ground_truth) if ground_truth else set()
        
        # Calculate precision and recall for categories
        if expected_set:
            matches = predicted_set & expected_set
            result["precision"] = len(matches) / len(predicted_set) if predicted_set else 0
            result["recall"] = len(matches) / len(expected_set) if expected_set else 0
            result["correct"] = (predicted_set == expected_set)
            
            if predicted_set != expected_set:
                missing = expected_set - predicted_set
                extra = predicted_set - expected_set
                if missing:
                    result["error_type"] = f"missing: {missing}"
                if extra:
                    result["error_type"] = f"{result.get('error_type', '')} extra: {extra}".strip()
        else:
            result["correct"] = len(predicted_set) == 0
    
    elif field_name == "data_storage_location":
        # Check if locations are detected (partial match acceptable)
        predicted_set = set(predicted) if predicted else set()
        expected_set = set(ground_truth) if ground_truth else set()
        
        # Normalize "State of Qatar" to "Qatar"
        predicted_normalized = set()
        for loc in predicted_set:
            if "Qatar" in loc:
                predicted_normalized.add("Qatar")
            else:
                predicted_normalized.add(loc)
        
        expected_normalized = set()
        for loc in expected_set:
            if "Qatar" in loc:
                expected_normalized.add("Qatar")
            else:
                expected_normalized.add(loc)
        
        matches = predicted_normalized & expected_normalized
        if expected_normalized:
            result["recall"] = len(matches) / len(expected_normalized)
            result["precision"] = len(matches) / len(predicted_normalized) if predicted_normalized else 0
            # Consider correct if recall >= 0.8 (found most locations)
            result["correct"] = result["recall"] >= 0.8
        else:
            result["correct"] = len(predicted_normalized) == 0
    
    else:
        # Boolean fields
        result["correct"] = (predicted == ground_truth)
        if not result["correct"]:
            result["error_type"] = f"expected {ground_truth}, got {predicted}"
    
    return result


def calculate_metrics(results: List[Dict]) -> Dict[str, float]:
    """
    Calculate overall precision, recall, F1, and accuracy.
    """
    total_fields = len(results)
    correct_fields = sum(1 for r in results if r["correct"])
    
    # Overall accuracy
    accuracy = correct_fields / total_fields if total_fields > 0 else 0
    
    # For fields with precision/recall (categories, locations)
    precisions = [r["precision"] for r in results if "precision" in r]
    recalls = [r["recall"] for r in results if "recall" in r]
    
    avg_precision = sum(precisions) / len(precisions) if precisions else accuracy
    avg_recall = sum(recalls) / len(recalls) if recalls else accuracy
    
    # F1 score
    f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
    
    return {
        "accuracy": accuracy,
        "precision": avg_precision,
        "recall": avg_recall,
        "f1_score": f1,
        "correct_fields": correct_fields,
        "total_fields": total_fields
    }


# ============================================================================
# MAIN EVALUATION
# ============================================================================

def run_accuracy_test():
    """
    Run the full accuracy test suite.
    """
    print("=" * 80)
    print("AI EXTRACTION MODULE - ACCURACY MEASUREMENT")
    print("=" * 80)
    print()
    
    all_results = []
    test_summaries = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'─' * 80}")
        print(f"TEST CASE {i}: {test_case['name']}")
        print(f"{'─' * 80}")
        
        # Run extraction
        predicted = run_extraction(test_case["text"])
        ground_truth = test_case["ground_truth"]
        
        # Evaluate each field
        case_results = []
        for field in ground_truth.keys():
            result = evaluate_field(
                predicted.get(field),
                ground_truth[field],
                field
            )
            case_results.append(result)
            all_results.append(result)
            
            # Print field result
            status = "✓ PASS" if result["correct"] else "✗ FAIL"
            print(f"  {status} | {field:30s} | Predicted: {str(predicted.get(field))[:40]}")
            if not result["correct"]:
                print(f"       {'':34s} | Expected:  {str(ground_truth[field])[:40]}")
                if result.get("error_type"):
                    print(f"       {'':34s} | Error: {result['error_type']}")
        
        # Case metrics
        case_metrics = calculate_metrics(case_results)
        test_summaries.append({
            "name": test_case["name"],
            "metrics": case_metrics
        })
        
        print(f"\n  Case Accuracy: {case_metrics['accuracy']:.1%} ({case_metrics['correct_fields']}/{case_metrics['total_fields']} fields correct)")
    
    # ========================================================================
    # OVERALL METRICS
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)
    
    overall_metrics = calculate_metrics(all_results)
    
    print(f"\n📊 AGGREGATE METRICS:")
    print(f"  Overall Accuracy:  {overall_metrics['accuracy']:.2%}")
    print(f"  Precision:         {overall_metrics['precision']:.2%}")
    print(f"  Recall:            {overall_metrics['recall']:.2%}")
    print(f"  F1-Score:          {overall_metrics['f1_score']:.2%}")
    print(f"  Correct Fields:    {overall_metrics['correct_fields']}/{overall_metrics['total_fields']}")
    
    # Per-field breakdown
    print(f"\n📋 PER-FIELD BREAKDOWN:")
    field_stats = {}
    for result in all_results:
        field = result["field"]
        if field not in field_stats:
            field_stats[field] = {"correct": 0, "total": 0}
        field_stats[field]["total"] += 1
        if result["correct"]:
            field_stats[field]["correct"] += 1
    
    for field, stats in sorted(field_stats.items()):
        acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {field:30s}: {acc:.1%} ({stats['correct']}/{stats['total']})")
    
    # Per-test-case summary
    print(f"\n📝 PER-TEST-CASE SUMMARY:")
    for summary in test_summaries:
        print(f"  {summary['name']:40s}: {summary['metrics']['accuracy']:.1%}")
    
    # Export results
    export_data = {
        "overall_metrics": {
            "accuracy": f"{overall_metrics['accuracy']:.2%}",
            "precision": f"{overall_metrics['precision']:.2%}",
            "recall": f"{overall_metrics['recall']:.2%}",
            "f1_score": f"{overall_metrics['f1_score']:.2%}",
            "correct_fields": overall_metrics['correct_fields'],
            "total_fields": overall_metrics['total_fields']
        },
        "per_field_accuracy": {
            field: f"{stats['correct'] / stats['total']:.2%}"
            for field, stats in field_stats.items()
        },
        "test_cases": [
            {
                "name": s["name"],
                "accuracy": f"{s['metrics']['accuracy']:.2%}",
                "correct": s['metrics']['correct_fields'],
                "total": s['metrics']['total_fields']
            }
            for s in test_summaries
        ]
    }
    
    # Save to JSON
    output_file = os.path.join(os.path.dirname(__file__), "..", "accuracy_results.json")
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✅ Results saved to: accuracy_results.json")
    
    print("\n" + "=" * 80)
    print(f"🎯 FINAL ACCURACY RATING: {overall_metrics['accuracy']:.1%}")
    print("=" * 80)
    print()
    
    return overall_metrics


if __name__ == "__main__":
    metrics = run_accuracy_test()
