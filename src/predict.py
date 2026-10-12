"""Prediction service, instantiated once per API process."""
import hashlib
import joblib
import pandas as pd
from src.explain_risk import get_risk_level, explain_customer_risk_with_ollama, generate_fallback_explanation
from src.explain_risk import explain_customer_risk_with_grok
FEATURES = ["age", "income", "loan_amount", "credit_score", "num_previous_defaults", "employment_years"]
class PredictionService:
    def __init__(self, settings):
        self.settings = settings
        model_path = settings.model_dir / "risk_model.pkl"
        self.model = joblib.load(model_path)
        self.features = list(joblib.load(settings.model_dir / "model_features.pkl"))
        if self.features != FEATURES or list(self.model.classes_) != [0, 1]:
            raise ValueError("Incompatible model schema or classes")
        if list(self.model.feature_names_in_) != self.features:
            raise ValueError("Model features do not match artifact")
        self.version = hashlib.sha256(model_path.read_bytes()).hexdigest()[:16]
        self.model.predict_proba(pd.DataFrame([[29, 42000, 30000, 580, 1, 1]], columns=self.features))
    def predict(self, customer_data):
        frame = pd.DataFrame([customer_data], columns=self.features)
        probability = float(self.model.predict_proba(frame)[0][1])
        provider = self.settings.explanation_provider
        if provider == "grok":
            explanation, fallback = explain_customer_risk_with_grok(customer_data, probability, self.settings)
        elif provider == "ollama" and self.settings.ollama_enabled:
            explanation, fallback = explain_customer_risk_with_ollama(customer_data, probability,
                self.settings.ollama_model, self.settings.ollama_host, self.settings.ollama_timeout)
        else:
            explanation, fallback = generate_fallback_explanation(customer_data, probability), True
        return {"prediction": int(self.model.predict(frame)[0]),
            "default_probability": round(probability, 4), "risk_level": get_risk_level(probability),
            "explanation": explanation, "explanation_fallback": fallback,
            "explanation_provider": "fallback" if fallback else provider,
            "explanation_type": "general_risk_commentary", "probability_calibrated": False,
            "model_version": self.version}
