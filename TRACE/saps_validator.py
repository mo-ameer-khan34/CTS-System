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
Your job is to inspect an uploaded SAPS affidavit form (standard form template) against specific structural, legal, and content completion rules.

The document submitted uses the official standard SAPS Affidavit layout. Evaluate the statement against the following criteria:

1. Document Header & Deponent Identity:
   - Presence of the document titles: "AFFIDAVIT", "SUID-AFRIKAANSE POLISIEDIENS", and "SOUTH AFRICAN POLICE SERVICE".
   - Deponent / Victim Identity fields MUST be populated (not left blank or merely dotted lines):
     * NAME and SURNAME
     * ID NO (Valid 13-digit SA ID or passport format)
     * AGE
     * HOME ADDRESS and POSTAL CODE
     * Contact Number (CELL, TEL [HOME], or WORK)
   - Oath Declaration Line: Presence of "STATE UNDER OATH:" or "STATES UNDER OATH:" preceding the statement body.

2. Statement Body & Details:
   - The body area below "STATE UNDER OATH:" must contain a coherent narrative statement describing the incident/matter.
   - Essential details present in the text: Date and/or Time, Incident location/address, and property/monetary values if financial crime or theft.
   - Sequential paragraph numbering (1., 2., etc.) is preferred; flag if completely disjointed or blank.

3. Statutory Jurat / Oath Block:
   - Verify the presence of the 3 statutory lines under the Justices of the Peace Act (allowing the template variation "ON TAKING"):
     1. "I KNOW AND UNDERSTAND THE CONTENTS OF THIS DECLARATION."
     2. "I HAVE NO OBJECTION TO/ON TAKING THE PRESCRIBED OATH."
     3. "I CONSIDER THE PRESCRIBED OATH TO BE BINDING ON MY CONSCIENCE."
   - If any of these 3 declaration lines are completely missing or contradicted, mark compliance as FALSE.

4. Attestation & Commissioner Block:
   - Presence of the attestation block: "I CERTIFY THAT ABOVE STATEMENT WAS TAKEN BY ME..."
   - Indication of deponent signature ("DEPONENTS SIGNATURE" area) and Commissioner ("COMMISSIONER OF OATH").

5. TESTING EXEMPTION (STAMP RULE):
   - DO NOT require or check for a physical ink station stamp, date stamp, or stamp boundary.
   - DO NOT fail compliance due to an absent or pre-printed stamp. Ignore the stamp field completely for system testing.

Accept the document as COMPLIANT if the template fields are filled with valid deponent/victim information, a substantive statement is provided, and the statutory jurat is intact.

Return ONLY a valid JSON object matching this schema:
{
  "is_compliant": bool,
  "checklist_results": {
    "header_and_deponent": {"passed": bool, "details": "string"},
    "statement_body_structure": {"passed": bool, "details": "string"},
    "statutory_jurat": {"passed": bool, "details": "string"},
    "attestation_and_signatures": {"passed": bool, "details": "string"}
  },
  "flags": ["list of string errors or missing fields"],
  "summary": "string summary of audit"
}
"""

def validate_saps_docket_affidavit(text_content: str, image_path: str = None) -> dict:
    client = get_gemini_client()
    
    words = text_content.strip().split()
    word_count = len(words)
    word_count_accepted = word_count >= 50
    
    contents = []
    
    if image_path and os.path.exists(image_path):
        img = Image.open(image_path)
        contents.append(img)
        
    prompt = f"""
    Affidavit Text Content:
    \"\"\"{text_content}\"\"\"
    
    Total Word Count: {word_count}
    
    Verify that the victim/deponent fields and statement body are properly populated and assess SAPS compliance.
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