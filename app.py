from flask import Flask, jsonify, request
from flask import send_from_directory
import json

app = Flask(__name__)

# --- GLOBAL DATA STRUCTURES (Loaded from Mock JSON) ---
RESOURCE_MAPPING = {}

# --- FINTECH SPECIALIST RULE DEFINITIONS (Hardcoded) ---
# Define the regulatory check list and their weights (from F's Task 0.4)
# Weights must sum to 1.0 (or 100)
REGULATORY_CHECKS = {
    "Capital Shortfall": {"weight": 0.30, "resource_topic": "Licensing Strategy"}, # Critical
    "Data Residency Failure": {"weight": 0.25, "resource_topic": "Data Residency"}, # Critical
    "Compliance Officer Missing": {"weight": 0.15, "resource_topic": "Corporate Structure"}, # High
    "AML/CFT Policy Gap": {"weight": 0.10, "resource_topic": "AML Policy Drafting"}, # High
    "AoA Submission": {"weight": 0.10, "resource_topic": None}, # Passed, but included for total
    "Fit & Proper Docs Missing": {"weight": 0.10, "resource_topic": None} # Medium
}

# Define the key regulatory thresholds
REGULATORY_THRESHOLDS = {
    "Minimum Capital (Cat 2)": 7500000, # QAR 7.5M
    "Required Data Location": "State of Qatar"
}

def load_resources():
    """Loads QDB programs and compliance experts from JSON."""
    global RESOURCE_MAPPING
    try:
        with open('resource_mapping_data.json', 'r') as f:
            RESOURCE_MAPPING = json.load(f)
        print("INFO: Resources loaded successfully.")
    except FileNotFoundError:
        print("ERROR: resource_mapping_data.json not found.")

# --- MOCK/SIMULATION for AI Student's (A) Task 1.1 & 1.3 ---
def mock_ai_extraction(startup_docs_text):
    """
    Simulates the AI's extraction from Al-Ameen Digital documents.
    In a real hackathon, this function would call the AI Student's NLP model.
    """
    # Based on Al-Ameen Digital Documents (mocked values)
    return {
        "entity_type": "LLC",
        "business_categories": ["P2P Lending", "Digital Payment Systems"],
        "paid_up_capital": 5000000,      # QAR 5M
        "data_storage_location": ["Ireland", "Singapore"],
        "has_compliance_officer": False, # plan to assign to Head of Finance
        "has_board_approved_aml": False, # under review by external legal counsel
        "has_signed_aoa": True,          # Articles of Association exists
    }

# --- TASK 1.2: Mapping Endpoint (Uses A's function) ---
@app.route('/api/map_startup_data', methods=['POST'])
def map_startup_data():
    # Get raw text data from frontend request (or mock it for now)
    startup_docs_text = request.json.get('documents', 'mock_text_placeholder') 
    
    # Call the AI's extraction function
    extracted_data = mock_ai_extraction(startup_docs_text)
    
    return jsonify(extracted_data), 200


# --- TASK 2.1: Gap Analysis Engine ---
def run_gap_analysis(extracted_data):
    """Compares startup data against regulatory thresholds to identify FAILs."""
    gaps = []
    
    # Check 1: Capital Shortfall (Requires QAR 7.5M for P2P)
    if extracted_data.get('paid_up_capital', 0) < REGULATORY_THRESHOLDS["Minimum Capital (Cat 2)"]:
        gaps.append("Capital Shortfall")
        
    # Check 2: Data Residency Failure
    if not any(loc == REGULATORY_THRESHOLDS["Required Data Location"] for loc in extracted_data.get('data_storage_location', [])):
        gaps.append("Data Residency Failure")
        
    # Check 3: Compliance Officer Missing (Must be designated & independent)
    if not extracted_data.get('has_compliance_officer', False): 
        gaps.append("Compliance Officer Missing")
        
    # Check 4: AML/CFT Policy Gap (Must be board-approved)
    if not extracted_data.get('has_board_approved_aml', False):
        gaps.append("AML/CFT Policy Gap")
        
    # Check 5: Fit & Proper Docs Missing (Implied failure due to no CO)
    if "Compliance Officer Missing" in gaps:
        gaps.append("Fit & Proper Docs Missing")

    # Check 6: AoA Submission (Must be signed AoA)
    # This is a PASS based on the mock data, so we don't add a gap if TRUE
    
    return gaps


# --- TASK 2.3: Actionable Feedback Loop ---
def find_recommendation(topic):
    """Finds a relevant expert or program based on a topic string.

    Returns a list of recommendation dicts drawn from RESOURCE_MAPPING.
    """
    recs = []

    # Search QDB Programs
    for program in RESOURCE_MAPPING.get('qdb_programs', []):
        # program is expected to have keys like 'program_name', 'focus_areas', 'eligibility'
        try:
            if topic in program.get('focus_areas', []):
                recs.append({
                    "type": "QDB Program",
                    "name": program.get('program_name'),
                    "contact": program.get('eligibility')
                })
        except AttributeError:
            # skip malformed entries
            continue

    # Search Compliance Experts
    for expert in RESOURCE_MAPPING.get('compliance_experts', []):
        try:
            if topic in expert.get('specialization', []):
                recs.append({
                    "type": "Compliance Expert",
                    "name": expert.get('name'),
                    "contact": expert.get('contact')
                })
        except AttributeError:
            continue

    return recs


def generate_recommendations(failed_gaps):
    """Maps all failed gaps to relevant resources."""
    final_recs = []
    for gap in failed_gaps:
        if gap not in REGULATORY_CHECKS:
            continue
        topic = REGULATORY_CHECKS[gap].get("resource_topic")
        if topic:
            resources = find_recommendation(topic)
            final_recs.append({
                "gap": gap,
                "resources": resources
            })
    return final_recs


# --- TASK 2.2: Weighted Scorecard Calculation ---
@app.route('/api/scorecard', methods=['POST'])
def calculate_scorecard():
    # Step 1: Get Extracted Data
    startup_docs_text = request.json.get('documents', 'mock_text_placeholder') 
    extracted_data = mock_ai_extraction(startup_docs_text)
    
    # Step 2: Run Gap Analysis
    failed_gaps = run_gap_analysis(extracted_data)
    
    # Step 3: Calculate Score
    total_possible_score = sum(check["weight"] for check in REGULATORY_CHECKS.values()) # Should be 1.0
    # Only sum weights for known checks to avoid KeyError
    score_lost = sum(REGULATORY_CHECKS[gap]["weight"] for gap in failed_gaps if gap in REGULATORY_CHECKS)
    final_score = (total_possible_score - score_lost) * 100
    
    # Step 4: Prepare the detailed scorecard
    score_breakdown = []
    for check_name, details in REGULATORY_CHECKS.items():
        is_fail = check_name in failed_gaps
        score_breakdown.append({
            "check": check_name,
            "status": "FAIL" if is_fail else "PASS",
            "weight": details["weight"] * 100,
            "score_contribution": 0 if is_fail else details["weight"] * 100
        })
        
    # Step 5: Implement Actionable Feedback (Task 2.3)
    recommendations = generate_recommendations(failed_gaps)
        
    return jsonify({
        "extracted_data": extracted_data,
        "readiness_score": round(final_score),
        "failed_gaps": failed_gaps,
        "score_breakdown": score_breakdown,
        "recommendations": recommendations
    }), 200

# --- TASK 0.1: Basic Status Endpoint ---
@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "Backend running", "version": "MVP 1.0"}), 200
    

@app.route('/')
def root():
    """Serve the static frontend index page."""
    # Flask will serve files from the ./static folder by default
    return app.send_static_file('index.html')


if __name__ == '__main__':
    load_resources()
    app.run(debug=True, port=5000)