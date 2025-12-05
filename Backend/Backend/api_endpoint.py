"""
FastAPI Endpoint: Integration of LLM and Rule Engine

This file shows how to combine:
1. NLU (regex-based extraction) - extracts structured data from user text
2. Rule Engine - calculates eligibility
3. LLM Service - generates friendly responses

This is the main API endpoint that your React Native app will call.
Now integrated with the Orchestrator for full pipeline processing.
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import re
import json

from rule_engine import (
    UserFinancialProfile,
    LoanType,
    check_eligibility,
    get_loan_summary
)
from llm_service import (
    LLMService,
    EligibilityContext,
    ConversationMessage
)
from orchestrator import Orchestrator, PipelineStage

app = FastAPI(title="Multilingual AI Loan Advisor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM service
try:
    llm_service = LLMService()
except ValueError as e:
    print("=" * 60)
    print("ERROR: Gemini API Key Not Found")
    print("=" * 60)
    print(str(e))
    print("=" * 60)
    raise

# Initialize Orchestrator (reuses llm_service, enables STT, disables OCR for now)
try:
    orchestrator = Orchestrator(
        llm_service=llm_service,
        enable_ocr=False,  # Can be enabled when OCR is implemented
        enable_stt=True    # Enable STT for audio processing
    )
    print("✅ Orchestrator initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: Orchestrator initialization issue: {e}")
    print("   Falling back to basic mode")
    orchestrator = None

class ChatRequest(BaseModel):
    """Request from mobile app"""
    message: str
    session_id: str = "default"
    user_language: Optional[str] = None  


class ChatResponse(BaseModel):
    """Response to mobile app"""
    response: str
    session_id: str
    extracted_data: Optional[Dict] = None  
    eligibility_result: Optional[Dict] = None  
    needs_clarification: bool = False
    missing_info: Optional[List[str]] = None


class EligibilityCheckRequest(BaseModel):
    """Direct eligibility check request"""
    monthly_income: float
    age: int
    employment_months: int
    loan_type: str
    loan_amount_requested: Optional[float] = None
    loan_tenure_years: Optional[int] = None
    existing_loans_emi: float = 0.0
    existing_credit_cards_min_payment: float = 0.0

def extract_loan_amount(text: str) -> Optional[float]:
    """
    Extract loan amount from text using improved regex patterns
    
    Priority: Look for loan-specific keywords first to avoid confusion with income
    Examples:
        "I need 5 lakh loan" -> 500000
        "loan of ₹500000" -> 500000
        "5 lacs for loan" -> 500000
    """
    text = text.replace(",", "")
    text_lower = text.lower()
    
    loan_lakh_pattern = r"loan.*?(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s)?\b"
    match = re.search(loan_lakh_pattern, text_lower)
    if match:
        return float(match.group(1)) * 100000
    lakh_loan_pattern = r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s)?\s*(?:loan|for|of)"
    match = re.search(lakh_loan_pattern, text_lower)
    if match:
        return float(match.group(1)) * 100000
    
    loan_crore_pattern = r"loan.*?(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s)?\b"
    match = re.search(loan_crore_pattern, text_lower)
    if match:
        return float(match.group(1)) * 10000000
    
    crore_loan_pattern = r"(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s)?\s*(?:loan|for|of)"
    match = re.search(crore_loan_pattern, text_lower)
    if match:
        return float(match.group(1)) * 10000000
    
    loan_currency_pattern = r"loan.*?(?:of|for|amount)?\s*(?:₹|rupees?|rs\.?)\s*(\d+(?:\.\d+)?)"
    match = re.search(loan_currency_pattern, text_lower)
    if match:
        return float(match.group(1))
    
    loan_for_lakh_pattern = r"loan.*?for.*?(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s)?\b"
    match = re.search(loan_for_lakh_pattern, text_lower)
    if match:
        return float(match.group(1)) * 100000
    
    loan_for_crore_pattern = r"loan.*?for.*?(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s)?\b"
    match = re.search(loan_for_crore_pattern, text_lower)
    if match:
        return float(match.group(1)) * 10000000
    
    of_lakh_pattern = r"of\s+(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s)?\b"
    match = re.search(of_lakh_pattern, text_lower)
    if match:
        match_start = match.start()
        context_before = text_lower[max(0, match_start-30):match_start]
        if "loan" in context_before:
            return float(match.group(1)) * 100000
    
    for_crore_pattern = r"for\s+.*?(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s)?\b"
    match = re.search(for_crore_pattern, text_lower)
    if match:
        match_start = match.start()
        context_before = text_lower[max(0, match_start-50):match_start]
        if "loan" in context_before:
            return float(match.group(1)) * 10000000
    
    if "income" not in text_lower and "salary" not in text_lower and "earning" not in text_lower:
        lakh_pattern = r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)(?:s)?\b"
        match = re.search(lakh_pattern, text_lower)
        if match:
            match_start = match.start()
            context_before = text_lower[max(0, match_start-50):match_start]
            context_after = text_lower[match.end():min(len(text_lower), match.end()+20)]
            loan_keywords = ["loan", "for", "of", "want", "need", "looking", "borrow"]
            if any(word in context_before or word in context_after for word in loan_keywords):
                return float(match.group(1)) * 100000
            elif 1 <= float(match.group(1)) <= 100:
                return float(match.group(1)) * 100000
        
        crore_pattern = r"(\d+(?:\.\d+)?)\s*(?:crore|cr)(?:s)?\b"
        match = re.search(crore_pattern, text_lower)
        if match:
            match_start = match.start()
            context_before = text_lower[max(0, match_start-50):match_start]
            context_after = text_lower[match.end():min(len(text_lower), match.end()+20)]
            
            loan_keywords = ["loan", "for", "of", "want", "need", "looking", "borrow"]
            if any(word in context_before or word in context_after for word in loan_keywords):
                return float(match.group(1)) * 10000000
            elif 1 <= float(match.group(1)) <= 10:
                return float(match.group(1)) * 10000000
    
    if "loan" in text_lower:
        large_number_pattern = r"\b(\d{5,})\b"
        matches = re.findall(large_number_pattern, text)
        for match_str in matches:
            num = float(match_str)
            if 100000 <= num <= 100000000:  
                return num
    
    return None


def extract_income(text: str) -> Optional[float]:
    """
    Extract monthly income from text with improved patterns
    
    Priority: Look for income-specific keywords to avoid confusion with loan amounts
    """
    text = text.replace(",", "")
    text_lower = text.lower()
    monthly_pattern = r"(\d+(?:\.\d+)?)\s*(?:k|thousand)?\s*(?:per month|monthly|pm)"
    income_k_pattern = r"(?:income|salary|earning|earn|make|get).*?(\d+(?:\.\d+)?)\s*k\b"
    match = re.search(income_k_pattern, text_lower)
    if match:
        return float(match.group(1)) * 1000
    k_income_pattern = r"(\d+(?:\.\d+)?)\s*k\s*(?:income|salary|per month|monthly)"
    match = re.search(k_income_pattern, text_lower)
    if match:
        return float(match.group(1)) * 1000
    income_currency_pattern = r"(?:income|salary|earning|earn|make|get).*?(?:is|of|₹|rupees?|rs\.?)\s*(\d+(?:\.\d+)?)"
    match = re.search(income_currency_pattern, text_lower)
    if match:
        num = float(match.group(1))
        if 10000 <= num <= 1000000:
            return num
    match = re.search(monthly_pattern, text_lower)
    if match:
        num_str = match.group(1)
        if "k" in text_lower[max(0, match.start()-5):match.end()]:
            return float(num_str) * 1000
        else:
            num = float(num_str)
            if 10000 <= num <= 1000000:
                return num
    
    if "loan" not in text_lower and "borrow" not in text_lower:
        k_pattern = r"(\d+(?:\.\d+)?)\s*k\b"
        match = re.search(k_pattern, text_lower)
        if match:
            return float(match.group(1)) * 1000
    
    if "income" in text_lower or "salary" in text_lower or "earning" in text_lower:
        medium_number_pattern = r"\b(\d{4,6})\b"
        matches = re.findall(medium_number_pattern, text)
        for match_str in matches:
            num = float(match_str)
            if 10000 <= num <= 500000:  
                return num
    
    return None


def extract_tenure(text: str) -> Optional[int]:
    """
    Extract loan tenure in years
    
    Avoids confusion with age by looking for loan-specific context
    """
    text_lower = text.lower()
    
    loan_tenure_patterns = [
        r"loan.*?(?:for|of|with|tenure).*?(\d+)\s*(?:years?|yrs?|y)\b",
        r"tenure.*?(\d+)\s*(?:years?|yrs?|yrs?)\b",
        r"repay.*?(?:in|for|over).*?(\d+)\s*(?:years?|yrs?)\b",
        r"(\d+)\s*(?:years?|yrs?)\s*(?:loan|tenure|repayment)"
    ]
    
    for pattern in loan_tenure_patterns:
        match = re.search(pattern, text_lower)
        if match:
            years = int(match.group(1))
            if 1 <= years <= 30:  
                return years
    
    loan_month_patterns = [
        r"loan.*?(?:for|of|with).*?(\d+)\s*(?:months?|mon)\b",
        r"tenure.*?(\d+)\s*(?:months?|mon)\b"
    ]
    
    for pattern in loan_month_patterns:
        match = re.search(pattern, text_lower)
        if match:
            months = int(match.group(1))
            if 12 <= months <= 360:  
                return months // 12
    
    year_pattern = r"(\d+)\s*(?:years?|yrs?|y)\b"
    matches = list(re.finditer(year_pattern, text_lower))
    
    for match in matches:
        years = int(match.group(1))
        start = max(0, match.start() - 15)
        end = min(len(text_lower), match.end() + 15)
        context = text_lower[start:end]
        
        if any(phrase in context for phrase in ["age", "aged", " am ", "years old", "yrs old"]):
            continue  
        
        if any(word in context for word in ["loan", "tenure", "repay", "emi", "for", "of"]):
            if 1 <= years <= 30:
                return years
    
    month_pattern = r"(\d+)\s*(?:months?|mon)\b"
    match = re.search(month_pattern, text_lower)
    if match:
        months = int(match.group(1))
        if 12 <= months <= 360:  
            return months // 12
    
    return None


def extract_age(text: str) -> Optional[int]:
    """
    Extract age from text
    Prioritizes age-specific patterns to avoid confusion with employment duration
    """
    text_lower = text.lower()
    
    age_patterns = [
        r"(?:age|aged)\s*(?:is|of)?\s*(\d{1,3})\b",
        r"am\s+(\d{1,3})\s+(?:years?\s+)?old\b",
        r"(\d{1,3})\s+years?\s+old\b",
        r"(\d{1,3})\s+years?\s+of\s+age\b"
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, text_lower)
        if match:
            age = int(match.group(1))
            if 18 <= age <= 100:  
                return age
    
    return None


def extract_loan_type(text: str) -> Optional[LoanType]:
    """
    Extract loan type from text with improved pattern matching
    
    Priority order: specific loan types first, then generic keywords
    """
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["business loan", "business", "commercial loan", "startup loan"]):
        return LoanType.BUSINESS
    
    if any(word in text_lower for word in ["education loan", "student loan", "study loan", "education", "student"]):
        return LoanType.EDUCATION
    
    if any(word in text_lower for word in ["car loan", "vehicle loan", "auto loan", "car", "vehicle", "auto"]):
        return LoanType.CAR
    
    if any(word in text_lower for word in ["home loan", "housing loan", "house loan", "home", "house", "housing"]):
        return LoanType.HOME
    
    if any(word in text_lower for word in ["personal loan", "personal", "unsecured loan"]):
        return LoanType.PERSONAL
    
    return None


def extract_existing_loans_emi(text: str) -> Optional[float]:
    """
    Extract existing loans EMI from text
    Examples: "I pay 5000 EMI", "existing loan EMI is 10000", "current EMI 15000"
    """
    text_lower = text.lower()
    patterns = [
        r"(?:existing|current|old|previous).*?(?:loan|emi).*?(?:is|of|₹|rupees?|rs\.?)\s*(\d+(?:\.\d+)?)",
        r"(?:loan|emi).*?(?:existing|current|old|previous).*?(?:is|of|₹|rupees?|rs\.?)\s*(\d+(?:\.\d+)?)",
        r"(?:pay|paying|have|have a).*?(\d+(?:\.\d+)?)\s*(?:per month|monthly|pm|emi)",
        r"emi.*?(?:is|of|₹|rupees?|rs\.?)\s*(\d+(?:\.\d+)?)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            num = float(match.group(1))
            if 1000 <= num <= 500000:
                return num
    
    return None
def extract_credit_card_payment(text: str) -> Optional[float]:
    """
    Extract credit card minimum payment from text
    Examples: "credit card payment 5000", "card payment is 10000"
    """
    text_lower = text.lower()
    patterns = [
        r"(?:credit card|card).*?(?:payment|minimum|min).*?(?:is|of|₹|rupees?|rs\.?)\s*(\d+(?:\.\d+)?)",
        r"(?:credit card|card).*?(\d+(?:\.\d+)?)\s*(?:per month|monthly|pm)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            num = float(match.group(1))
            if 500 <= num <= 100000:
                return num
    
    return None


def extract_employment_status(text: str) -> Optional[str]:
    """
    Extract employment status from text
    Returns: "employed", "self_employed", "unemployed", or None
    """
    text_lower = text.lower()
    self_employed_keywords = ["self employed", "self-employed", "business owner", "own business", 
                              "freelancer", "consultant", "entrepreneur"]
    if any(keyword in text_lower for keyword in self_employed_keywords):
        return "self_employed"
    unemployed_keywords = ["unemployed", "not working", "no job", "between jobs", "looking for work"]
    if any(keyword in text_lower for keyword in unemployed_keywords):
        return "unemployed"
    employed_keywords = ["employed", "working", "job", "salary", "salaried", "employee", 
                         "work at", "work for", "company"]
    if any(keyword in text_lower for keyword in employed_keywords):
        return "employed"
    
    return None


def extract_employment_months(text: str) -> Optional[int]:
    """
    Extract employment duration in months
    Handles: "working for 2 years", "employed 24 months", "2 years", "24 months", etc.
    IMPORTANT: Excludes age patterns like "27 years old" to avoid confusion
    """
    text_lower = text.lower()
    age_indicators = [r"\d+\s+years?\s+old", r"age\s+(?:is|of)?\s*\d+", r"aged\s+\d+", r"\d+\s+years?\s+of\s+age"]
    for age_pattern in age_indicators:
        if re.search(age_pattern, text_lower):
            return None  
    patterns = [
        
        r"(?:working|employed|experience|job).*?(?:for|since|of)?\s*(\d+)\s*(?:years?|yrs?|y)\b",
        r"(?:working|employed|experience|job).*?(?:for|since|of)?\s*(\d+)\s*(?:months?|mon)\b",
        r"(\d+)\s*(?:years?|yrs?|y)\s*(?:of|in|at|with).*?(?:experience|employment|working|job)",
        r"(\d+)\s*(?:months?|mon)\s*(?:of|in|at|with).*?(?:experience|employment|working|job)",
        r"(\d+)\s*(?:years?|yrs?|y)\b(?!\s+old)",
        r"(\d+)\s*(?:months?|mon)\b",
    ]
    
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, text_lower)
        if match:
            num = int(match.group(1))
            if i in [0, 2, 4] or "year" in pattern or "yr" in pattern:
                months = num * 12
                if 1 <= months <= 600:
                    return months
            else:
                if 1 <= num <= 600:
                    return num
    
    return None


def detect_intent(text: str) -> str:
    """
    Detect user intent from text
    
    Returns:
        - "apply_loan": User wants to apply for a loan
        - "check_eligibility": User wants to check eligibility
        - "ask_question": User has a general question
        - "provide_info": User is providing information
    """
    text_lower = text.lower()
    apply_keywords = ["apply", "want", "need", "looking for", "interested in", "get a loan"]
    if any(keyword in text_lower for keyword in apply_keywords):
        return "apply_loan"
    eligibility_keywords = ["eligible", "eligibility", "can i get", "qualify", "qualification", "check"]
    if any(keyword in text_lower for keyword in eligibility_keywords):
        return "check_eligibility"
    question_keywords = ["what", "how", "why", "when", "where", "?", "explain", "tell me"]
    if any(keyword in text_lower for keyword in question_keywords):
        return "ask_question"
    
    return "provide_info"


def extract_financial_data(text: str, existing_profile: Optional[UserFinancialProfile] = None) -> Dict:
    """
    Extract all financial data from user text (IMPROVED)
    
    Returns dictionary with:
    - extracted: Dictionary of extracted fields
    - missing: List of missing required fields
    - intent: Detected user intent
    """
    extracted = {}
    missing = []
    intent = detect_intent(text)
    loan_amount = extract_loan_amount(text)
    if loan_amount:
        extracted["loan_amount_requested"] = loan_amount
    elif not existing_profile or existing_profile.loan_amount_requested == 0:
        missing.append("loan amount")
    
    income = extract_income(text)
    if income:
        extracted["monthly_income"] = income
    elif not existing_profile or existing_profile.monthly_income == 0:
        missing.append("monthly income")
    
    age = extract_age(text)
    if age:
        extracted["age"] = age
    elif not existing_profile or existing_profile.age == 0:
        missing.append("age")
    
    employment_status = extract_employment_status(text)
    if employment_status:
        extracted["employment_status"] = employment_status
    
    if "age" not in extracted:
        employment = extract_employment_months(text)
        if employment:
            extracted["employment_months"] = employment
    else:
        employment = extract_employment_months(text)
        if employment:
            if age and employment == age * 12:
                pass
            else:
                extracted["employment_months"] = employment
    
    has_income = income or (existing_profile and existing_profile.monthly_income > 0)
    if has_income and not employment and (not existing_profile or existing_profile.employment_months == 0):
        missing.append("employment duration")
    elif not has_income and (not existing_profile or existing_profile.employment_months == 0):
        missing.append("employment duration")
    
    tenure = extract_tenure(text)
    if tenure:
        extracted["loan_tenure_years"] = tenure
    elif not existing_profile or existing_profile.loan_tenure_years == 0:
        missing.append("loan tenure")
    
    
    loan_type = extract_loan_type(text)
    if loan_type:
        extracted["loan_type"] = loan_type
    elif not existing_profile or not existing_profile.loan_type:
        missing.append("loan type")
    
    existing_emi = extract_existing_loans_emi(text)
    if existing_emi:
        extracted["existing_loans_emi"] = existing_emi
    
    credit_card_payment = extract_credit_card_payment(text)
    if credit_card_payment:
        extracted["existing_credit_cards_min_payment"] = credit_card_payment
    
    return {
        "extracted": extracted,
        "missing": missing,
        "intent": intent
    }



# Note: Session management is now handled by the Orchestrator
# These functions are kept for backward compatibility with /eligibility/check endpoint



@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint - handles conversational loan advisor
    
    Now uses the Orchestrator for full pipeline processing:
    1. STT (if audio provided)
    2. Normalization
    3. NLU (Intent + Slot Extraction)
    4. Rules Engine (Eligibility Calculation)
    5. LLM (Generate Response)
    6. DB/Audit (Logging)
    """
    try:
        if orchestrator is None:
            raise HTTPException(
                status_code=503, 
                detail="Orchestrator not available. Please check server configuration."
            )
        
        # Process request through the full pipeline
        pipeline_response = orchestrator.process_request(
            session_id=request.session_id,
            user_input=request.message,
            user_language=request.user_language,
            audio_data=None,  # Can be extended to accept audio files
            document_data=None  # Can be extended to accept documents
        )
        
        # Extract data from pipeline response
        response_text = pipeline_response.get("response", "No response generated")
        extracted_data = pipeline_response.get("extracted_data", {})
        eligibility_result_data = pipeline_response.get("eligibility_result")
        missing_info = pipeline_response.get("missing_info", [])
        
        # Determine if clarification is needed
        # Check if eligibility was calculated (means we have enough info)
        needs_clarification = eligibility_result_data is None
        
        # Use eligibility result directly (orchestrator now includes all fields)
        eligibility_result = eligibility_result_data
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            extracted_data=extracted_data if extracted_data else None,
            eligibility_result=eligibility_result,
            needs_clarification=needs_clarification,
            missing_info=missing_info if missing_info else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.post("/chat/audio", response_model=ChatResponse)
async def chat_audio_endpoint(
    audio_file: UploadFile = File(..., description="Audio file (mp3, wav, m4a, etc.)"),
    session_id: str = Form("default", description="Session ID for conversation tracking"),
    user_language: Optional[str] = Form(None, description="User's preferred language (e.g., 'english', 'hindi')")
):
    """
    Chat endpoint with audio input - handles voice queries
    
    Accepts audio files and processes them through the full pipeline:
    1. STT (Speech-to-Text) - converts audio to text
    2. Normalization - text cleaning
    3. NLU (Intent + Slot Extraction)
    4. Rules Engine (Eligibility Calculation)
    5. LLM (Generate Response)
    6. DB/Audit (Logging)
    
    Supported audio formats: mp3, wav, m4a, flac, ogg, etc.
    """
    try:
        if orchestrator is None:
            raise HTTPException(
                status_code=503, 
                detail="Orchestrator not available. Please check server configuration."
            )
        
        # Validate audio file
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            # Allow if content_type is not set (some clients don't send it)
            # We'll let Whisper handle format validation
            pass
        
        # Read audio file content
        audio_data = await audio_file.read()
        
        if len(audio_data) == 0:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty. Please upload a valid audio file."
            )
        
        # Process request through the full pipeline with audio
        pipeline_response = orchestrator.process_request(
            session_id=session_id,
            user_input="",  # Will be generated from audio via STT
            user_language=user_language,
            audio_data=audio_data,  # Pass audio data for STT processing
            document_data=None
        )
        
        # Extract data from pipeline response
        response_text = pipeline_response.get("response", "No response generated")
        extracted_data = pipeline_response.get("extracted_data", {})
        eligibility_result_data = pipeline_response.get("eligibility_result")
        missing_info = pipeline_response.get("missing_info", [])
        
        # Get transcribed text from STT stage (if available)
        pipeline_status = pipeline_response.get("pipeline_status", {})
        stt_status = pipeline_status.get("stt", {})
        transcribed_text = None
        
        # Try to get transcribed text from orchestrator context
        if orchestrator.sessions.get(session_id):
            context = orchestrator.sessions[session_id]
            stt_result = context.component_results.get(PipelineStage.STT)
            if stt_result and stt_result.data:
                transcribed_text = stt_result.data.get("text")
        
        # Add transcribed text to extracted_data if available
        if transcribed_text and extracted_data:
            extracted_data["transcribed_text"] = transcribed_text
        
        # Determine if clarification is needed
        needs_clarification = eligibility_result_data is None
        
        # Use eligibility result directly (orchestrator now includes all fields)
        eligibility_result = eligibility_result_data
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            extracted_data=extracted_data if extracted_data else None,
            eligibility_result=eligibility_result,
            needs_clarification=needs_clarification,
            missing_info=missing_info if missing_info else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing audio request: {str(e)}"
        )


@app.post("/eligibility/check")
async def check_eligibility_endpoint(request: EligibilityCheckRequest):
    """
    Direct eligibility check endpoint (if you have all data upfront)
    """
    try:
        loan_type_map = {
            "personal_loan": LoanType.PERSONAL,
            "home_loan": LoanType.HOME,
            "car_loan": LoanType.CAR,
            "education_loan": LoanType.EDUCATION
        }
        
        loan_type = loan_type_map.get(request.loan_type.lower())
        if not loan_type:
            raise HTTPException(status_code=400, detail="Invalid loan type")
        
        profile = UserFinancialProfile(
            monthly_income=request.monthly_income,
            age=request.age,
            employment_months=request.employment_months,
            loan_type=loan_type,
            loan_amount_requested=request.loan_amount_requested or 0,
            loan_tenure_years=request.loan_tenure_years or 0,
            existing_loans_emi=request.existing_loans_emi,
            existing_credit_cards_min_payment=request.existing_credit_cards_min_payment
        )
        
        result = check_eligibility(profile)
        summary = get_loan_summary(profile, result)
        
        return {
            "eligibility": summary,
            "message": result.approval_message if result.is_eligible else "; ".join(result.rejection_reasons)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Loan Advisor API"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

