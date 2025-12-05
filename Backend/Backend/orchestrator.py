"""
Orchestration Layer for Multilingual AI Loan Advisor

This module coordinates all components:
- STT (Speech-to-Text)
- NLU (Intent + Slot Extraction)
- Rules Engine (EMI/DTI/Eligibility)
- OCR (Document Processing)
- LLM (Conversation & Explanations)
- DB (Session Management)

Features:
- Sequential pipeline execution
- Error handling & retries
- Logging & audit trail
- Confidence thresholds
- Fallback mechanisms
"""

import logging
import time
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback

from llm_service import LLMService, ConversationMessage, EligibilityContext
from rule_engine import (
    UserFinancialProfile,
    LoanType,
    check_eligibility,
    get_loan_summary
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
try:
    from stt_service import STTService
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    logger.warning("STT service not available - install stt_service.py")


class ComponentStatus(str, Enum):
    """Status of each component"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStage(str, Enum):
    """Pipeline stages"""
    STT = "stt"  # Speech-to-Text
    NORMALIZATION = "normalization"
    NLU = "nlu"  # Natural Language Understanding
    RULES = "rules"  # Rules Engine
    OCR = "ocr"  # Optional document processing
    LLM = "llm"  # Language Model
    DB = "db"  # Database/Audit


@dataclass
class ComponentResult:
    """Result from a component execution"""
    component: PipelineStage
    status: ComponentStatus
    data: Any = None
    error: Optional[str] = None
    confidence: float = 1.0
    execution_time: float = 0.0
    retry_count: int = 0


@dataclass
class PipelineContext:
    """Context passed through the pipeline"""
    session_id: str
    user_input: str  # Text input (after STT if needed)
    user_profile: Optional[UserFinancialProfile] = None
    extracted_data: Dict = field(default_factory=dict)
    eligibility_result: Optional[Any] = None
    conversation_history: List[ConversationMessage] = field(default_factory=list)
    component_results: Dict[PipelineStage, ComponentResult] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)


class Orchestrator:
    """
    Main orchestration class that coordinates all components
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        stt_service: Optional[Any] = None,
        max_retries: int = 3,
        confidence_threshold: float = 0.7,
        enable_ocr: bool = False,
        enable_stt: bool = True
    ):
        """
        Initialize orchestrator
        
        Args:
            llm_service: LLM service instance
            stt_service: STT service instance (optional, will create if STT_AVAILABLE)
            max_retries: Maximum retry attempts for failed components
            confidence_threshold: Minimum confidence for accepting results
            enable_ocr: Enable OCR processing
            enable_stt: Enable Speech-to-Text processing
        """
        self.llm_service = llm_service or LLMService()
        self.max_retries = max_retries
        self.confidence_threshold = confidence_threshold
        self.enable_ocr = enable_ocr
        self.enable_stt = enable_stt and STT_AVAILABLE
        
        if self.enable_stt:
            try:
                self.stt_service = stt_service or STTService()
                logger.info("STT service initialized")
            except Exception as e:
                logger.warning(f"STT service initialization failed: {e}")
                self.enable_stt = False
                self.stt_service = None
        else:
            self.stt_service = None
        
        self.sessions: Dict[str, PipelineContext] = {}
        
        # Define the order of questions to ask
        self.question_order = [
            "greeting",           # 1. Greeting prompt
            "loan amount",        # 2. Loan amount
            "loan type",          # 2b. Loan type (needed for eligibility)
            "monthly income",     # 3. Monthly salary
            "age",                # 4. Age
            "loan tenure",        # 5. Loan tenure
            "employment status",  # 6. Employment status (salaried or not)
            "existing debts",     # 7. Existing loans/payments
        ]
        
        logger.info(f"Orchestrator initialized: OCR={enable_ocr}, STT={self.enable_stt}")
    
    def process_request(
        self,
        session_id: str,
        user_input: str,
        user_language: Optional[str] = None,
        audio_data: Optional[bytes] = None,
        document_data: Optional[bytes] = None
    ) -> Dict:
        """
        Main entry point - processes a user request through the entire pipeline
        
        Args:
            session_id: Unique session identifier
            user_input: Text input (or will be generated from audio if STT enabled)
            user_language: User's preferred language
            audio_data: Optional audio data for STT
            document_data: Optional document/image for OCR
        
        Returns:
            Complete response with all pipeline results
        """
        context = self._get_or_create_context(session_id)
        context.user_input = user_input
        context.metadata["user_language"] = user_language
        context.metadata["has_audio"] = audio_data is not None
        context.metadata["has_document"] = document_data is not None
        
        logger.info(f"Processing request for session {session_id}: {user_input[:50]}...")
        
        try:
            if self.enable_stt and audio_data:
                context = self._run_stt(context, audio_data)
            
            context = self._run_normalization(context)
            
            context = self._run_nlu(context)
            
            context = self._run_rules_engine(context)
            
            if self.enable_ocr and document_data:
                context = self._run_ocr(context, document_data)
            
            context = self._run_llm(context, user_language)
            
            context = self._run_db_audit(context)
            
            return self._build_response(context)
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}\n{traceback.format_exc()}")
            return self._build_error_response(context, str(e))
    
    def _get_or_create_context(self, session_id: str) -> PipelineContext:
        """Get existing context or create new one"""
        is_new_session = session_id not in self.sessions
        if is_new_session:
            self.sessions[session_id] = PipelineContext(session_id=session_id, user_input="")
            self.sessions[session_id].metadata["is_new_session"] = True
        return self.sessions[session_id]
    
    def _is_new_session(self, context: PipelineContext) -> bool:
        """Check if this is a new session (first message)"""
        history = self.llm_service.get_history(context.session_id, limit=100)
        # New session if no assistant messages yet (or only one user message)
        assistant_messages = [msg for msg in history if msg.role == "assistant"]
        return len(assistant_messages) == 0
    
    def _get_next_question(self, context: PipelineContext) -> Optional[str]:
        """
        Determine the next question to ask based on predefined order
        
        Order:
        1. Greeting (if new session)
        2. Loan amount
        3. Monthly income
        4. Age
        5. Loan tenure
        6. Employment status
        7. Existing debts
        8. Then eligibility analysis
        """
        profile = context.user_profile
        
        # Check if new session - return greeting
        if self._is_new_session(context):
            return "greeting"
        
        # Check each field in order
        if not profile or not profile.loan_amount_requested or profile.loan_amount_requested == 0:
            return "loan amount"
        
        # Check loan type - needed for eligibility calculation
        if not profile or not profile.loan_type:
            return "loan type"
        
        if not profile or not profile.monthly_income or profile.monthly_income == 0:
            return "monthly income"
        
        if not profile or not profile.age or profile.age == 0:
            return "age"
        
        if not profile or not profile.loan_tenure_years or profile.loan_tenure_years == 0:
            return "loan tenure"
        
        # Check employment status - need to know if salaried or not
        # We check if employment_months is set (for salaried employees)
        # For self-employed, we might still need employment_months (business duration)
        # But first check if we have income - if yes, we need employment status
        if profile and profile.monthly_income and profile.monthly_income > 0:
            # Have income - check if we know employment status
            # Check history to see if we've asked about employment status
            history = self.llm_service.get_history(context.session_id, limit=20)
            asked_about_employment = any(
                "salaried" in msg.content.lower() or "self-employed" in msg.content.lower() or "employment" in msg.content.lower()
                for msg in history if msg.role == "assistant"
            )
            if not asked_about_employment:
                return "employment status"
            # If asked but no employment_months, we still need it
            if not profile.employment_months or profile.employment_months == 0:
                return "employment status"  # Ask again or ask for duration
        
        # Check existing debts
        has_existing_debts = (
            (profile.existing_loans_emi and profile.existing_loans_emi > 0) or
            (profile.existing_credit_cards_min_payment and profile.existing_credit_cards_min_payment > 0)
        )
        # We need to explicitly ask if they have existing debts (even if 0, we should confirm)
        # Check if we've asked about this before
        history = self.llm_service.get_history(context.session_id, limit=20)
        asked_about_debts = any(
            "existing" in msg.content.lower() or "loan" in msg.content.lower() or "debt" in msg.content.lower()
            for msg in history if msg.role == "assistant"
        )
        if not asked_about_debts:
            return "existing debts"
        
        # All questions answered - return None to proceed with eligibility
        return None
    
    def _run_stt(self, context: PipelineContext, audio_data: bytes) -> PipelineContext:
        """Stage 1: Speech-to-Text"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.STT, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[STT] Processing audio for session {context.session_id} ({len(audio_data)} bytes)")
            
            if not self.stt_service:
                result.status = ComponentStatus.SKIPPED
                result.data = {"text": context.user_input, "note": "STT service not available"}
                result.confidence = 0.0
                logger.warning("[STT] Service not initialized, skipping")
            else:
                user_lang = context.metadata.get("user_language")
                language_code = None
                if user_lang:
                    from stt_service import get_language_code
                    language_code = get_language_code(user_lang)
                
                transcription = self.stt_service.transcribe_with_fallback(
                    audio_data,
                    language=language_code,
                    max_retries=self.max_retries
                )
                
                if transcription.get("error"):
                    result.status = ComponentStatus.FAILED
                    result.error = transcription.get("error")
                    result.data = {"text": context.user_input, "fallback": True}
                    result.confidence = 0.0
                    logger.error(f"[STT] Transcription failed: {result.error}")
                else:
                    transcribed_text = transcription.get("text", "").strip()
                    detected_lang = transcription.get("language", "unknown")
                    
                    if transcribed_text:
                        result.status = ComponentStatus.SUCCESS
                        result.data = {
                            "text": transcribed_text,
                            "language": detected_lang,
                            "original_length": len(context.user_input)
                        }
                        result.confidence = transcription.get("confidence", 0.9)
                        context.user_input = transcribed_text
                        logger.info(f"[STT] Success: '{transcribed_text[:50]}...' (lang: {detected_lang})")
                    else:
                        result.status = ComponentStatus.FAILED
                        result.error = "Empty transcription result"
                        result.data = {"text": context.user_input, "fallback": True}
                        result.confidence = 0.0
                        logger.warning("[STT] Empty transcription, using original input")
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[STT] Error: {e}\n{traceback.format_exc()}")
            result.data = {"text": context.user_input, "fallback": True}
            result.confidence = 0.0
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.STT] = result
        
        if result.data and "text" in result.data:
            context.user_input = result.data["text"]
        
        return context
    
    def _run_normalization(self, context: PipelineContext) -> PipelineContext:
        """Stage 2: Text Normalization/Transliteration"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.NORMALIZATION, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[NORMALIZATION] Processing text for session {context.session_id}")
            
            from normalization_service import NormalizationService
            
            if not hasattr(self, '_normalization_service'):
                self._normalization_service = NormalizationService()
            
            user_lang = context.metadata.get("user_language")
            
            normalization_result = self._normalization_service.normalize(
                context.user_input,
                language=user_lang
            )
            
            normalized_text = normalization_result['normalized_text']
            changes_made = normalization_result.get('changes_made', [])
            
            result.status = ComponentStatus.SUCCESS
            result.data = {
                "normalized_text": normalized_text,
                "original_text": normalization_result['original_text'],
                "changes_made": changes_made
            }
            result.confidence = normalization_result.get('confidence', 1.0)
            context.user_input = normalized_text
            
            if changes_made:
                logger.info(f"[NORMALIZATION] Applied changes: {', '.join(changes_made)}")
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[NORMALIZATION] Error: {e}\n{traceback.format_exc()}")
            context.user_input = context.user_input.strip()
            result.data = {"normalized_text": context.user_input, "fallback": True}
            result.confidence = 0.5
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.NORMALIZATION] = result
        return context
    
    def _run_nlu(self, context: PipelineContext) -> PipelineContext:
        """Stage 3: Natural Language Understanding (Intent + Slot Extraction)"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.NLU, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[NLU] Extracting data for session {context.session_id}")
            
            from api_endpoint import extract_financial_data
            
            existing_profile = context.user_profile
            logger.info(f"[NLU] Calling extract_financial_data with profile: income={existing_profile.monthly_income if existing_profile else 'None'}, employment={existing_profile.employment_months if existing_profile else 'None'}")
            extraction_result = extract_financial_data(context.user_input, existing_profile)
            logger.info(f"[NLU] Extraction returned: {extraction_result}")
            
            extracted = extraction_result.get("extracted", {})
            missing = extraction_result.get("missing", [])
            intent = extraction_result.get("intent", "provide_info")
            
            logger.info(f"[NLU] Extraction result - extracted: {extracted}, missing: {missing}")
            
            context.extracted_data = extracted
            context.metadata["intent"] = intent
            
            if extracted:
                logger.info(f"[NLU] Extracted data: {extracted}")
                if context.user_profile is None:
                    loan_type = extracted.get("loan_type")
                    context.user_profile = UserFinancialProfile(
                        monthly_income=extracted.get("monthly_income", 0),
                        age=extracted.get("age", 0),
                        employment_months=extracted.get("employment_months", 0),
                        existing_loans_emi=extracted.get("existing_loans_emi", 0.0),
                        existing_credit_cards_min_payment=extracted.get("existing_credit_cards_min_payment", 0.0),
                        loan_amount_requested=extracted.get("loan_amount_requested", 0),
                        loan_tenure_years=extracted.get("loan_tenure_years", 0),
                        loan_type=loan_type  # This should be a LoanType enum or None
                    )
                else:
                    logger.info(f"[NLU] Updating existing profile. Extracted keys: {list(extracted.keys())}")
                    for key, value in extracted.items():
                        logger.info(f"[NLU] Processing key: {key}, value: {value}, type: {type(value)}")
                        if hasattr(context.user_profile, key):
                            logger.info(f"[NLU] Profile has attribute {key}")
                            if key == "loan_type" and value:
                                context.user_profile.loan_type = value
                            elif key == "loan_tenure_years":
                                if value and isinstance(value, (int, float)) and value > 0:
                                    context.user_profile.loan_tenure_years = int(value)
                            elif key == "employment_months":
                                if value and isinstance(value, (int, float)) and value > 0:
                                    old_value = context.user_profile.employment_months
                                    context.user_profile.employment_months = int(value)
                                    logger.info(f"[NLU] Updated employment_months: {old_value} -> {context.user_profile.employment_months}")
                            else:
                                setattr(context.user_profile, key, value)
            
            result.status = ComponentStatus.SUCCESS
            result.data = {
                "extracted": extracted,
                "missing": missing,
                "intent": intent
            }
            result.confidence = 1.0 if extracted else 0.5  # Higher confidence if we extracted something
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[NLU] Error: {e}")
            result.data = {"extracted": {}, "missing": []}
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.NLU] = result
        return context
    
    def _run_rules_engine(self, context: PipelineContext) -> PipelineContext:
        """Stage 4: Rules Engine (Eligibility Calculation)"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.RULES, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[RULES] Calculating eligibility for session {context.session_id}")
            
            if context.user_profile:
                has_income = context.user_profile.monthly_income and context.user_profile.monthly_income > 0
                has_age = context.user_profile.age and context.user_profile.age > 0
                has_loan_type = bool(context.user_profile.loan_type)
                
                if has_income and has_age and has_loan_type:
                    eligibility_result = check_eligibility(context.user_profile)
                    context.eligibility_result = eligibility_result
                    
                    result.status = ComponentStatus.SUCCESS
                    result.data = {
                        "is_eligible": eligibility_result.is_eligible,
                        "eligible_amount": eligibility_result.eligible_amount,
                        "suggested_emi": eligibility_result.suggested_emi,
                        "dti_ratio": eligibility_result.dti_ratio
                    }
                    result.confidence = 1.0  # Rules are deterministic
                else:
                    result.status = ComponentStatus.SKIPPED
                    missing_fields = []
                    if not has_income:
                        missing_fields.append("monthly income")
                    if not has_age:
                        missing_fields.append("age")
                    if not has_loan_type:
                        missing_fields.append("loan type")
                    result.data = {"reason": "Insufficient data for eligibility check", "missing": missing_fields}
                    result.confidence = 0.0
            else:
                result.status = ComponentStatus.SKIPPED
                result.data = {"reason": "No user profile available for eligibility check"}
                result.confidence = 0.0
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[RULES] Error: {e}")
            result.data = {}
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.RULES] = result
        return context
    
    def _run_ocr(self, context: PipelineContext, document_data: bytes) -> PipelineContext:
        """Stage 5: OCR (Document Processing)"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.OCR, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[OCR] Processing document for session {context.session_id}")
            
            result.status = ComponentStatus.SKIPPED
            result.data = {"text": "", "note": "OCR not implemented yet"}
            result.confidence = 0.0
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[OCR] Error: {e}")
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.OCR] = result
        return context
    
    def _run_llm(self, context: PipelineContext, user_language: Optional[str]) -> PipelineContext:
        """Stage 6: LLM (Generate Response)"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.LLM, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[LLM] Generating response for session {context.session_id}")
            
            history = self.llm_service.get_history(context.session_id, limit=10)
            self.llm_service.add_to_history(context.session_id, "user", context.user_input)
            history = self.llm_service.get_history(context.session_id, limit=10)
            context.conversation_history = history
            
            # Check if we have eligibility result - if yes, explain it
            # Determine next question in the sequence
            next_question = self._get_next_question(context)
            if next_question:
                # We still need to ask questions; don't explain old eligibility results
                context.eligibility_result = None
            
            if context.eligibility_result:
                eligibility = context.eligibility_result
                profile_tenure = context.user_profile.loan_tenure_years if context.user_profile else 0
                if profile_tenure and isinstance(profile_tenure, (int, float)) and profile_tenure > 0:
                    tenure_years = int(profile_tenure)
                    tenure_was_provided = True
                else:
                    tenure_years = eligibility.max_tenure_years if eligibility.max_tenure_years > 0 else 5
                    tenure_was_provided = False
                
                eligibility_context = EligibilityContext(
                    is_eligible=eligibility.is_eligible,
                    eligible_amount=eligibility.eligible_amount,
                    requested_amount=context.user_profile.loan_amount_requested if context.user_profile else 0,
                    suggested_emi=eligibility.suggested_emi,
                    tenure_years=tenure_years,
                    loan_type=context.user_profile.loan_type.value if context.user_profile and context.user_profile.loan_type else "unknown",
                    dti_ratio=eligibility.dti_ratio,
                    rejection_reasons=eligibility.rejection_reasons,
                    warnings=getattr(eligibility, "warnings", []),
                    user_profile={
                        "monthly_income": context.user_profile.monthly_income if context.user_profile else 0,
                        "age": context.user_profile.age if context.user_profile else 0,
                        "employment_months": context.user_profile.employment_months if context.user_profile else 0
                    }
                )
                
                eligibility_context.tenure_was_provided = tenure_was_provided
                
                lang = user_language or self.llm_service.detect_language(context.user_input)
                response = self.llm_service.explain_eligibility(
                    eligibility_context,
                    lang,
                    context.session_id
                )
            else:
                # Use sequential question flow (we already computed next_question above)
                lang = user_language or self.llm_service.detect_language(context.user_input)
                
                if next_question == "greeting":
                    response = self.llm_service.ask_greeting(lang, context.session_id)
                elif next_question == "loan amount":
                    response = self.llm_service.ask_clarification("loan amount", history, lang, context.session_id)
                elif next_question == "loan type":
                    response = self.llm_service.ask_clarification("loan type", history, lang, context.session_id)
                elif next_question == "monthly income":
                    response = self.llm_service.ask_clarification("monthly income", history, lang, context.session_id)
                elif next_question == "age":
                    response = self.llm_service.ask_clarification("age", history, lang, context.session_id)
                elif next_question == "loan tenure":
                    response = self.llm_service.ask_clarification("loan tenure", history, lang, context.session_id)
                elif next_question == "employment status":
                    # Check if we already have income - if yes, ask about employment duration
                    if context.user_profile and context.user_profile.monthly_income > 0:
                        # We have income, so ask about employment duration
                        response = self.llm_service.ask_clarification("employment duration", history, lang, context.session_id)
                    else:
                        # Ask about employment status first
                        response = self.llm_service.ask_about_employment_status(history, lang, context.session_id)
                elif next_question == "existing debts":
                    response = self.llm_service.ask_about_existing_debts(history, lang, context.session_id)
                elif next_question is None:
                    # All questions answered - output submission message only
                    # Do NOT calculate or explain eligibility - that's backend processing
                    response = "Thank you. Your information has been submitted for backend processing."
                    
                    # Still calculate eligibility in background for internal use, but don't show it to user
                    if context.user_profile and context.user_profile.loan_type:
                        eligibility_result = check_eligibility(context.user_profile)
                        context.eligibility_result = eligibility_result
                else:
                    # Fallback - ask for the missing field
                    response = self.llm_service.ask_clarification(next_question, history, lang, context.session_id)
            
            result.status = ComponentStatus.SUCCESS
            result.data = {"response": response}
            result.confidence = 0.9  # LLM confidence
            context.metadata["llm_response"] = response
            
            self.llm_service.add_to_history(context.session_id, "assistant", response)
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[LLM] Error: {e}")
            result.data = {"response": "I apologize, but I'm having trouble processing your request. Please try again."}
            result.confidence = 0.0
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.LLM] = result
        return context
    
    def _run_db_audit(self, context: PipelineContext) -> PipelineContext:
        """Stage 7: Database/Audit Logging"""
        start_time = time.time()
        result = ComponentResult(component=PipelineStage.DB, status=ComponentStatus.PENDING)
        
        try:
            result.status = ComponentStatus.RUNNING
            logger.info(f"[DB] Auditing session {context.session_id}")
            
            total_time = time.time() - context.start_time
            logger.info(f"Session {context.session_id} completed in {total_time:.2f}s")
            
            result.status = ComponentStatus.SUCCESS
            result.data = {
                "session_id": context.session_id,
                "timestamp": datetime.now().isoformat(),
                "total_time": total_time,
                "components_executed": len([r for r in context.component_results.values() if r.status == ComponentStatus.SUCCESS])
            }
            result.confidence = 1.0
            
        except Exception as e:
            result.status = ComponentStatus.FAILED
            result.error = str(e)
            logger.error(f"[DB] Error: {e}")
        
        result.execution_time = time.time() - start_time
        context.component_results[PipelineStage.DB] = result
        return context
    
    def _build_response(self, context: PipelineContext) -> Dict:
        """Build final response from pipeline context"""
        llm_result = context.component_results.get(PipelineStage.LLM)
        response_text = llm_result.data.get("response", "No response generated") if llm_result else "Error generating response"
        
        # Get missing info from NLU stage
        missing_info = []
        nlu_result = context.component_results.get(PipelineStage.NLU)
        if nlu_result and nlu_result.data:
            missing_info = nlu_result.data.get("missing", [])
        
        # Build eligibility result with full details
        eligibility_result = None
        if context.eligibility_result:
            eligibility_result = {
                "is_eligible": context.eligibility_result.is_eligible,
                "eligible_amount": context.eligibility_result.eligible_amount,
                "suggested_emi": context.eligibility_result.suggested_emi,
                "dti_ratio": context.eligibility_result.dti_ratio,
                "rejection_reasons": context.eligibility_result.rejection_reasons,
                "max_tenure_years": getattr(context.eligibility_result, "max_tenure_years", None)
            }
        
        return {
            "response": response_text,
            "session_id": context.session_id,
            "extracted_data": context.extracted_data,
            "eligibility_result": eligibility_result,
            "missing_info": missing_info,
            "pipeline_status": {
                stage.value: {
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "confidence": result.confidence,
                    "error": result.error
                }
                for stage, result in context.component_results.items()
            },
            "metadata": context.metadata
        }
    
    def _build_error_response(self, context: PipelineContext, error: str) -> Dict:
        """Build error response"""
        return {
            "response": f"I apologize, but I encountered an error: {error}. Please try again.",
            "session_id": context.session_id,
            "error": error,
            "pipeline_status": {
                stage.value: {
                    "status": result.status.value,
                    "error": result.error
                }
                for stage, result in context.component_results.items()
            }
        }



def main():
    """Main function for terminal interaction"""
    print("=" * 60)
    print("🤖 Multilingual AI Loan Advisor - Orchestrated Pipeline")
    print("=" * 60)
    print("\nThis bot coordinates:")
    print("  • STT (Speech-to-Text)")
    print("  • NLU (Intent + Slot Extraction)")
    print("  • Rules Engine (Eligibility Calculation)")
    print("  • OCR (Document Processing)")
    print("  • LLM (Conversation & Explanations)")
    print("  • DB (Audit & Logging)")
    print("\nType 'exit' or 'quit' to end the conversation")
    print("=" * 60)
    print()
    
    try:
        orchestrator = Orchestrator(
            enable_ocr=False,  # Set to True when OCR is implemented
            enable_stt=False   # Set to True when STT is implemented
        )
    except Exception as e:
        print(f"❌ Error initializing orchestrator: {e}")
        return
    
    session_id = "terminal_session"
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n👋 Goodbye! Have a great day!")
                break
            
            print("\n🔄 Processing through pipeline...")
            response = orchestrator.process_request(
                session_id=session_id,
                user_input=user_input,
                user_language=None  # Auto-detect
            )
            
            print(f"\n🤖 Assistant: {response['response']}")
            
            if "--debug" in user_input.lower():
                print("\n📊 Pipeline Status:")
                for stage, status in response.get("pipeline_status", {}).items():
                    print(f"  {stage}: {status['status']} ({status.get('execution_time', 0):.3f}s)")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.exception("Terminal error")


if __name__ == "__main__":
    main()

