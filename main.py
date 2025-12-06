from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import io
import os
import re
import json

import pdfplumber
from groq import Groq

# =========================
# GROQ (AI) SETUP
# =========================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Choose Groq model
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # fine for local demo / hackathon
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# FRONTEND: serve index.html at "/"
# =========================
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """
    When you open http://127.0.0.1:8001/ in browser,
    this will directly show your index.html page.
    """
    return FileResponse("index.html")


# =========================
# FILE TEXT EXTRACTION
# =========================
def extract_text_from_file(upload_file: UploadFile) -> str:
    """
    Extract text from uploaded file.
    - If PDF: use pdfplumber
    - Else: decode as UTF-8
    """
    filename = upload_file.filename.lower()
    content = upload_file.file.read()

    if filename.endswith(".pdf"):
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
                return "\n".join(pages_text)
        except Exception:
            try:
                return content.decode("utf-8", errors="ignore")
            except Exception:
                return ""
    else:
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return ""


# =========================
# AI-BASED CLAUSE DETECTION
# =========================
def ai_detect_risks(full_text: str, language: str):
    """
    Ask Groq LLM to:
    - read whole document text
    - find risky clauses
    - classify type + severity
    - generate simplified explanation in chosen language
    Returns list of clauses or None if error / no API key.
    """
    if not groq_client or not GROQ_API_KEY:
        return None  # fallback to rule-based

    lang_desc = (
        "English (simple, non-legal, friendly tone)"
        if language == "en"
        else "Hinglish (mix of Hindi and English, written in Latin letters, very simple)"
    )

    system_msg = (
        "You are a careful legal assistant for Indian consumers.\n"
        "You read contracts (loan agreements, credit card T&Cs, EMI plans, insurance, rental agreements).\n"
        "Your job is to identify clauses that may create risk for a normal customer, then explain them in very simple language.\n"
        "You are NOT giving legal advice, only a simple explanation."
    )

    # Truncate very long documents so request doesn't explode
    truncated_text = full_text[:15000]

    user_msg = f"""
Read the following contract text and extract all clauses that look risky for a normal customer
in India. Focus especially on:

1. Lock-in or minimum tenure (hard to exit a plan / agreement).
2. Foreclosure / prepayment charges for loans and EMIs.
3. Penalties, late fees, or high overdue interest.
4. Automatic renewal of services / subscriptions.
5. Data sharing / third-party marketing / sharing with partners.
6. Hidden fees like processing fees, non-refundable fees, maintenance charges, etc.

The contract text is:

\"\"\"{truncated_text}\"\"\" 

Return ONLY valid JSON (no explanation text outside JSON) with this structure:

{{
  "clauses": [
    {{
      "type": "lock_in" | "foreclosure" | "penalty" | "auto_renew" | "data_sharing" | "charges" | "other",
      "title": "short human-readable title for the clause",
      "severity": "high" | "medium" | "low",
      "original_text": "exact sentence or paragraph from the contract that is risky",
      "simplified_text": "very simple explanation in {lang_desc}"
    }}
  ]
}}

Rules:
- Only include clauses that are actually risky or important.
- If nothing is risky, return: {{ "clauses": [] }}
- Keep "original_text" short but complete enough to understand the clause.
- Make "simplified_text" 1–3 short sentences, extremely simple {lang_desc}.
- Do NOT add any extra keys. Do NOT wrap the JSON with ``` or any markdown.
""".strip()

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        content = completion.choices[0].message.content.strip()

        # Try to safely extract JSON even if model wraps it weirdly
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            return None

        json_str = content[start : end + 1]
        data = json.loads(json_str)

        clauses = data.get("clauses", [])
        cleaned = []
        for c in clauses:
            cleaned.append({
                "type": c.get("type", "other"),
                "title": c.get("title", "Risky clause"),
                "severity": c.get("severity", "medium").lower(),
                "original_text": c.get("original_text", "").strip(),
                "simplified_text": c.get("simplified_text", "").strip(),
            })
        return cleaned

    except Exception:
        return None


# =========================
# SIMPLE RULE-BASED FALLBACK
# =========================
def fallback_detect_risks(text: str, language: str):
    """
    Keyword rules.
    Used only if AI-based detection fails.
    """
    rules = {
        "lock_in": {
            "title": "Lock-in Period",
            "severity": "high",
            "keywords": ["lock-in", "lock in", "minimum tenure", "cannot cancel", "min tenure"]
        },
        "foreclosure": {
            "title": "Foreclosure / Prepayment Charges",
            "severity": "high",
            "keywords": ["foreclosure", "prepayment", "pre-closure", "pre closure"]
        },
        "penalty": {
            "title": "Penalty & Late Fees",
            "severity": "high",
            "keywords": ["late fee", "late payment", "penalty", "overdue interest"]
        },
        "auto_renew": {
            "title": "Automatic Renewal",
            "severity": "medium",
            "keywords": ["auto renewal", "auto-renewal", "automatically renewed"]
        },
        "data_sharing": {
            "title": "Data Sharing & Third-Party Consent",
            "severity": "medium",
            "keywords": ["third party", "share your data", "marketing purposes", "partners and affiliates"]
        },
        "charges": {
            "title": "Hidden Charges & Fees",
            "severity": "medium",
            "keywords": ["processing fee", "non-refundable", "service charge", "additional charges", "maintenance fee"]
        }
    }

    def simple_explanation(title: str, language: str) -> str:
        if language == "hi":
            mapping = {
                "Lock-in Period": "Iska matlab hai ki aap kuch time tak yeh plan ya agreement easily band nahi kar sakte.",
                "Foreclosure / Prepayment Charges": "Agar aap loan ya EMI jaldi band karoge to extra charges ya penalty lag sakti hai.",
                "Penalty & Late Fees": "Payment delay hone par aapko extra late fee ya penalty deni padegi.",
                "Automatic Renewal": "Agar aap time se cancel nahi karoge to yeh plan automatically renew ho sakta hai.",
                "Data Sharing & Third-Party Consent": "Aapka personal data dusri companies ke saath share ho sakta hai.",
                "Hidden Charges & Fees": "Isme aise hidden charges ho sakte hain jo pehle clearly nazar nahi aate."
            }
            return mapping.get(title, "Yeh clause aapke liye risk create kar sakta hai. Dhyan se padho.")
        else:
            mapping = {
                "Lock-in Period": "This means you may not be able to easily exit or cancel this plan for some time.",
                "Foreclosure / Prepayment Charges": "If you close the loan or EMI early, you may have to pay extra foreclosure or prepayment charges.",
                "Penalty & Late Fees": "If your payment is late, you may need to pay penalty or late fees.",
                "Automatic Renewal": "The plan may renew automatically unless you cancel it in time.",
                "Data Sharing & Third-Party Consent": "Your personal data may be shared with other companies or partners.",
                "Hidden Charges & Fees": "There might be extra fees that are not clearly visible at first."
            }
            return mapping.get(title, "This clause might create some risk for you. Please read it carefully.")

    text_clean = text.replace("\n", " ")
    sentences = [s.strip() for s in re.split(r"[.!?]", text_clean) if s.strip()]

    detected = []
    seen = set()

    for sentence in sentences:
        lower = sentence.lower()
        for key, rule in rules.items():
            for kw in rule["keywords"]:
                if kw in lower:
                    tag = (rule["title"], sentence)
                    if tag in seen:
                        continue
                    seen.add(tag)

                    detected.append({
                        "type": key,
                        "title": rule["title"],
                        "severity": rule["severity"],
                        "original_text": sentence,
                        "simplified_text": simple_explanation(rule["title"], language)
                    })
                    break
    return detected


# =========================
# RISK SCORE + LEVEL
# =========================
def calculate_risk_score(clauses):
    """
    - high = +25
    - medium = +15
    - low = +5
    max 100
    """
    score = 0
    for c in clauses:
        sev = (c.get("severity") or "medium").lower()
        if sev == "high":
            score += 25
        elif sev == "medium":
            score += 15
        else:
            score += 5
    return min(score, 100)


def risk_level_from_score(score: int) -> str:
    if score < 30:
        return "low"
    elif score < 70:
        return "medium"
    else:
        return "high"


# =========================
# MAIN API: /analyze
# =========================
@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    language: str = Form("en")  # "en" or "hi"
):
    """
    - Extract text
    - Prefer AI to detect risky clauses
    - If AI fails, use rule-based fallback
    - Calculate risk score + summary
    """
    filename = file.filename
    raw_text = extract_text_from_file(file)

    if not raw_text.strip():
        msg_en = "We could not read any text from this document. Please upload a text-based or clear PDF."
        msg_hi = "Is document se text read nahi ho paaya. Kripya ek clear text-based PDF ya file upload karein."
        return {
            "file_name": filename,
            "risk_score": 0,
            "risk_level": "unknown",
            "summary": msg_hi if language == "hi" else msg_en,
            "clauses": []
        }

    # 1) Try AI-based detection
    clauses = ai_detect_risks(raw_text, language)

    # 2) If AI fails or returns nothing, use fallback
    if clauses is None:
        clauses = fallback_detect_risks(raw_text, language)

    risk_score = calculate_risk_score(clauses)
    risk_level = risk_level_from_score(risk_score)

    high_count = sum(1 for c in clauses if (c.get("severity") or "").lower() == "high")
    med_count = sum(1 for c in clauses if (c.get("severity") or "").lower() == "medium")

    # English summary
    parts_en = []
    if risk_level == "high":
        parts_en.append("This document has HIGH risk. It contains clauses that can lock you in or cause significant extra costs.")
    elif risk_level == "medium":
        parts_en.append("This document has MEDIUM risk. It contains some clauses you should review carefully before signing.")
    else:
        parts_en.append("This document appears to have LOW risk based on our checks, but you should still read it once before signing.")

    if high_count:
        parts_en.append(f"We found about {high_count} high-severity clauses (e.g., heavy penalties or long lock-in).")
    if med_count:
        parts_en.append(f"We also found {med_count} medium-severity clauses (such as extra charges or data sharing).")

    parts_en.append("Scroll down to review each risky clause in simple language before you decide to sign.")
    summary_en = " ".join(parts_en)

    # Hinglish summary
    parts_hi = []
    if risk_level == "high":
        parts_hi.append("Yeh document HIGH risk wala hai. Isme aise clauses hain jo aapko lock-in kar sakte hain ya extra paise dilaa sakte hain.")
    elif risk_level == "medium":
        parts_hi.append("Yeh document MEDIUM risk ka hai. Isme kuch important clauses hain jo sign karne se pehle dhyaan se padhna chahiye.")
    else:
        parts_hi.append("Humaare checks ke hisaab se yeh document LOW risk lagta hai, lekin sign karne se pehle ek baar zaroor padhna chahiye.")

    if high_count:
        parts_hi.append(f"Humein lagbhag {high_count} high-risk clauses mile (jaise bada lock-in ya heavy penalty).")
    if med_count:
        parts_hi.append(f"Humein {med_count} medium-risk clauses bhi mile (jaise extra charges, processing fee, data sharing).")

    parts_hi.append("Neeche har risky clause ko simple Hinglish/English mein explain kiya gaya hai. Sign karne se pehle ek baar zaroor dekh lo.")
    summary_hi = " ".join(parts_hi)

    summary = summary_hi if language == "hi" else summary_en

    return {
        "file_name": filename,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "summary": summary,
        "clauses": clauses
    }


# =========================
# Run directly from VS Code terminal
# =========================
if __name__ == "__main__":
    import uvicorn
    # Clickable URL in VS Code: http://127.0.0.1:8003
    uvicorn.run("main:app", host="127.0.0.1", port=8003, reload=True)
