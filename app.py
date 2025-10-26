from flask import Flask, jsonify, request
from flask import send_from_directory, send_file
import json
import io
import sqlite3
from datetime import datetime

# AI extraction logic lives in ai_extractor.py (implemented by the AI Student)
from ai_extractor import run_extraction
from ingest_utils import extract_text_from_files

app = Flask(__name__)

# --- GLOBAL DATA STRUCTURES (Loaded from Mock JSON) ---
RESOURCE_MAPPING = {}

# --- FINTECH SPECIALIST RULE DEFINITIONS (Loaded from external config) ---
# These are populated at startup from `rules_config.json` by load_rules().
REGULATORY_CHECKS = {}
SECTION_WEIGHTS = {}
REGULATORY_THRESHOLDS = {}

# --- TRANSPARENCY: Original regulation article texts ---
REGULATION_TEXTS = {}

# --- PERSISTENCE (SQLite) ---
DB_PATH = 'assessments.db'

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                input_len INTEGER,
                readiness_score INTEGER,
                failed_gaps TEXT,
                extracted_data TEXT,
                score_breakdown TEXT
            )
            """
        )
        conn.commit()
    finally:
        try: conn.close()
        except Exception: pass

def save_assessment(result: dict):
    """Persist an assessment and return its inserted ID (or None on error)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        failed = json.dumps(result.get('failed_gaps', []))
        extracted = json.dumps(result.get('extracted_data', {}))
        breakdown = json.dumps(result.get('score_breakdown', []))
        score = int(result.get('readiness_score', 0))
        input_len = len(json.dumps(result))
        cur.execute(
            "INSERT INTO assessments (created_at, input_len, readiness_score, failed_gaps, extracted_data, score_breakdown) VALUES (?,?,?,?,?,?)",
            (datetime.utcnow().isoformat(), input_len, score, failed, extracted, breakdown)
        )
        conn.commit()
        try:
            return cur.lastrowid
        except Exception:
            return None
    except Exception:
        # Swallow persistence errors for MVP
        return None
    finally:
        try: conn.close()
        except Exception: pass


def load_regulation_texts():
    """Load original regulation article texts used for transparency view."""
    global REGULATION_TEXTS
    try:
        with open('regulation_texts.json', 'r') as f:
            REGULATION_TEXTS = json.load(f)
        print("INFO: Regulation texts loaded successfully.")
    except FileNotFoundError:
        print("WARN: regulation_texts.json not found. Transparency view will be empty.")

# Load regulation texts at import time
load_regulation_texts()


def load_rules():
    """Load regulatory rules (checks and thresholds) from rules_config.json.

    Falls back to empty dicts if the file is missing; prints an INFO/WARN message.
    """
    global REGULATORY_CHECKS, SECTION_WEIGHTS, REGULATORY_THRESHOLDS
    try:
        with open('rules_config.json', 'r') as f:
            rules = json.load(f)
        REGULATORY_CHECKS = rules.get('REGULATORY_CHECKS', {})
        SECTION_WEIGHTS = rules.get('SECTION_WEIGHTS', {})
        REGULATORY_THRESHOLDS = rules.get('REGULATORY_THRESHOLDS', {})
        print("INFO: Rules loaded successfully from rules_config.json.")
    except FileNotFoundError:
        print("WARN: rules_config.json not found. Using empty defaults for rules.")


# Load rules at import time so endpoints can use them immediately
load_rules()
init_db()


# --- B: Define Full Startup Text (Simulates consolidated Al-Ameen documents) ---
FULL_STARTUP_TEXT = """
Al-Ameen Digital, LLC: Articles of Association (Excerpt) ... 
1.2. Paid-Up Capital: The initial paid-up capital upon incorporation was QAR 5,000,000 (Five Million Qatari Riyals).
...
Project Al-Ameen: Peer-to-Peer Investment Platform ... Our primary activities are: ... Facilitation of peer-to-peer financing services. ...
...
Al-Ameen Digital: Data Privacy and Customer Consent Policy ... All customer data is currently processed and stored within our secure cloud environment, hosted across the AWS regions in Ireland and Singapore. ... We do not currently have a dedicated Compliance Officer but plan to assign these duties to the Head of Finance...
"""

def load_resources():
    """Loads compliance experts and topic resources from JSON."""
    global RESOURCE_MAPPING
    try:
        with open('resource_mapping_data.json', 'r') as f:
            RESOURCE_MAPPING = json.load(f)
        print("INFO: Resources loaded successfully.")
    except FileNotFoundError:
        print("ERROR: resource_mapping_data.json not found.")

# AI extraction (implemented in ai_extractor.py)

# --- TASK 1.2: Mapping Endpoint (Uses A's function) ---
@app.route('/api/map_startup_data', methods=['POST'])
def map_startup_data():
    # Get raw text data from frontend request (or mock it for now)
    startup_docs_text = request.json.get('documents', 'mock_text_placeholder') 
    
    # Call the AI's extraction function (real implementation lives in ai_extractor.run_extraction)
    extracted_data = run_extraction(startup_docs_text)
    
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
    
    # New P2 checks (Product P2 additions)
    # Data Retention: regulator requires 10 years; Al-Ameen's doc says 7 years -> flag if not 10
    if not extracted_data.get('has_10_year_retention', False):
        gaps.append('Data Retention Shortfall')

    # P2P Monitoring System: must be deployed/operational for marketplaces
    if not extracted_data.get('has_p2p_monitoring_system', False):
        gaps.append('P2P Monitoring Gap')

    return gaps


# --- TASK 2.3: Actionable Feedback Loop ---
def find_recommendation(topic):
    """Finds a relevant expert based on a topic string.

    Returns a list of recommendation dicts drawn from RESOURCE_MAPPING.
    """
    recs = []

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
    # Ensure RESOURCE_MAPPING is loaded (useful when functions are invoked via import, not via running the server)
    try:
        if not RESOURCE_MAPPING:
            load_resources()
    except Exception:
        pass
    final_recs = []
    for gap in failed_gaps:
        if gap not in REGULATORY_CHECKS:
            # If we don't have a mapping for a new gap, still include it with empty resources
            final_recs.append({"gap": gap, "resources": []})
            continue
        topic = REGULATORY_CHECKS[gap].get("resource_topic")
        resources = []
        # First, check for direct topic_resources loaded in RESOURCE_MAPPING (added for new gaps)
        try:
            direct = RESOURCE_MAPPING.get('topic_resources', {}).get(topic, [])
            if direct:
                resources.extend(direct)
        except Exception:
            pass

        # Also attempt to find matching programs/experts using the older find_recommendation logic
        if topic:
            resources_from_lookup = find_recommendation(topic)
            if resources_from_lookup:
                resources.extend(resources_from_lookup)

        final_recs.append({
            "gap": gap,
            "resources": resources
        })
    return final_recs


# --- TASK 2.2: Weighted Scorecard Calculation ---
@app.route('/api/scorecard', methods=['POST'])
def calculate_scorecard():
    # Step 1: Get Extracted Data
    # Prefer request-provided documents (pasted text from demo) and fall back to FULL_STARTUP_TEXT
    startup_docs_text = None
    if request.is_json:
        startup_docs_text = request.json.get('documents')

    if startup_docs_text and isinstance(startup_docs_text, str) and startup_docs_text.strip():
        extracted_data = run_extraction(startup_docs_text)
    else:
        # For demo reliability, use the consolidated startup text when none provided
        extracted_data = run_extraction(FULL_STARTUP_TEXT)
    
    # Step 2: Run Gap Analysis
    failed_gaps = run_gap_analysis(extracted_data)
    
    # Step 3: Calculate Score using SECTION_WEIGHTS and per-section deduction
    # SECTION_WEIGHTS holds absolute points (e.g., 30,25,15,15,15) summing to 100
    total_possible_score = sum(SECTION_WEIGHTS.values()) if SECTION_WEIGHTS else 100

    # Build a mapping of checks -> section so we can compute per-check deduction
    # This mapping is conservative and must align with product definitions.
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

    # Count checks per section (only for checks we know about)
    section_checks = {}
    for chk in REGULATORY_CHECKS.keys():
        sec = CHECK_TO_SECTION.get(chk)
        if not sec:
            continue
        section_checks.setdefault(sec, []).append(chk)

    # For each failed gap, deduct the per-check share from that section's points
    deductions = {sec: 0 for sec in SECTION_WEIGHTS.keys()}
    for gap in failed_gaps:
        sec = CHECK_TO_SECTION.get(gap)
        if not sec or sec not in SECTION_WEIGHTS:
            # Unknown section -> skip
            continue
        checks_in_section = section_checks.get(sec, [])
        if not checks_in_section:
            continue
        per_check_deduction = SECTION_WEIGHTS[sec] / len(checks_in_section)
        deductions[sec] += per_check_deduction

    # Compute final score
    score_lost = sum(deductions.values())
    final_score = max(0, total_possible_score - score_lost)

    # Step 4: Prepare the detailed scorecard per check (show each check's contribution)
    score_breakdown = []
    for check_name, details in REGULATORY_CHECKS.items():
        sec = CHECK_TO_SECTION.get(check_name)
        checks_in_section = section_checks.get(sec, []) if sec else []
        weight_per_check = (SECTION_WEIGHTS.get(sec, 0) / len(checks_in_section)) if checks_in_section else 0
        is_fail = check_name in failed_gaps
        score_breakdown.append({
            "check": check_name,
            "status": "FAIL" if is_fail else "PASS",
            "weight": weight_per_check,
            "score_contribution": 0 if is_fail else weight_per_check
        })
        
    # Step 5: Implement Actionable Feedback (Task 2.3)
    recommendations = generate_recommendations(failed_gaps)
        
    result = {
        "extracted_data": extracted_data,
        "readiness_score": round(final_score),
        "failed_gaps": failed_gaps,
        "score_breakdown": score_breakdown,
        "recommendations": recommendations
    }

    # Save assessment to DB (best-effort)
    try:
        aid = save_assessment(result)
        if aid:
            result["assessment_id"] = aid
    except Exception:
        pass

    return jsonify(result), 200


@app.route('/api/scorecard_upload', methods=['POST'])
def scorecard_upload():
    """Accept files (pdf/docx/txt), extract text, and run the scorecard pipeline."""
    if 'files' not in request.files:
        return jsonify({"error": "No files part in request."}), 400
    files = request.files.getlist('files')
    named_files = []
    for f in files:
        try:
            named_files.append((f.filename, f.read()))
        except Exception:
            continue
    combined_text = extract_text_from_files(named_files)
    if not combined_text.strip():
        return jsonify({"error": "Could not extract text from files."}), 400

    # Reuse existing logic by calling extraction and scoring flow
    extracted_data = run_extraction(combined_text)
    failed_gaps = run_gap_analysis(extracted_data)

    total_possible_score = sum(SECTION_WEIGHTS.values()) if SECTION_WEIGHTS else 100
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
    deductions = {sec: 0 for sec in SECTION_WEIGHTS.keys()}
    for gap in failed_gaps:
        sec = CHECK_TO_SECTION.get(gap)
        if not sec or sec not in SECTION_WEIGHTS:
            continue
        checks_in_section = section_checks.get(sec, [])
        if not checks_in_section:
            continue
        per_check_deduction = SECTION_WEIGHTS[sec] / len(checks_in_section)
        deductions[sec] += per_check_deduction
    score_lost = sum(deductions.values())
    final_score = max(0, total_possible_score - score_lost)
    score_breakdown = []
    for check_name, details in REGULATORY_CHECKS.items():
        sec = CHECK_TO_SECTION.get(check_name)
        checks_in_section = section_checks.get(sec, []) if sec else []
        weight_per_check = (SECTION_WEIGHTS.get(sec, 0) / len(checks_in_section)) if checks_in_section else 0
        is_fail = check_name in failed_gaps
        score_breakdown.append({
            "check": check_name,
            "status": "FAIL" if is_fail else "PASS",
            "weight": weight_per_check,
            "score_contribution": 0 if is_fail else weight_per_check
        })
    recommendations = generate_recommendations(failed_gaps)
    result = {
        "extracted_data": extracted_data,
        "readiness_score": round(final_score),
        "failed_gaps": failed_gaps,
        "score_breakdown": score_breakdown,
        "recommendations": recommendations
    }
    try:
        aid = save_assessment(result)
        if aid:
            result["assessment_id"] = aid
    except Exception:
        pass
    return jsonify(result), 200


def build_pdf_from_result(result: dict) -> bytes:
    """Create a simple PDF report using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        # Header bar
        c.setFillColor(colors.HexColor('#5C2D91'))
        c.rect(0, height-2.5*cm, width, 2.5*cm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(2*cm, height-1.3*cm, "QDB Regulatory Readiness Report")
        c.setFont("Helvetica", 11)
        c.drawString(2*cm, height-1.8*cm, "Generated by QIAS — MVP")

        x, y = 2*cm, height - 3.2*cm
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 11)
        c.drawString(x, y, f"Score: {result.get('readiness_score', 0)} / 100")
        y -= 0.6*cm
        failed = ", ".join(result.get('failed_gaps', [])) or "None"
        c.drawString(x, y, f"Failed Gaps: {failed}")
        y -= 0.9*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Score Breakdown")
        y -= 0.6*cm
        c.setFont("Helvetica", 10)
        alt = False
        for row in result.get('score_breakdown', [])[:30]:
            # alternating background
            if alt:
                c.setFillColor(colors.HexColor('#F5F0FF'))
                c.rect(x-0.3*cm, y-0.2*cm, width-3.4*cm, 0.7*cm, fill=1, stroke=0)
                c.setFillColor(colors.black)
            line = f"{row.get('check')}: {row.get('status')} (weight {round(row.get('weight',0))}, contrib {round(row.get('score_contribution',0))})"
            c.drawString(x, y, line[:110])
            y -= 0.55*cm
            alt = not alt
            if y < 2.5*cm:
                # footer then new page
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor('#666666'))
                c.drawString(2*cm, 1.5*cm, "Qatar Development Bank — Demo report. For advisory purposes only.")
                c.showPage()
                # redraw header bar for new page
                c.setFillColor(colors.HexColor('#5C2D91'))
                c.rect(0, height-2.5*cm, width, 2.5*cm, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 18)
                c.drawString(2*cm, height-1.3*cm, "QDB Regulatory Readiness Report")
                x, y = 2*cm, height - 3.2*cm
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 10)
        y -= 0.4*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Recommendations")
        y -= 0.6*cm
        c.setFont("Helvetica", 10)
        for rec in result.get('recommendations', [])[:20]:
            c.drawString(x, y, f"- {rec.get('gap')}")
            y -= 0.5*cm
            for r in rec.get('resources', [])[:3]:
                title = r.get('title') or r.get('name') or 'Resource'
                typ = r.get('type') or ''
                c.drawString(x+0.5*cm, y, f"• {title} ({typ})")
                y -= 0.45*cm
                if y < 2*cm:
                    c.showPage(); y = height - 2*cm; c.setFont("Helvetica", 10)
            y -= 0.2*cm
            if y < 2*cm:
                c.showPage(); y = height - 2*cm; c.setFont("Helvetica", 10)
        # Footer on last page
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor('#666666'))
        c.drawString(2*cm, 1.5*cm, "Qatar Development Bank — Contact: info@qdb.qa (placeholder)")
        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    except Exception as e:
        try:
            print(f"ERROR: Failed generating PDF: {e}")
        except Exception:
            pass
        return b""


@app.route('/api/report', methods=['POST'])
def report_pdf():
    """Generate a PDF report.

    Accepts one of the following (in priority order):
    - assessment_id: Load a previously saved assessment from DB and render it.
    - result: A full result object (extracted_data, failed_gaps, etc.) to render as-is.
    - documents: Raw text to extract and score (fallbacks to demo text if empty).
    """
    payload = request.get_json(silent=True) or {}

    # 1) If assessment_id is provided, load from DB and render directly
    aid = payload.get('assessment_id')
    if isinstance(aid, int) or (isinstance(aid, str) and aid.isdigit()):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT readiness_score, failed_gaps, extracted_data, score_breakdown FROM assessments WHERE id=?", (int(aid),))
            row = cur.fetchone()
        finally:
            try: conn.close()
            except Exception: pass
        if row:
            try:
                result = {
                    "extracted_data": json.loads(row[2] or '{}'),
                    "readiness_score": int(row[0] or 0),
                    "failed_gaps": json.loads(row[1] or '[]'),
                    "score_breakdown": json.loads(row[3] or '[]'),
                    "recommendations": generate_recommendations(json.loads(row[1] or '[]'))
                }
            except Exception:
                result = None
            if result:
                pdf_bytes = build_pdf_from_result(result)
                if not pdf_bytes:
                    return jsonify({"error": "Failed to generate PDF."}), 500
                return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name='readiness_report.pdf')

    # 2) If a full result object is provided, use it directly
    if isinstance(payload.get('result'), dict):
        result = payload['result']
        pdf_bytes = build_pdf_from_result(result)
        if not pdf_bytes:
            return jsonify({"error": "Failed to generate PDF."}), 500
        return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name='readiness_report.pdf')

    # 3) Otherwise, accept raw documents text (or fallback to demo text) and recompute
    text = payload.get('documents') or ''
    if not (isinstance(text, str) and text.strip()):
        text = FULL_STARTUP_TEXT
    extracted_data = run_extraction(text)
    failed_gaps = run_gap_analysis(extracted_data)

    # Reuse same scoring math as calculate_scorecard
    total_possible_score = sum(SECTION_WEIGHTS.values()) if SECTION_WEIGHTS else 100
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
    deductions = {sec: 0 for sec in SECTION_WEIGHTS.keys()}
    for gap in failed_gaps:
        sec = CHECK_TO_SECTION.get(gap)
        if not sec or sec not in SECTION_WEIGHTS:
            continue
        checks_in_section = section_checks.get(sec, [])
        if not checks_in_section:
            continue
        per_check_deduction = SECTION_WEIGHTS[sec] / len(checks_in_section)
        deductions[sec] += per_check_deduction
    score_lost = sum(deductions.values())
    final_score = max(0, total_possible_score - score_lost)
    score_breakdown = []
    for check_name, details in REGULATORY_CHECKS.items():
        sec = CHECK_TO_SECTION.get(check_name)
        checks_in_section = section_checks.get(sec, []) if sec else []
        weight_per_check = (SECTION_WEIGHTS.get(sec, 0) / len(checks_in_section)) if checks_in_section else 0
        is_fail = check_name in failed_gaps
        score_breakdown.append({
            "check": check_name,
            "status": "FAIL" if is_fail else "PASS",
            "weight": weight_per_check,
            "score_contribution": 0 if is_fail else weight_per_check
        })
    recommendations = generate_recommendations(failed_gaps)
    result = {
        "extracted_data": extracted_data,
        "readiness_score": round(final_score),
        "failed_gaps": failed_gaps,
        "score_breakdown": score_breakdown,
        "recommendations": recommendations
    }
    pdf_bytes = build_pdf_from_result(result)
    if not pdf_bytes:
        return jsonify({"error": "Failed to generate PDF."}), 500
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name='readiness_report.pdf')

# --- TASK 0.1: Basic Status Endpoint ---
@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "Backend running", "version": "MVP 1.0"}), 200
    

@app.route('/')
def root():
    """Serve the static frontend index page."""
    # Flask will serve files from the ./static folder by default
    return app.send_static_file('index.html')


@app.route('/api/regulation_texts', methods=['GET'])
def regulation_texts():
    """Return the original regulatory article texts for transparency views."""
    return jsonify(REGULATION_TEXTS), 200

@app.route('/api/assessments', methods=['GET'])
def list_assessments():
    """Return a list of recent assessments (id, created_at, readiness_score)."""
    items = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for row in cur.execute("SELECT id, created_at, readiness_score FROM assessments ORDER BY id DESC LIMIT 20"):
            items.append({"id": row[0], "created_at": row[1], "readiness_score": row[2]})
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass
    return jsonify(items), 200

@app.route('/api/assessments/<int:aid>', methods=['GET'])
def get_assessment(aid: int):
    item = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, created_at, readiness_score, failed_gaps, extracted_data, score_breakdown FROM assessments WHERE id=?", (aid,))
        row = cur.fetchone()
        if row:
            item = {
                "id": row[0],
                "created_at": row[1],
                "readiness_score": row[2],
                "failed_gaps": json.loads(row[3] or '[]'),
                "extracted_data": json.loads(row[4] or '{}'),
                "score_breakdown": json.loads(row[5] or '[]'),
            }
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass
    if not item:
        return jsonify({"error": "not found"}), 404
    return jsonify(item), 200

if __name__ == '__main__':
    load_resources()
    app.run(debug=True, port=5000)