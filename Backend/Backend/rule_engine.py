"""
Rule-Based Loan Eligibility Engine

This module handles all deterministic loan calculations and eligibility checks.

Key Functions:
- EMI calculation
- DTI (Debt-to-Income) ratio
- Eligibility checks
- Loan type specific rules
"""

import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class LoanType(str, Enum):
    """Supported loan types"""
    PERSONAL = "personal_loan"
    HOME = "home_loan"
    CAR = "car_loan"
    EDUCATION = "education_loan"
    BUSINESS = "business_loan"


@dataclass
class UserFinancialProfile:
    """Structured user financial information"""
    monthly_income: float
    age: int
    employment_months: int
    existing_loans_emi: float = 0.0
    existing_credit_cards_min_payment: float = 0.0
    loan_amount_requested: float = 0.0
    loan_tenure_years: int = 0
    loan_type: Optional[LoanType] = None

@dataclass
class EligibilityResult:
    """Result of eligibility check"""
    is_eligible: bool
    eligible_amount: float
    max_tenure_years: int
    suggested_emi: float
    dti_ratio: float
    rejection_reasons: list[str]
    warnings: list[str]
    approval_message: str

LOAN_RULES = {
    LoanType.PERSONAL: {
        "min_income": 15000,
        "min_age": 21,
        "max_age": 65,
        "max_dti": 0.4,  
        "min_employment_months": 6,
        "max_loan_multiplier": 20, 
        "interest_rate": 10.5,  
        "min_tenure_years": 1,
        "max_tenure_years": 5
    },
    LoanType.HOME: {
        "min_income": 25000,
        "min_age": 21,
        "max_age": 70,
        "max_dti": 0.5, 
        "min_employment_months": 12,
        "max_loan_multiplier": 60,  
        "interest_rate": 8.5,
        "min_tenure_years": 5,
        "max_tenure_years": 30
    },
    LoanType.CAR: {
        "min_income": 20000,
        "min_age": 21,
        "max_age": 65,
        "max_dti": 0.45,
        "min_employment_months": 6,
        "max_loan_multiplier": 10,  
        "interest_rate": 9.0,
        "min_tenure_years": 1,
        "max_tenure_years": 7
    },
    LoanType.EDUCATION: {
        "min_income": 0,  
        "min_age": 18,
        "max_age": 35,
        "max_dti": 0.4,
        "min_employment_months": 0,
        "max_loan_multiplier": 15,
        "interest_rate": 8.0,
        "min_tenure_years": 1,
        "max_tenure_years": 15
    },
    LoanType.BUSINESS: {
        "min_income": 100000,
        "min_age": 18,
        "max_age": 60,
        "max_dti": 0.4,
        "min_employment_months": 12,  
        "max_loan_multiplier": 30,  
        "interest_rate": 12.0, 
        "min_tenure_years": 1,
        "max_tenure_years": 10
    }
}


def calculate_emi(principal: float, annual_rate: float, tenure_years: int) -> float:
    """
    Calculate Equated Monthly Installment (EMI)
    
    Formula: EMI = [P × R × (1+R)^N] / [(1+R)^N - 1]
    Where:
        P = Principal (loan amount)
        R = Monthly interest rate (annual_rate / 12 / 100)
        N = Number of monthly installments (tenure_years * 12)
    
    Args:
        principal: Loan amount
        annual_rate: Annual interest rate (e.g., 10.5 for 10.5%)
        tenure_years: Loan tenure in years
    
    Returns:
        Monthly EMI amount
    """
    if principal <= 0 or tenure_years <= 0:
        return 0.0
    monthly_rate = annual_rate / 12 / 100
    num_months = tenure_years * 12
    if monthly_rate == 0:
        return principal / num_months
    
    emi = (principal * monthly_rate * (1 + monthly_rate) ** num_months) / \
          ((1 + monthly_rate) ** num_months - 1)
    
    return round(emi, 3)


def calculate_dti_ratio(
    monthly_income: float,
    existing_loans_emi: float,
    existing_credit_cards_min_payment: float,
    new_loan_emi: float
) -> float:
    """
    Calculate Debt-to-Income (DTI) ratio
    
    DTI = (All monthly debt payments) / Monthly income
    
    Args:
        monthly_income: User's monthly income
        existing_loans_emi: Existing loan EMIs
        existing_credit_cards_min_payment: Credit card minimum payments
        new_loan_emi: Proposed new loan EMI
    
    Returns:
        DTI ratio (0.0 to 1.0+)
    """
    if monthly_income <= 0:
        return 999.0 
    
    total_debt = existing_loans_emi + existing_credit_cards_min_payment + new_loan_emi
    dti = total_debt / monthly_income
    
    return round(dti, 3)


def calculate_max_eligible_amount(
    monthly_income: float,
    annual_rate: float,
    max_dti: float,
    existing_debt: float,
    tenure_years: int
) -> float:
    """
    Calculate maximum loan amount user is eligible for based on DTI
    
    We reverse-engineer the EMI formula to find max principal
    
    Args:
        monthly_income: User's monthly income
        annual_rate: Interest rate
        max_dti: Maximum allowed DTI ratio
        existing_debt: Existing monthly debt payments
        tenure_years: Desired tenure
    
    Returns:
        Maximum eligible loan amount
    """
    max_total_debt = monthly_income * max_dti
    available_for_new_loan = max_total_debt - existing_debt
    
    if available_for_new_loan <= 0:
        return 0.0
    monthly_rate = annual_rate / 12 / 100
    num_months = tenure_years * 12
    
    if monthly_rate == 0:
        return available_for_new_loan * num_months
    principal = available_for_new_loan * \
                ((1 + monthly_rate) ** num_months - 1) / \
                (monthly_rate * (1 + monthly_rate) ** num_months)
    
    return round(principal, 3)

def check_eligibility(profile: UserFinancialProfile) -> EligibilityResult:
    """
    Main eligibility check function
    This runs through all rules and returns a comprehensive result.
    Args:
        profile: User's financial profile
    Returns:
        EligibilityResult with all details
    """
    if not profile.loan_type:
        return EligibilityResult(
            is_eligible=False,
            eligible_amount=0.0,
            max_tenure_years=0,
            suggested_emi=0.0,
            dti_ratio=0.0,
            rejection_reasons=["Loan type not specified"],
            approval_message=""
        )
    
    rules = LOAN_RULES[profile.loan_type]
    rejection_reasons: list[str] = []
    warnings: list[str] = []
    
    if profile.monthly_income <= 0:
        rejection_reasons.append("Monthly income must be greater than 0.")
    elif profile.monthly_income < rules["min_income"]:
        rejection_reasons.append(
            f"Minimum income required: ₹{rules['min_income']:,.0f}/month. "
            f"Your income: ₹{profile.monthly_income:,.0f}/month"
        )
    
    if profile.age < rules["min_age"]:
        rejection_reasons.append(
            f"Minimum age required: {rules['min_age']} years. "
            f"Your age: {profile.age} years"
        )
    elif profile.age > rules["max_age"]:
        rejection_reasons.append(
            f"Maximum age allowed: {rules['max_age']} years. "
            f"Your age: {profile.age} years"
        )
    
    if profile.employment_months < rules["min_employment_months"]:
        rejection_reasons.append(
            f"Minimum employment duration: {rules['min_employment_months']} months. "
            f"Your employment: {profile.employment_months} months"
        )
    
    existing_debt = profile.existing_loans_emi + profile.existing_credit_cards_min_payment
    
    max_by_income = profile.monthly_income * rules["max_loan_multiplier"]
    
    tenure = int(profile.loan_tenure_years) if profile.loan_tenure_years and isinstance(profile.loan_tenure_years, (int, float)) and profile.loan_tenure_years > 0 else rules["max_tenure_years"]
    max_by_dti = calculate_max_eligible_amount(
        profile.monthly_income,
        rules["interest_rate"],
        rules["max_dti"],
        existing_debt,
        tenure
    )
    
    eligible_amount = min(max_by_income, max_by_dti)
    
    loan_amount = profile.loan_amount_requested
    if isinstance(loan_amount, (int, float)) and loan_amount > 0:
        if loan_amount > eligible_amount:
            warnings.append(
                f"Requested amount ₹{loan_amount:,.0f} exceeds eligible amount "
                f"₹{eligible_amount:,.0f}. Capped to eligible amount."
            )
        else:
            eligible_amount = loan_amount
    
    if eligible_amount > 0 and tenure > 0:
        proposed_emi = calculate_emi(eligible_amount, rules["interest_rate"], tenure)
        dti = calculate_dti_ratio(
            profile.monthly_income,
            profile.existing_loans_emi,
            profile.existing_credit_cards_min_payment,
            proposed_emi
        )
        
        if dti > rules["max_dti"]:
            rejection_reasons.append(
                f"Debt-to-Income ratio {dti:.1%} exceeds maximum allowed {rules['max_dti']:.1%}"
            )
    else:
        proposed_emi = 0.0
        dti = calculate_dti_ratio(
            profile.monthly_income,
            profile.existing_loans_emi,
            profile.existing_credit_cards_min_payment,
            0.0
        )
    
    if profile.loan_tenure_years and isinstance(profile.loan_tenure_years, (int, float)) and profile.loan_tenure_years > 0:
        tenure_years = int(profile.loan_tenure_years)
        if tenure_years < rules["min_tenure_years"]:
            rejection_reasons.append(
                f"Minimum tenure: {rules['min_tenure_years']} years"
            )
        elif tenure_years > rules["max_tenure_years"]:
            rejection_reasons.append(
                f"Maximum tenure: {rules['max_tenure_years']} years"
            )
    
    is_eligible = len(rejection_reasons) == 0 and eligible_amount > 0
    
    if is_eligible:
        approval_message = (
            f"Congratulations! You are eligible for a {profile.loan_type.value.replace('_', ' ').title()} "
            f"of ₹{eligible_amount:,.0f} with EMI of ₹{proposed_emi:,.0f}/month "
            f"for {tenure} years at {rules['interest_rate']}% interest rate."
        )
        if warnings:
            approval_message += " Note: " + " ".join(warnings)
    else:
        approval_message = ""
    
    return EligibilityResult(
        is_eligible=is_eligible,
        eligible_amount=eligible_amount,
        max_tenure_years=rules["max_tenure_years"],
        suggested_emi=proposed_emi,
        dti_ratio=dti,
        rejection_reasons=rejection_reasons,
        warnings=warnings,
        approval_message=approval_message
    )

def format_currency(amount: float) -> str:
    """Format amount as Indian currency"""
    return f"₹{amount:,.0f}"


def get_loan_summary(profile: UserFinancialProfile, result: EligibilityResult) -> Dict:
    """
    Generate a summary dictionary for LLM to use
    
    This structured data will be passed to the LLM for generating responses.
    """
    return {
        "loan_type": profile.loan_type.value if profile.loan_type else "unknown",
        "is_eligible": result.is_eligible,
        "eligible_amount": result.eligible_amount,
        "requested_amount": profile.loan_amount_requested,
        "suggested_emi": result.suggested_emi,
        "tenure_years": int(profile.loan_tenure_years) if profile.loan_tenure_years and isinstance(profile.loan_tenure_years, (int, float)) and profile.loan_tenure_years > 0 else result.max_tenure_years,
        "dti_ratio": result.dti_ratio,
        "rejection_reasons": result.rejection_reasons,
        "user_profile": {
            "monthly_income": profile.monthly_income,
            "age": profile.age,
            "employment_months": profile.employment_months
        }
    }

if __name__ == "__main__":
    profile1 = UserFinancialProfile(
        monthly_income=50000,
        age=30,
        employment_months=24,
        existing_loans_emi=5000,
        existing_credit_cards_min_payment=2000,
        loan_amount_requested=500000,
        loan_tenure_years=5,
        loan_type=LoanType.PERSONAL
    )
    
    result1 = check_eligibility(profile1)
    print("Example 1 - Eligible User:")
    print(f"Eligible: {result1.is_eligible}")
    print(f"Eligible Amount: ₹{result1.eligible_amount:,.0f}")
    print(f"EMI: ₹{result1.suggested_emi:,.0f}")
    print(f"DTI: {result1.dti_ratio:.1%}")
    print(f"Reasons: {result1.rejection_reasons}")
    print()
    
    profile2 = UserFinancialProfile(
        monthly_income=10000,
        age=25,
        employment_months=12,
        loan_amount_requested=200000,
        loan_tenure_years=3,
        loan_type=LoanType.PERSONAL
    )

    result2 = check_eligibility(profile2)
    print("Example 2 - Ineligible User:")
    print(f"Eligible: {result2.is_eligible}")
    print(f"Reasons: {result2.rejection_reasons}")
    print()