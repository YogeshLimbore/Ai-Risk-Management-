import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.api import create_app
from src.config import Settings

CUSTOMER = dict(age=29, income=42000.0, loan_amount=30000.0,
    credit_score=580, num_previous_defaults=1, employment_years=1.0)

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.mock = patch("src.explain_risk.ollama.Client.chat", side_effect=RuntimeError("private-secret"))
        self.mock.start()
        self.client_context = TestClient(create_app(Settings()))
        self.client = self.client_context.__enter__()
    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.mock.stop()
    def test_prediction_and_fallback(self):
        response = self.client.post("/predict", json=CUSTOMER)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn(result["prediction"], [0, 1])
        self.assertTrue(0 <= result["default_probability"] <= 1)
        self.assertTrue(result["explanation_fallback"])
        self.assertNotIn("private-secret", response.text)
        self.assertFalse(result["probability_calibrated"])
        self.assertIn("X-Request-ID", response.headers)
    def test_model_loaded_once(self):
        with patch("src.predict.joblib.load", side_effect=AssertionError("reloaded")):
            for _ in range(2):
                self.assertEqual(self.client.post("/predict", json=CUSTOMER).status_code, 200)
    def test_ready(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
    def test_invalid_inputs(self):
        for key, value in [("age",17),("age",101),("income",-1),("loan_amount",-1),
            ("credit_score",299),("credit_score",901),("num_previous_defaults",-1),
            ("num_previous_defaults",11),("employment_years",12),("age",True),
            ("age","29"),("income",1e13),("unexpected",1)]:
            with self.subTest(key=key, value=value):
                self.assertEqual(self.client.post("/predict", json={**CUSTOMER,key:value}).status_code,422)
        for number in ["NaN", "Infinity", "-Infinity"]:
            import json
            body = json.dumps(CUSTOMER).replace('42000.0', number)
            self.assertEqual(self.client.post("/predict", content=body,
                headers={"Content-Type":"application/json"}).status_code,422)
    def test_successful_ollama(self):
        with patch("src.explain_risk.ollama.Client.chat", return_value={"message":{"content":"General commentary"}}):
            self.assertFalse(self.client.post("/predict",json=CUSTOMER).json()["explanation_fallback"])
    def test_timeout_and_empty_response(self):
        for outcome in [httpx.ReadTimeout("internal"), {"message":{"content":""}}]:
            with patch("src.explain_risk.ollama.Client.chat", side_effect=outcome if isinstance(outcome,Exception) else None,
                return_value=outcome):
                self.assertTrue(self.client.post("/predict",json=CUSTOMER).json()["explanation_fallback"])
    def test_missing_artifacts(self):
        with TemporaryDirectory() as directory:
            with TestClient(create_app(Settings(model_dir=Path(directory)))) as client:
                self.assertEqual(client.get("/health").status_code,503)
                self.assertEqual(client.post("/predict",json=CUSTOMER).status_code,503)
    def test_api_key(self):
        with TestClient(create_app(Settings(api_key="test-key"))) as client:
            self.assertEqual(client.post("/predict",json=CUSTOMER).status_code,401)
            self.assertEqual(client.post("/predict",json=CUSTOMER,headers={"X-API-Key":"test-key"}).status_code,200)
    def test_rate_limit(self):
        with patch.dict("os.environ", {"MAX_REQUESTS_PER_MINUTE":"1"}):
            with TestClient(create_app(Settings())) as client:
                self.assertEqual(client.post("/predict",json=CUSTOMER).status_code,200)
                self.assertEqual(client.post("/predict",json=CUSTOMER).status_code,429)
    def test_corrupt_artifacts(self):
        with TemporaryDirectory() as directory:
            Path(directory, "risk_model.pkl").write_bytes(b"invalid")
            with TestClient(create_app(Settings(model_dir=Path(directory)))) as client:
                self.assertEqual(client.get("/health").status_code,503)

    def test_metrics(self):
        self.assertIn("risk_request_seconds",self.client.get("/metrics").text)

    def test_cloud_mode_skips_ollama(self):
        with TestClient(create_app(Settings(ollama_enabled=False))) as client:
            with patch("src.predict.explain_customer_risk_with_ollama") as explain:
                result = client.post("/predict", json=CUSTOMER)
                self.assertEqual(result.status_code, 200)
                self.assertTrue(result.json()["explanation_fallback"])
                explain.assert_not_called()

if __name__ == "__main__":
    unittest.main()
