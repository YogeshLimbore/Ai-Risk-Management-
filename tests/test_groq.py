import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.api import create_app
from src.config import Settings

CUSTOMER = dict(age=29, income=42000.0, loan_amount=30000.0,
                credit_score=580, num_previous_defaults=1, employment_years=1.0)


class GroqTests(unittest.TestCase):
    def test_success_and_configuration(self):
        response = httpx.Response(200, json={"choices": [{"message": {"content": "General commentary"}}]},
                                  request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"))
        settings = Settings(explanation_provider="groq", groq_api_key="test-secret", groq_timeout=7)
        with TestClient(create_app(settings)) as client:
            with patch("src.explain_risk.ProviderClient") as provider:
                call = provider.return_value.__enter__.return_value.post
                call.return_value = response
                result = client.post("/predict", json=CUSTOMER).json()
                self.assertEqual(result["explanation_provider"], "groq")
                self.assertFalse(result["explanation_fallback"])
                args = call.call_args
                self.assertEqual(args.args[0], "https://api.groq.com/openai/v1/chat/completions")
                self.assertEqual(args.kwargs["headers"]["Authorization"], "Bearer test-secret")
                self.assertEqual(args.kwargs["json"]["max_completion_tokens"], 1024)

    def test_failures_are_clean(self):
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        cases = [httpx.ReadTimeout("private-secret"),
                 httpx.Response(401, json={"error": "private-secret"}, request=request),
                 httpx.Response(429, json={"error": "private-secret"}, request=request),
                 httpx.Response(500, json={"error": "private-secret"}, request=request),
                 httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}, request=request),
                 httpx.Response(200, json={}, request=request)]
        with TestClient(create_app(Settings(explanation_provider="groq", groq_api_key="test-secret"))) as client:
            for outcome in cases:
                with self.subTest(outcome=type(outcome).__name__):
                    with patch("src.explain_risk.ProviderClient") as provider:
                        call = provider.return_value.__enter__.return_value.post
                        call.side_effect = outcome if isinstance(outcome, Exception) else None
                        call.return_value = outcome
                        response = client.post("/predict", json=CUSTOMER)
                        self.assertEqual(response.status_code, 200)
                        self.assertTrue(response.json()["explanation_fallback"])
                        self.assertNotIn("private-secret", response.text)

    def test_missing_key_does_not_call_provider(self):
        with TestClient(create_app(Settings(explanation_provider="groq", groq_api_key=""))) as client:
            with patch("src.explain_risk.ProviderClient") as call:
                self.assertTrue(client.post("/predict", json=CUSTOMER).json()["explanation_fallback"])
                call.assert_not_called()

    def test_secret_not_in_settings_repr(self):
        self.assertNotIn("private-secret", repr(Settings(groq_api_key="private-secret")))


if __name__ == "__main__":
    unittest.main()
