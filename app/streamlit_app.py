import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "30"))

st.set_page_config(
    page_title="AI-Powered Risk & Insights System",
    page_icon="📊",
    layout="wide"
)


st.title("AI-Powered Risk & Insights System")
st.write(
    "This application predicts customer loan default risk and generates "
    "business-friendly explanations using a Machine Learning model and Ollama."
)


st.sidebar.header("Customer Input")


age = st.sidebar.number_input(
    "Age",
    min_value=18,
    max_value=100,
    value=29,
    step=1
)

income = st.sidebar.number_input(
    "Annual Income",
    min_value=0.0,
    value=42000.0,
    step=1000.0
)

loan_amount = st.sidebar.number_input(
    "Loan Amount",
    min_value=0.0,
    value=30000.0,
    step=1000.0
)

credit_score = st.sidebar.number_input(
    "Credit Score",
    min_value=300,
    max_value=900,
    value=580,
    step=1
)

num_previous_defaults = st.sidebar.number_input(
    "Number of Previous Defaults",
    min_value=0,
    max_value=10,
    value=1,
    step=1
)

employment_years = st.sidebar.number_input(
    "Employment Years",
    min_value=0.0,
    max_value=float(min(50, age - 18)),
    value=float(min(1, age - 18)),
    step=0.5
)

customer_data = {
    "age": age,
    "income": income,
    "loan_amount": loan_amount,
    "credit_score": credit_score,
    "num_previous_defaults": num_previous_defaults,
    "employment_years": employment_years
}


st.subheader("Customer Profile")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Age", age)
    st.metric("Income", f"${income:,.0f}")

with col2:
    st.metric("Loan Amount", f"${loan_amount:,.0f}")
    st.metric("Credit Score", credit_score)

with col3:
    st.metric("Previous Defaults", num_previous_defaults)
    st.metric("Employment Years", employment_years)


if st.button("Predict Risk"):
    with st.spinner("Predicting risk and generating explanation..."):
        try:
            response = requests.post(f"{API_URL}/predict", json=customer_data,
                headers={"X-API-Key": os.getenv("API_KEY", "")}, timeout=API_TIMEOUT)
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError):
            st.error("Prediction unavailable. Check your inputs or try again later.")
            st.stop()

    st.subheader("Prediction Result")

    prediction = result["prediction"]
    default_probability = result["default_probability"]
    risk_level = result["risk_level"]
    explanation = result["explanation"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Prediction", "Default" if prediction == 1 else "No Default")

    with col2:
        st.metric("Model score (uncalibrated)", f"{default_probability * 100:.2f}%")

    with col3:
        st.metric("Risk Level", risk_level)

    st.subheader("General Risk Commentary")
    st.write(explanation)

    if result["explanation_fallback"]:
        st.info("The explanation service is unavailable. Rule-based commentary is shown.")
    st.caption("Commentary is not verified model reasoning. Human review is required.")


st.markdown("---")
st.caption(
    "Note: This is a case study demo system. It should not be used for real lending decisions without proper validation, governance, and compliance review."
)