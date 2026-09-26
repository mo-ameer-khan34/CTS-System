import os
import json
from google import genai
from google.genai import types
from PIL import Image

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

VALIDATION_SYSTEM_INSTRUCTION = """
You are an expert South African Police Service (SAPS) affidavit compliance auditor.
Your job is to inspect an affidavit statement (text and/or image) against the following strict legal, structural, and layout standards:

1. Document Title & Header Validation:
   - Exact Title Match: Presence of "SWORN STATEMENT" or "AFFIDAVIT" at the top.
   - Deponent Identity: Full Names & Surname, valid 13-digit SA ID or passport regex match, residential address block populated, contact phone number present.
   - Oath Declaration Line: Explicit phrase "states under oath" or "solemnly declares in English" prior to the statement body.

2. Statement Body & Structural Logic:
   - Paragraph Sequence: Must use sequential numbered format (1., 2., 3., etc.). Flag unnumbered narrative blocks as an error.
   - Capacity Assertion (Paragraph 1): Standard authority phrases present (e.g., "adult male/female", "facts fall within my personal knowledge").
   - Essential Crime Data: Date and time of incident, physical incident address/location, monetary value (R/ZAR) if financial crime/fraud/theft.
   - Annexure Cross-Referencing: If any annexure (e.g., "Annexure A1") is mentioned in text, verify explicit definition.

3. Statutory Jurat / Oath Block (Mandatory Justices of the Peace Act lines):
   - Verbatim check for all 3 lines:
     1. "I know and understand the contents of this declaration."
     2. "I have no objection to taking the prescribed oath."
     3. "I consider the prescribed oath to be binding on my conscience."
   - Rejection Condition: If ANY of these 3 lines are missing, altered, or truncated, mark compliance as FALSE.

4. Signature & Stamp Visual/Bounding Box Verification:
   - Deponent signature mark directly below statutory oath block.
   - Commissioner attestation clause ("I certify that the deponent has acknowledged...").
   - Commissioner signature, rank/force number, full name, business address, and date.
   - SAPS / Commissioner official ink stamp boundary showing station name, date, and designation.

Return ONLY a valid JSON object matching this schema:
{
  "is_compliant": bool,
  "checklist_results": {
    "header_and_deponent": {"passed": bool, "details": "string"},
    "statement_body_structure": {"passed": bool, "details": "string"},
    "statutory_jurat": {"passed": bool, "details": "string"},
    "signatures_and_stamp": {"passed": bool, "details": "string"}
  },
  "flags": ["list of string errors or omissions"],
  "summary": "string summary of audit"
}
"""

def validate_saps_docket_affidavit(text_content: str, image_path: str = None) -> dict:
    client = get_gemini_client()
    
    # Calculate word count
    words = text_content.strip().split()
    word_count = len(words)
    word_count_accepted = word_count >= 50  # adjust minimal threshold as needed
    
    contents = []
    
    # Attach visual scan if image is present
    if image_path and os.path.exists(image_path):
        img = Image.open(image_path)
        contents.append(img)
        
    prompt = f"""
    Affidavit Text Content:
    \"\"\"{text_content}\"\"\"
    
    Total Word Count: {word_count}
    
    Perform the complete compliance check and return the JSON evaluation.
    """
    contents.append(prompt)
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=VALIDATION_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.1
        )
    )
    
    try:
        result_json = json.loads(response.text)
    except Exception:
        result_json = {
            "is_compliant": False,
            "flags": ["Failed to parse AI response into JSON format."],
            "summary": response.text
        }
        
    result_json["word_count"] = word_count
    result_json["word_count_accepted"] = word_count_accepted
    return result_json