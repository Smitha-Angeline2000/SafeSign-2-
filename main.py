import os
import io
import json
import re
from typing import Any, Dict, List

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from groq import Groq

# OCR-related imports
from PIL import Image
import pytesseract

# PDF tools
import pdfplumber

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


app = FastAPI()

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # okay for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "SafeSign backend running with AI + OCR support!"}


def get_groq_client() -> Groq:
    """
    Create Groq client using API key from environment.
    Set:  export GROQ_API_KEY="your_key_here"
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")
    return Groq(api_key=api_key)


def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes using Tesseract via pytesseract.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return ""

    try:
        text = pytesseract.image_to_string(image)
    except Exception:
        text = ""

    return text or ""


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF:
    1. Try pdfplumber (normal text-based PDFs)
    2. If that fails or is empty, try OCR on each page image via pdf2image + Tesseract
    """
    text = ""

    # Step 1: normal text extraction
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages_text)
    except Exception:
        text = ""

    # If we already got decent text, return it
    if text and len(text.strip()) > 30:
        return text

    # Step 2: OCR fallback for scanned PDFs / image-based PDFs
    if not PDF2IMAGE_AVAILABLE:
        # pdf2image missing – can't OCR pages
        return text  # may be empty or partial

    try:
        images = convert_from_bytes(pdf_bytes)
    except Exception:
        return text  # fallback

    ocr_chunks = []
    for img in images:
        try:
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text:
                ocr_chunks.append(ocr_text)
        except Exception:
            continue

    if ocr_chunks:
        return "\n".join(ocr_chunks)

    return text or ""


def extract_text_from_file(upload_file: UploadFile) -> str:
    """
    Extracts text from uploaded file.
    - If PDF: normal text extraction + OCR fallback
    - If IMAGE (jpg/png): OCR
    - Otherwise: decodes as UTF-8
    """
    filename = (upload_file.filename or "").lower()
    content = upload_file.file.read()

    if not content:
        return ""

    # Handle images directly
    if any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
        return ocr_image_bytes(content)

    # Handle PDFs
    if filename.endswith(".pdf"):
        return extract_text_from_pdf_bytes(content)

    # Fallback: treat as text file
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def fallback_risk_level(score: int) -> str:
    if score < 30:
        return "low"
    elif score < 70:
        return "medium"
    else:
        return "high"


def call_groq_for_analysis(text: str, language: str) -> Dict[str, Any]:
    """
    Sends the full document text to Groq LLM and asks it to:
    - detect risky clauses
    - assign severity
    - generate simplified explanation (English or Hinglish)
    - compute an overall risk score and risk level
    - write a short overall summary

    Returns a parsed Python dict.
    """

    client = get_groq_client()

    # limit very long docs
    max_chars = 20000
    if len(text) > max_chars:
        text_for_model = text[:max_chars]
    else:
        text_for_model = text

    lang_label = "English" if language == "en" else "Hinglish (mix of Hindi and English in Latin script)"

    system_prompt = (
        "You are an expert contract and financial-risk analysis assistant. "
        "Your job is to read the full document carefully and identify clauses that may create risk for a consumer, such as:\n"
        "- lock-in periods or minimum tenure where the user cannot easily exit\n"
        "- foreclosure or prepayment charges for closing loans early\n"
        "- penalties, late fees, or high interest on overdue amounts\n"
        "- hidden charges, non-refundable fees, and vague extra fees\n"
        "- automatic renewal / auto-renewal of plans or subscriptions\n"
        "- data sharing with third parties, partners, advertisers, or analytics vendors\n"
        "- any clearly unfair, illegal, or one-sided terms\n\n"
        "For each risky clause, you must:\n"
        "- copy the original text snippet of that clause (or the key sentence(s))\n"
        "- assign a severity: 'low', 'medium', or 'high'\n"
        "- assign a category type (e.g., 'lock_in', 'foreclosure', 'penalty', 'charges', 'auto_renew', 'data_sharing', 'illegal_terms', or 'other')\n"
        f"- generate a simplified explanation in {lang_label} that a non-expert user can understand.\n\n"
        "Then you must compute an overall risk_score from 0 to 100, where:\n"
        "- 0–29 = low risk\n"
        "- 30–69 = medium risk\n"
        "- 70–100 = high risk\n\n"
        "You must also provide a short overall summary of the document's risk in plain language.\n\n"
        "IMPORTANT:\n"
        "- Be cautious and conservative: if in doubt, mark a clause as at least medium risk.\n"
        "- Use the numeric values in the clause (e.g., percentage penalties, lock-in months) to decide severity.\n"
        "- Do NOT hallucinate clauses; only use what actually appears in the given text.\n"
        "- Output MUST be valid JSON only, no extra text.\n"
        "- JSON keys must exactly match the following schema."
    )

    user_prompt = {
        "role": "user",
        "content": (
            "Analyse the following contract or financial document and respond ONLY with valid JSON "
            "conforming EXACTLY to this schema:\n\n"
            "{\n"
            '  "risk_score": <integer 0-100>,\n'
            '  "risk_level": "low" | "medium" | "high",\n'
            '  "summary": "<short plain-language summary in the requested language>",\n'
            '  "clauses": [\n'
            "    {\n"
            '      "type": "lock_in" | "foreclosure" | "penalty" | "charges" | "auto_renew" | "data_sharing" | "illegal_terms" | "other",\n'
            '      "title": "<short human-readable title>",\n'
            '      "original_text": "<exact clause or key sentence(s) from the document>",\n'
            '      "simplified_text": "<simple explanation in the requested language>",\n'
            '      "severity": "low" | "medium" | "high"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"Requested explanation language: {lang_label}.\n\n"
            "Now here is the document text to analyse:\n\n"
            f"{text_for_model}"
        ),
    }

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # or whichever Groq model you're using
        messages=[
            {"role": "system", "content": system_prompt},
            user_prompt,
        ],
        temperature=0.1,
    )

    raw_content = completion.choices[0].message.content

    def try_parse_json(s: str) -> Dict[str, Any]:
        s = s.strip()
        # Remove markdown fences if present
        if s.startswith(""):
            s = re.sub(r"^(json)?", "", s.strip(), flags=re.IGNORECASE).strip()
            if s.endswith("```"):
                s = s[:-3].strip()
        return json.loads(s)

    try:
        data = try_parse_json(raw_content)
    except Exception:
        data = {
            "risk_score": 0,
            "risk_level": "low",
            "summary": (
                "The AI analysis failed to return structured data. "
                "Please review the document manually; no structured risk result is available."
            ),
            "clauses": [],
        }

    # Sanity checks
    risk_score = data.get("risk_score")
    if not isinstance(risk_score, int):
        try:
            risk_score = int(risk_score)
        except Exception:
            risk_score = 0
    risk_score = max(0, min(100, risk_score))
    data["risk_score"] = risk_score

    risk_level = str(data.get("risk_level", "")).lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = fallback_risk_level(risk_score)
    data["risk_level"] = risk_level

    clauses = data.get("clauses")
    if not isinstance(clauses, list):
        clauses = []

    cleaned_clauses: List[Dict[str, Any]] = []
    for c in clauses:
        if not isinstance(c, dict):
            continue
        cleaned_clauses.append({
            "type": c.get("type", "other"),
            "title": c.get("title", "Risky clause"),
            "original_text": c.get("original_text", ""),
            "simplified_text": c.get("simplified_text", ""),
            "severity": c.get("severity", "medium").lower(),
        })
    data["clauses"] = cleaned_clauses

    if not isinstance(data.get("summary"), str):
        data["summary"] = "No summary available from the AI analysis."

    return data


@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    language: str = Form("en"),  # "en" -> English, "hi" -> Hinglish
):
    """
    Main endpoint:
    - Extracts text from file (PDF or image) using OCR if needed
    - Sends it to Groq LLM for fully AI-based analysis
    - Returns overall risk score, level, summary, and per-clause explanations
    """

    filename = file.filename or "document"

    raw_text = extract_text_from_file(file)

    if not raw_text or not raw_text.strip():
        msg_en = "We could not read any text from this document. If it is an image/scanned PDF, please ensure it is clear and high-resolution."
        msg_hi = "Is document se text read nahi ho paaya. Agar yeh image/scanned PDF hai, to please ek clear high-resolution copy upload karein."
        return {
            "file_name": filename,
            "risk_score": 0,
            "risk_level": "unknown",
            "summary": msg_hi if language == "hi" else msg_en,
            "clauses": [],
        }

    ai_result = call_groq_for_analysis(raw_text, language)

    return {
        "file_name": filename,
        "risk_score": ai_result["risk_score"],
        "risk_level": ai_result["risk_level"],
        "summary": ai_result["summary"],
        "clauses": ai_result["clauses"],
    }


# Optional: run with python main.py
if _name_ == "_main_":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8003, reload=True)