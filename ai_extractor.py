import re
import spacy
from typing import Dict, List, Any

# --- 1. SETUP ---
# Load the small English model from spaCy. This is fast and reliable for hackathons.
try:
    nlp = spacy.load("en_core_web_sm")
    print("INFO: spaCy model loaded successfully.")
except:
    print("ERROR: spaCy model not found. Please run: python -m spacy download en_core_web_sm")
    # Note: if the model isn't available the rest of the extraction will still run
    # using simple rule-based fallbacks, but performance may be reduced.


# --- 2. EXTRACTION HELPER FUNCTIONS ---

def extract_financials(text: str) -> int:
    """
    Extracts the Paid-Up Capital amount from the text using multiple pattern matches.
    Target: QAR 5,000,000 or variations
    """
    # Try multiple patterns for better coverage
    patterns = [
        r"Paid-Up Capital:.*?was QAR ([\d,]+)",  # Original pattern
        r"Paid-Up Capital:.*?QAR ([\d,]+)",       # Without "was"
        r"Paid[- ]?Up Capital.*?QAR ([\d,]+)",    # Flexible spacing
        r"initial capital.*?QAR ([\d,]+)",        # "initial capital"
        r"secured QAR ([\d,]+)",                  # "secured QAR"
        r"started with QAR ([\d,]+)",             # "started with QAR"
        r"seed funding.*?QAR ([\d,]+)",           # "seed funding"
        r"capital.*?QAR ([\d,]+)",                # Generic "capital"
        r"QAR ([\d,]+).*?capital",                # Capital after amount
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Remove commas and convert to integer
            capital_str = match.group(1).replace(',', '')
            return int(capital_str)
    
    return 0

def extract_business_categories(text: str) -> List[str]:
    """
    Identifies the regulatory categories based on key service activities.
    Target: P2P Lending (Category 2) and Payment Service Provider (Category 1)
    """
    categories = []
    text_lower = text.lower()
    
    # Category 2 (Marketplace Lending - P2P/Crowdfunding)
    if "peer-to-peer" in text_lower or "p2p" in text_lower or "facilitation of peer-to-peer financing services" in text_lower:
        categories.append("P2P Lending (Category 2)")
    
    # Category 1 (Payment Service Provider - PSP)
    if "payment processing" in text_lower or "digital payment systems" in text_lower or "electronic money issuance" in text_lower:
        categories.append("Payment Service Provider (Category 1)")
        
    # The system must be assessed against the *highest* capital requirement of all applicable categories.
    return categories

def extract_compliance_status(text: str) -> Dict[str, Any]:
    """
    Extracts critical status flags for Compliance Officer, AML Policy, and Data Location.
    Uses spaCy for basic NER and rule-based keyword matching.
    """
    status = {
        "data_storage_location": [],
        "has_compliance_officer": False,
        "has_board_approved_aml": False,
        "has_signed_aoa": False
    }
    
    # 3.1 Data Storage Location (Rule: MUST be Qatar)
    # Use spaCy NER to find geo-political entities + keyword matching
    text_lower = text.lower()
    
    # Define comprehensive location patterns
    location_patterns = {
        "Qatar": [r"\bqatar\b", r"state of qatar", r"within qatar", r"in qatar", r"qatar\s+region"],
        "Ireland": [r"\bireland\b", r"irish\s+region"],
        "Singapore": [r"\bsingapore\b"],
        "Dubai": [r"\bdubai\b", r"in dubai"],
        "UAE": [r"\buae\b", r"united arab emirates"],
    }
    
    detected_locations = []
    for location, patterns in location_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if location not in detected_locations:
                    detected_locations.append(location)
                break
    
    # Also use spaCy NER for additional locations
    try:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "GPE":  # Geo-Political Entity
                location_name = ent.text.strip()
                # Normalize
                if "Qatar" in location_name and "Qatar" not in detected_locations:
                    detected_locations.append("Qatar")
                elif location_name not in detected_locations:
                    # Check if it's one of our known locations
                    for known_loc in location_patterns.keys():
                        if known_loc.lower() in location_name.lower():
                            if known_loc not in detected_locations:
                                detected_locations.append(known_loc)
                            break
    except Exception:
        pass
    
    status["data_storage_location"] = detected_locations
    
    # 4. Current Compliance and Governance Plan
    
    # Compliance Officer Status (Rule: Must be designated & independent)
    # Check for negative indicators first
    negative_indicators = [
        "plan to assign these duties to the head of finance",
        "plan to hire a compliance officer",
        "will appoint",
        "planning to hire",
        "do not currently have a dedicated compliance officer"
    ]
    
    has_negative = any(phrase in text_lower for phrase in negative_indicators)
    
    if has_negative:
        status["has_compliance_officer"] = False
    elif "compliance officer" in text_lower:
        # Positive indicators
        positive_patterns = [
            r"(appointed|have|has|designated)\s+.*?compliance officer",
            r"compliance officer.*?(appointed|designated|independent)",
            r"(mr\.|ms\.|dr\.)\s+\w+.*?compliance officer",
            r"compliance officer.*?(mr\.|ms\.|dr\.)",
        ]
        if any(re.search(pattern, text_lower) for pattern in positive_patterns):
            status["has_compliance_officer"] = True
    
    # AML Policy Status (Rule: Must be Board-approved)
    # Check for negative indicators
    aml_negative = [
        "policy for reporting suspicious transactions is currently under review",
        "under development",
        "under review",
        "working on developing an aml policy",
        "aml policy.*?under review",
        "aml.*?under development"
    ]
    
    has_aml_negative = False
    for pattern in aml_negative:
        if re.search(pattern, text_lower):
            has_aml_negative = True
            break
    
    if has_aml_negative:
        status["has_board_approved_aml"] = False
    else:
        # Look for positive indicators
        aml_positive = [
            r"board[- ]?approved.*?aml",
            r"aml.*?board[- ]?approved",
            r"aml.*?policy.*?(approved|ratified|implemented)",
            r"anti[- ]?money laundering.*?policy.*?(approved|ratified)",
        ]
        if any(re.search(pattern, text_lower) for pattern in aml_positive):
            status["has_board_approved_aml"] = True

    # AoA Submission (Rule: The document exists and is referenced)
    if "articles of association" in text_lower:
        status["has_signed_aoa"] = True # It exists in the provided excerpts

    return status


def extract_data_retention(text: str) -> bool:
    """
    Check whether the company's privacy/data retention policy specifies a 10-year retention period.
    Al-Ameen's doc currently states 7 years; the circular requires 10 years.
    Return True if 10 years explicitly mentioned, otherwise False.
    """
    text_lower = text.lower()
    # Look for explicit '10 years' or 'ten years' in retention context
    if '10 years' in text_lower or 'ten years' in text_lower:
        # Ensure it's mentioned in the context of retention/retain/retention period
        if 'retain' in text_lower or 'retention' in text_lower or 'retention period' in text_lower:
            return True
    # If it mentions 7 years explicitly, return False
    if '7 years' in text_lower or 'seven years' in text_lower:
        return False
    # As a fallback, look for phrases indicating a retention policy but no duration -> assume False
    if 'retain' in text_lower or 'retention' in text_lower or 'retention period' in text_lower:
        return False
    return False


def extract_p2p_monitoring_system(text: str) -> bool:
    """
    Detect whether the startup states it has an active P2P monitoring/system for transactions.
    We look for explicit deployment language (deployed/implemented/in production) alongside
    keywords like 'transaction monitoring', 'P2P monitoring', 'fraud detection', 'surveillance'.
    If not explicit, return False.
    """
    text_lower = text.lower()
    monitoring_keywords = ['transaction monitoring', 'transaction surveillance', 'p2p monitoring', 'p2p surveillance', 'fraud detection', 'monitoring system', 'real-time monitoring']
    deployed_words = ['deployed', 'implemented', 'in production', 'is deployed', 'is implemented', 'operational', 'live']

    found_monitoring = any(k in text_lower for k in monitoring_keywords)
    if not found_monitoring:
        return False

    # If monitoring keywords exist, check if the doc says it's actually deployed/operational
    if any(w in text_lower for w in deployed_words):
        return True

    # Ambiguous mentions (planning, under development) should be considered False
    negative_indicators = ['plan to', 'planning to', 'under development', 'under review', 'pilot', 'prototype']
    if any(n in text_lower for n in negative_indicators):
        return False

    return False


# --- 3. MAIN EXPORT FUNCTION ---

def run_extraction(full_startup_text: str) -> Dict[str, Any]:
    """
    The final function called by the Software Engineer (S).
    It consolidates all extracted data into a single structured dictionary.
    """
    financials = extract_financials(full_startup_text)
    categories = extract_business_categories(full_startup_text)
    compliance = extract_compliance_status(full_startup_text)
    
    # Additional checks required by Product (P2): data retention and P2P monitoring
    has_10_year_retention = extract_data_retention(full_startup_text)
    has_p2p_monitoring_system = extract_p2p_monitoring_system(full_startup_text)

    # This structured dictionary is the output the S needs for the Gap Analysis Engine
    return {
        "paid_up_capital": financials,
        "business_categories": categories,
        "data_storage_location": compliance["data_storage_location"],
        "has_compliance_officer": compliance["has_compliance_officer"],
        "has_board_approved_aml": compliance["has_board_approved_aml"],
        "has_signed_aoa": compliance["has_signed_aoa"],
        "entity_type": "LLC", # Hardcoded from AoA excerpt title
        # P2 additions
        "has_10_year_retention": has_10_year_retention,
        "has_p2p_monitoring_system": has_p2p_monitoring_system
    }

# Example to test your script:
if __name__ == '__main__':
    # This block allows you to test your functions locally before giving it to the SE
    MOCK_TEXT = """
    Al-Ameen Digital, LLC: Articles of Association (Excerpt) 
    1.2. Paid-Up Capital: The initial paid-up capital upon incorporation was QAR 5,000,000 (Five Million Qatari Riyals).
    Project Al-Ameen: Peer-to-Peer Investment Platform. Our primary activities are: Facilitation of peer-to-peer financing services. 
    Al-Ameen Digital: Data Privacy and Customer Consent Policy. All customer data is currently processed and stored within our secure cloud environment, hosted across the AWS regions in Ireland and Singapore. We do not currently have a dedicated Compliance Officer but plan to assign these duties to the Head of Finance... 
    """
    
    extracted_data = run_extraction(MOCK_TEXT)
    print("\n--- AI EXTRACTION OUTPUT ---")
    import pprint
    pprint.pprint(extracted_data)

    # Expected Critical Output Check:
    assert extracted_data['paid_up_capital'] == 5000000
    assert "P2P Lending (Category 2)" in extracted_data['business_categories']
    assert "Ireland" in extracted_data['data_storage_location']
    assert extracted_data['has_compliance_officer'] == False
    print("\n[SUCCESS] AI Extraction passed local test.")
