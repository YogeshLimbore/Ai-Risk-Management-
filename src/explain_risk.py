import ollama
from httpx import Client as ProviderClient
import logging
import json
logger = logging.getLogger(__name__)


def explain_customer_risk_with_grok(customer_data, probability, settings):
    """Send commentary requests to xAI, retaining a clean fallback on failures."""
    try:
        if not settings.xai_api_key:
            raise ValueError("Missing xAI configuration")
        with ProviderClient(timeout=settings.xai_timeout, follow_redirects=False) as client:
            response = client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.xai_api_key}"},
                json={"model": settings.xai_model, "stream": False,
                      "reasoning_effort": "none", "max_tokens": 500,
                      "messages": [
                          {"role": "system", "content": "Provide general risk commentary, not verified model attribution. Never claim the score is calibrated. Do not recommend approval, denial, or loan terms; require qualified human review."},
                          {"role": "user", "content": build_risk_prompt(customer_data, probability)}]},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty explanation")
            return content.strip(), False
    except Exception as error:
        # Never log request headers, customer values, or provider response bodies.
        logger.warning(json.dumps({"event": "explanation_failed", "provider": "grok",
                                   "error_type": type(error).__name__}))
        return generate_fallback_explanation(customer_data, probability), True


def get_risk_level(probability: float) -> str:
    """
    Convert default probability into a business-friendly risk level.
    """

    if probability >= 0.70:
        return "High Risk"
    elif probability >= 0.40:
        return "Medium Risk"
    else:
        return "Low Risk"


def build_risk_prompt(customer_data: dict, probability: float) -> str:
    """
    Build a structured prompt for the local Ollama LLM.
    """

    risk_level = get_risk_level(probability)

    prompt = f"""
You are a risk analyst working for a fintech company.

Provide general risk commentary only. These rules are not verified reasons for the model prediction. The score is uncalibrated. Do not recommend approval or rejection; recommend human review.

Important rules:
- Do not use technical machine learning terms.
- Do not mention model internals, algorithms, probability calibration, or feature importance.
- Do not say a weak factor is good.
- A credit score below 600 should always be described as a concern.
- Previous defaults should always be described as a risk factor.
- Explain both positive and negative factors.
- Keep the explanation short, clear, and practical.
- Make sure the explanation matches the final risk level.

Customer details:
- Age: {customer_data["age"]}
- Income: {customer_data["income"]}
- Loan Amount: {customer_data["loan_amount"]}
- Credit Score: {customer_data["credit_score"]}
- Number of Previous Defaults: {customer_data["num_previous_defaults"]}
- Employment Years: {customer_data["employment_years"]}
- Predicted Default Probability: {round(probability * 100, 2)}%
- Final Risk Level: {risk_level}

Return the answer in this exact format:

Risk Level:
<risk level>

Positive Factors:
- <positive factor 1>
- <positive factor 2>

Risk Factors:
- <risk factor 1>
- <risk factor 2>

Business Recommendation:
<short recommendation>
"""

    return prompt


def generate_fallback_explanation(customer_data: dict, probability: float) -> str:
    """
    Generate a rule-based fallback explanation if Ollama is unavailable.
    """

    risk_level = get_risk_level(probability)

    positive_factors = []
    risk_factors = []

    income = customer_data["income"]
    loan_amount = customer_data["loan_amount"]
    credit_score = customer_data["credit_score"]
    previous_defaults = customer_data["num_previous_defaults"]
    employment_years = customer_data["employment_years"]

    debt_to_income_ratio = loan_amount / income if income > 0 else 1

    if debt_to_income_ratio <= 0.5:
        positive_factors.append(
            "The loan amount appears manageable compared to the customer's income."
        )
    else:
        risk_factors.append(
            "The loan amount is high compared to the customer's income, which may create repayment pressure."
        )

    if credit_score >= 700:
        positive_factors.append(
            "The customer has a strong credit score, which indicates better creditworthiness."
        )
    elif credit_score >= 600:
        positive_factors.append(
            "The customer has an acceptable credit score."
        )
    else:
        risk_factors.append(
            "The customer has a credit score below 600, which is a credit risk concern."
        )

    if previous_defaults == 0:
        positive_factors.append(
            "The customer has no previous defaults."
        )
    else:
        risk_factors.append(
            "The customer has previous defaults, which increases the chance of repayment issues."
        )

    if employment_years >= 2:
        positive_factors.append(
            "The customer has a reasonable employment history, which may indicate income stability."
        )
    else:
        risk_factors.append(
            "The customer has a short employment history, which may indicate income instability."
        )

    if not positive_factors:
        positive_factors.append(
            "There are limited positive indicators based on the available customer data."
        )

    if not risk_factors:
        risk_factors.append(
            "No major risk factors were found in the available customer data."
        )

    if risk_level == "High Risk":
        recommendation = (
            "Review the application carefully, consider stricter loan terms, "
            "and request additional verification before approval."
        )
    elif risk_level == "Medium Risk":
        recommendation = (
            "Consider approving with controlled terms, closer repayment monitoring, "
            "or a lower approved loan amount."
        )
    else:
        recommendation = (
            "The customer may be considered for approval, but standard repayment monitoring should continue."
        )

    explanation = f"""
Risk Level:
{risk_level}

Positive Factors:
- {positive_factors[0]}
- {positive_factors[1] if len(positive_factors) > 1 else "No additional strong positive factor identified."}

Risk Factors:
- {risk_factors[0]}
- {risk_factors[1] if len(risk_factors) > 1 else "No additional major risk factor identified."}

Human Review:
This is general rule-based commentary, not verified model reasoning. A qualified reviewer must assess the application.
"""

    return explanation.strip()


def explain_customer_risk_with_ollama(
    customer_data: dict,
    probability: float,
    model_name: str = "llama3.2",
    host: str = "http://localhost:11434",
    timeout: float = 20
) -> str:
    """
    Generate a customer risk explanation using Ollama.
    Falls back to a rule-based explanation if Ollama is unavailable.
    """

    prompt = build_risk_prompt(
        customer_data=customer_data,
        probability=probability
    )

    try:
        response = ollama.Client(host=host, timeout=timeout).chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response["message"]["content"]
        if not content.strip():
            raise ValueError("Empty explanation")
        return content, False

    except Exception as error:
        fallback_explanation = generate_fallback_explanation(
            customer_data=customer_data,
            probability=probability
        )

        logger.warning(json.dumps({"event": "explanation_failed", "error_type": type(error).__name__}))
        return fallback_explanation, True
