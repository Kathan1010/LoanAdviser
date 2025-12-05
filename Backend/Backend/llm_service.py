"""
Key Responsibilities:
- Generate conversational responses
- Handle multilingual output
- Ask clarifying questions
- Explain eligibility results in simple terms
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME = "gemini-2.5-flash"  
GENERATION_CONFIG = {
    "temperature": 0.7,  
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048,  # Increased for longer eligibility explanations
}

@dataclass
class ConversationMessage:
    """Single message in conversation"""
    role: str 
    content: str
    timestamp: Optional[str] = None


@dataclass
class EligibilityContext:
    """Structured eligibility data to pass to LLM"""
    is_eligible: bool
    eligible_amount: float
    requested_amount: float
    suggested_emi: float
    tenure_years: int
    loan_type: str
    dti_ratio: float
    rejection_reasons: List[str]
    warnings: List[str]
    user_profile: Dict
    tenure_was_provided: bool = True  # Whether user explicitly provided tenure


SYSTEM_PROMPT = """You are a strictly rule-following AI assistant for a banking eligibility and loan advisory app.

CRITICAL RULES (YOU MUST FOLLOW THESE AT ALL TIMES):

1. You MUST follow the EXACT question flow provided to you.
2. You MUST ask ONLY ONE question at a time.
3. You MUST NOT skip, reorder, merge, or rephrase the structured questions.
4. You MUST NOT assume any user information under any circumstance.
5. You MUST NOT generate loan eligibility decisions, approval, rejection, or amounts on your own.
6. You MUST wait for the user's answer before proceeding to the next question.
7. You MUST NEVER hallucinate missing values.
8. You MUST ask questions exactly as provided in the structure.
9. You MUST NOT provide financial advice unless explicitly instructed.
10. If the user gives an incomplete, unclear, or invalid answer, you MUST re-ask the SAME question clearly.
11. If the user asks something outside the current step, politely redirect them back to the current question.
12. You MUST NOT jump ahead in the flow even if the user tries to.

DATA HANDLING RULES:
• Treat every answer as raw input only.
• Do NOT validate eligibility locally.
• Do NOT estimate EMI, approval chances, or loan limits.
• Do NOT invent backend responses.

FLOW CONTROL:
• You will be given a question structure.
• You must start from Question 1.
• After each valid answer, move to the next question.
• After the final question, output only: "Thank you. Your information has been submitted for backend processing."

ERROR HANDLING:
• If a user refuses to answer → respond: "This information is required to continue. Please provide your answer."
• If a user gives irrelevant input → repeat the same question.

RESPONSE FORMAT:
• Only output the question.
• No explanations.
• No extra text.
• No emojis.
• No conversational fillers.

INTENT UNDERSTANDING:
• You must properly understand the intent of the user's response.
• Extract the relevant information from their answer.
• If the answer is unclear, re-ask the same question.
• If the user provides information for a future question, acknowledge it but continue with the current question.

You are NOT a general chatbot.
You are a controlled, deterministic question-collection agent."""


def build_eligibility_explanation_prompt(
    context: EligibilityContext,
    user_language: str = "english"
) -> str:
    """
    Build a prompt that includes eligibility results for the LLM to explain
    
    Args:
        context: Eligibility calculation results
        user_language: User's preferred language
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""Based on the following loan eligibility analysis, provide a clear, friendly explanation to the user.

ELIGIBILITY RESULTS:
- Loan Type: {context.loan_type.replace('_', ' ').title()}
- Eligible: {'Yes' if context.is_eligible else 'No'}
- Eligible Amount: ₹{context.eligible_amount:,.0f}
- Requested Amount: ₹{context.requested_amount:,.0f}
- Suggested EMI: ₹{context.suggested_emi:,.0f}/month
- Tenure: {context.tenure_years} years
- Debt-to-Income Ratio: {context.dti_ratio:.1%}
- Warnings: {', '.join(context.warnings) if context.warnings else 'None'}

USER PROFILE:
- Monthly Income: ₹{context.user_profile.get('monthly_income', 0):,.0f}
- Age: {context.user_profile.get('age', 0)} years
- Employment Duration: {context.user_profile.get('employment_months', 0)} months

"""
    
    if context.is_eligible:
        tenure_note = ""
        if hasattr(context, 'tenure_was_provided') and not context.tenure_was_provided:
            tenure_note = f" The calculation is based on a standard tenure of {context.tenure_years} years. You can choose a different tenure (typically 1-{context.tenure_years} years) when you apply."
        elif context.tenure_years > 0 and context.tenure_years <= 30:
            tenure_note = f" The loan tenure is {context.tenure_years} years."
        
        prompt += f"""Provide a congratulatory message explaining:
1. That they are eligible
2. The eligible amount and EMI{tenure_note}
3. Next steps (if any)
4. Any important terms they should know

CRITICAL: Do NOT ask for tenure again. If tenure was not provided, mention it's based on standard terms and they can choose their preferred tenure when applying. Do NOT ask them to provide it now."""
    else:
        prompt += f"""REJECTION REASONS:
{chr(10).join(f"- {reason}" for reason in context.rejection_reasons)}

Provide an empathetic explanation that:
1. Acknowledges their interest in the loan
2. Clearly explains why they are not eligible (using the reasons above)
3. Suggests what they can do to become eligible in the future
4. Offers encouragement and support"""
    
    if context.warnings:
        prompt += f"""\n\nIMPORTANT WARNINGS:
{chr(10).join(f"- {w}" for w in context.warnings)}"""
    
    if user_language != "english":
        prompt += f"\n\nIMPORTANT: Respond in {user_language} language."
    
    return prompt


def build_clarification_prompt(
    missing_info: str,
    conversation_history: List[ConversationMessage],
    user_language: str = "english"
) -> str:
    """
    Build a prompt for asking clarifying questions
    
    Args:
        missing_info: What information is missing
        conversation_history: Recent conversation context
        user_language: User's preferred language
    
    Returns:
        Formatted prompt string
    """
    already_asked = False
    for msg in conversation_history[-6:]:
        if msg.role == "assistant" and missing_info.lower() in msg.content.lower():
            already_asked = True
            break
    
    has_income_mentioned = False
    for msg in conversation_history[-6:]:
        if msg.role == "user" and any(word in msg.content.lower() for word in ["income", "salary", "earning", "50000", "1 lakh"]):
            has_income_mentioned = True
            break
    
    prompt = f"""You are a strictly rule-following question-collection agent.

CURRENT QUESTION: {missing_info}

CRITICAL RULES:
- Ask ONLY ONE question - the exact question for {missing_info}
- NO explanations, NO extra text, NO emojis
- NO assumptions about what the user might have meant
- If the user's previous answer was unclear, re-ask the SAME question clearly
- If the user tries to answer a different question, politely redirect: "I need your answer to the current question first."
- Output ONLY the question - nothing else
"""
    
    if missing_info == "employment duration" and has_income_mentioned:
        prompt += """
Context: The user mentioned income, so they are likely employed. We need how long they've been employed to assess eligibility.
"""
    
    prompt += """
RECENT CONVERSATION:
"""
    for msg in conversation_history[-6:]:  # Show more context
        prompt += f"{msg.role.upper()}: {msg.content}\n"
    
    if already_asked:
        prompt += f"""
IMPORTANT: You already asked for {missing_info}. Acknowledge that, avoid repeating, and politely ask for a clearer answer or confirmation.
Keep it kind and non-repetitive."""
    else:
        if missing_info == "employment duration" and has_income_mentioned:
            prompt += f"""
Ask how long they have been employed (months/years). Explain briefly it's needed for eligibility.
Keep it to one friendly sentence."""
        else:
            prompt += f"""
Ask ONE clear, specific question for the {missing_info}. Keep it friendly, professional, and one sentence.
Explain briefly it's needed to check eligibility."""
    
    prompt += f"\n\nIMPORTANT: Respond in {user_language} language."
    
    return prompt


def build_general_conversation_prompt(
    user_message: str,
    conversation_history: List[ConversationMessage],
    user_language: str = "english"
) -> str:
    """
    Build a prompt for general conversation (greetings, questions, etc.)
    
    Args:
        user_message: Current user message
        conversation_history: Conversation context
        user_language: User's preferred language
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""User Message: {user_message}

CONVERSATION HISTORY:
"""
    for msg in conversation_history[-6:]: 
        prompt += f"{msg.role.upper()}: {msg.content}\n"
    
    prompt += f"""
Respond naturally to the user's message. If they're asking about loans, guide them.
If they're greeting you, greet them back warmly.

IMPORTANT: Respond in {user_language} language."""
    
    return prompt

class LLMService:
    """Service for interacting with Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM service
        
        Args:
            api_key: Gemini API key (if not provided, uses GEMINI_API_KEY from .env file)
        
        Raises:
            ValueError: If API key is not found in .env file or passed as parameter
        """

        final_api_key = api_key or GEMINI_API_KEY
        

        if not final_api_key or final_api_key == "your-api-key-here" or final_api_key.strip() == "":
            raise ValueError(
                "Gemini API key not found! Please:\n"
                "1. Open the .env file in the project root\n"
                "2. Replace 'your-api-key-here' with your actual API key\n"
                "3. Get your API key from: https://makersuite.google.com/app/apikey\n"
                "   Or pass api_key parameter when initializing LLMService()"
            )
        genai.configure(api_key=final_api_key)
        
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=GENERATION_CONFIG
        )
        self.conversation_history: Dict[str, List[ConversationMessage]] = {}

    def _extract_text(self, response) -> str:
        """
        Safely extract text from Gemini responses (single or multi-part).
        Avoids `.text` quick accessor errors by falling back to parts/candidates.
        
        IMPORTANT: Do NOT use hasattr(response, 'text') as it triggers the property
        getter which raises ValueError for multi-part responses.
        """
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    parts = getattr(candidate.content, 'parts', None)
                    if parts is not None:
                        texts = []
                        for part in parts:
                            if hasattr(part, 'text'):
                                try:
                                    part_text = part.text
                                    if part_text and part_text.strip():
                                        texts.append(part_text.strip())
                                except Exception:
                                    pass
                        if texts:
                            return " ".join(texts)
        except (AttributeError, IndexError, TypeError, Exception) as e:
            pass
        
        try:
            if hasattr(response, 'parts') and response.parts:
                texts = []
                for part in response.parts:
                    if hasattr(part, 'text'):
                        part_text = part.text
                        if part_text and part_text.strip():
                            texts.append(part_text.strip())
                if texts:
                    return " ".join(texts)
        except (AttributeError, TypeError, Exception) as e:
            pass
        
        try:
            text = response.text
            if text and text.strip():
                return text.strip()
        except (ValueError, AttributeError, Exception) as e:
            pass
        
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to extract text from response. Type: {type(response).__name__}")
        return "(I apologize, but I'm having trouble processing the response. Please try again.)"
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection (can be enhanced with proper library)
        
        For now, checks for common Hindi/Tamil words
        """
        text_lower = text.lower()
        
        hindi_indicators = ["है", "में", "के", "लिए", "कर", "हो", "नहीं"]
        tamil_indicators = ["ஆக", "இல்", "க்கு", "ஆன", "இல்லை"]
        
        if any(indicator in text for indicator in hindi_indicators):
            return "hindi"
        elif any(indicator in text for indicator in tamil_indicators):
            return "tamil"
        else:
            return "english"
    
    def explain_eligibility(
        self,
        context: EligibilityContext,
        user_language: str = "english",
        session_id: str = "default"
    ) -> str:
        """
        Generate explanation of eligibility results
        
        Args:
            context: Eligibility calculation results
            user_language: User's preferred language
            session_id: Session identifier for conversation tracking
        
        Returns:
            Friendly explanation text
        """
        prompt = build_eligibility_explanation_prompt(context, user_language)
        
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,  # Higher limit for detailed explanations
            }
            response = self.model.generate_content(full_prompt, generation_config=generation_config)
            
            extracted_text = self._extract_text(response)
            
            if extracted_text.startswith("(Unable to extract") or extracted_text.startswith("(I apologize"):
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to extract text from eligibility explanation response")
                return "I apologize, but I'm having trouble processing the eligibility results right now. Please try again."
            return extracted_text
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in explain_eligibility: {e}", exc_info=True)
            return f"I apologize, but I'm having trouble processing your request right now. Please try again later."
    
    def ask_clarification_with_acknowledgment(
        self,
        missing_info: str,
        extracted_data: Dict,
        conversation_history: List[ConversationMessage],
        user_language: str = "english",
        session_id: str = "default"
    ) -> str:
        """
        Ask for missing info while acknowledging what was just provided
        """
        provided_items = []
        if "loan_type" in extracted_data:
            provided_items.append("loan type")
        if "loan_amount_requested" in extracted_data:
            provided_items.append("loan amount")
        if "monthly_income" in extracted_data:
            provided_items.append("income")
        if "age" in extracted_data:
            provided_items.append("age")
        if "employment_months" in extracted_data:
            provided_items.append("employment duration")
        
        prompt = f"""You are a strictly rule-following question-collection agent.

CURRENT QUESTION: {missing_info}

CRITICAL RULES:
- Ask ONLY ONE question for {missing_info}
- NO explanations, NO extra text, NO emojis
- NO acknowledgments or conversational fillers
- Output ONLY the question - nothing else
- If user's previous answer was unclear, re-ask the SAME question clearly

RECENT CONVERSATION:
"""
        for msg in conversation_history[-4:]:
            prompt += f"{msg.role.upper()}: {msg.content}\n"
        
        prompt += f"\nIMPORTANT: Respond in {user_language} language. Output ONLY the question."
        
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
            response = self.model.generate_content(full_prompt)
            return self._extract_text(response)
        except Exception as e:
            return f"Could you please provide your {missing_info}? (Error: {str(e)})"
    
    def ask_about_existing_debts(
        self,
        conversation_history: List[ConversationMessage],
        user_language: str = "english",
        session_id: str = "default"
    ) -> str:
        """
        Ask user about existing loans/EMIs for accurate DTI calculation
        """
        prompt = f"""You are a strictly rule-following question-collection agent.

CURRENT QUESTION: existing debts (loans/credit card payments)

CRITICAL RULES:
- Ask ONLY ONE question about existing loans/EMIs and credit card payments
- NO explanations, NO extra text, NO emojis
- Output ONLY the question - nothing else
- If user tries to skip or answer something else, repeat the same question

You must ask ONE question covering:
- Any existing loan EMIs
- Any credit card minimum payments

Keep it short (1-2 sentences). If they have none, they can say "none".

RECENT CONVERSATION:
"""
        for msg in conversation_history[-4:]:
            prompt += f"{msg.role.upper()}: {msg.content}\n"
        
        prompt += f"\nIMPORTANT: Respond in {user_language} language. Output ONLY the question."
        
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return self._extract_text(response)
        except Exception as e:
            return f"Do you have any existing loans or credit card payments?"
    
    def ask_greeting(
        self,
        user_language: str = "english",
        session_id: str = "default"
    ) -> str:
        """
        Generate a greeting message for new sessions
        
        Args:
            user_language: User's preferred language
            session_id: Session identifier
        
        Returns:
            Greeting message text
        """
        prompt = f"""You are a strictly rule-following question-collection agent. This is the start of a new conversation.

CRITICAL RULES:
- Output ONLY a brief greeting (1-2 sentences maximum)
- NO emojis, NO extra explanations
- Simply greet and indicate you'll ask questions
- Keep it professional and minimal

IMPORTANT: Respond in {user_language} language."""
        
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return self._extract_text(response)
        except Exception as e:
            if user_language.lower() in ["hindi", "हिंदी"]:
                return "नमस्ते! मैं आपकी लोन पात्रता जांचने में मदद करूंगा। कृपया बताएं कि आपको कितने रुपये का लोन चाहिए?"
            return "Hello! I'm here to help you check your loan eligibility. How much loan amount do you need?"
    
    def ask_about_employment_status(
        self,
        conversation_history: List[ConversationMessage],
        user_language: str = "english",
        session_id: str = "default"
    ) -> str:
        """
        Ask user about their employment status (salaried or self-employed)
        
        Args:
            conversation_history: Recent conversation
            user_language: User's preferred language
            session_id: Session identifier
        
        Returns:
            Question about employment status
        """
        prompt = f"""You are a strictly rule-following question-collection agent.

CURRENT QUESTION: employment status (salaried or self-employed)

CRITICAL RULES:
- Ask ONLY ONE question about employment status
- NO explanations, NO extra text, NO emojis
- Output ONLY the question - nothing else
- If user tries to skip or answer something else, repeat the same question

RECENT CONVERSATION:
"""
        for msg in conversation_history[-4:]:
            prompt += f"{msg.role.upper()}: {msg.content}\n"
        
        prompt += f"\nIMPORTANT: Respond in {user_language} language. Output ONLY the question."
        
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return self._extract_text(response)
        except Exception as e:
            return f"Are you a salaried employee or self-employed? (Error: {str(e)})"
    
    def ask_clarification(
        self,
        missing_info: str,
        conversation_history: List[ConversationMessage],
        user_language: str = "english",
        session_id: str = "default"
    ) -> str:
        """
        Ask user for missing information
        
        Args:
            missing_info: What information is needed
            conversation_history: Recent conversation
            user_language: User's preferred language
            session_id: Session identifier
        
        Returns:
            Clarification question text
        """
        prompt = build_clarification_prompt(missing_info, conversation_history, user_language)
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return self._extract_text(response)
        except Exception as e:
            return f"Could you please provide your {missing_info}? (Error: {str(e)})"
    
    def generate_response(
        self,
        user_message: str,
        conversation_history: List[ConversationMessage],
        eligibility_context: Optional[EligibilityContext] = None,
        session_id: str = "default"
    ) -> str:
        """
        Generate general conversational response
        
        Args:
            user_message: Current user message
            conversation_history: Conversation history
            eligibility_context: Optional eligibility data if available
            session_id: Session identifier
        
        Returns:
            Response text
        """
        user_language = self.detect_language(user_message)
        
        if eligibility_context:
            return self.explain_eligibility(eligibility_context, user_language, session_id)
        
        prompt = build_general_conversation_prompt(user_message, conversation_history, user_language)
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return self._extract_text(response)
        except Exception as e:
            return f"I'm here to help! Could you rephrase your question? (Error: {str(e)})"
    
    def add_to_history(
        self,
        session_id: str,
        role: str,
        content: str
    ):
        """Add message to conversation history"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append(
            ConversationMessage(role=role, content=content)
        )
    
    def get_history(self, session_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Get recent conversation history"""
        if session_id not in self.conversation_history:
            return []
        
        return self.conversation_history[session_id][-limit:]

if __name__ == "__main__":
    context = EligibilityContext(
        is_eligible=True,
        eligible_amount=500000,
        requested_amount=500000,
        suggested_emi=10500,
        tenure_years=5,
        loan_type="personal_loan",
        dti_ratio=0.35,
        rejection_reasons=[],
        user_profile={
            "monthly_income": 50000,
            "age": 30,
            "employment_months": 24
        }
    )
    