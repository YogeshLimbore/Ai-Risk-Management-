# AI Risk Insights SystemFor a free-cloud learning deployment, follow [DEPLOYMENT.md](DEPLOYMENT.md).

Learning deployment: Streamlit collects customer inputs and calls FastAPI. FastAPI validates inputs, serves a packaged Random Forest, and calls Ollama for optional general commentary. Training runs separately.

## Local setup

Use Python 3.13. The pinned versions match the environment used to verify the bundled model. Install and run from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
# In another terminal:
python -m streamlit run app/streamlit_app.py
```

Set environment variables in your shell; `.env.example` documents the defaults. Local Python processes do not automatically load `.env`. Docker Compose reads `.env` for interpolation.

- `API_URL`: Streamlit backend URL, default `http://localhost:8000`.
- `API_TIMEOUT`: UI request timeout in seconds, default 30. Keep above the Ollama timeout.
- `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`: default `http://localhost:11434`, `llama3.2`, 20 seconds.
- `MODEL_DIR`: trusted artifact directory containing `risk_model.pkl` and `model_features.pkl`.
- `API_KEY`: optional local-demo key; set a strong secret before shared access. Streamlit sends it server-side as `X-API-Key`.
- `MAX_REQUESTS_PER_MINUTE`: per-process global prediction limit, default 60.
- `MAX_CONCURRENT_PREDICTIONS`: per-process inference concurrency, default 4.

`POST /predict` accepts age, income, loan_amount, credit_score, num_previous_defaults, employment_years. It returns prediction, uncalibrated default_probability, risk_level, commentary, explanation_fallback, explanation_type, probability_calibrated and model_version. `/health` returns 503 unless artifacts load and pass schema and inference checks. `/metrics` exposes Prometheus request counts, latency histograms and explanation fallback counts, with API-key protection when configured.

The model and feature list load once per process during startup. An unavailable model leaves the service unready; restart after repairing artifacts. Ollama errors and empty responses produce clean rule-based commentary without internal exception text.

## Input assumptions

Age 18�100; credit score 300�900; previous defaults 0�10; employment 0�50 years and no more than age minus 18 (assumed working age). Income and loan amount must be finite and non-negative, capped at 1 trillion as a numerical safety bound. These are demo assumptions, not validated lending policy. Numeric strings, booleans and unknown fields are rejected. Financial units must match training data.

## Docker

```powershell
Copy-Item .env.example .env
# Edit API_KEY and other settings in .env.
docker compose up --build -d
docker compose exec ollama ollama pull llama3.2
```

Open http://localhost:8501. API and UI ports bind to loopback. Ollama is internal and its downloaded models persist in a named volume. Predictions work with fallback commentary while Ollama is unavailable or its model has not been pulled. Only the API image contains the Random Forest artifacts. The UI image installs only UI requirements. Docker builds install pinned direct dependencies; transitive dependencies are not fully locked yet.

## Training and model releases

```powershell
python -m pip install -r requirements-training.txt
python -m src.train_model
```

Each run creates a unique `models/releases/<UTC timestamp>/` directory with model, features and metadata: dataset SHA-256, artifact hash, Python and ML library versions, training parameters, split settings, evaluation metrics and Brier score. Seed and split are fixed for repeatability. Existing serving artifacts are preserved. Review evaluation before promoting a release; point `MODEL_DIR` at it locally, or deliberately copy approved artifacts into `models/` for a new image. Keep previous releases for rollback. The bundled legacy artifact has a content-derived version but its original training provenance is unavailable. Load only trusted pickle artifacts.

## Before public hosting

Put both UI and API behind an authenticated HTTPS reverse proxy or identity-aware gateway. Provision certificates and secrets through the hosting platform; do not expose Ollama. The optional API key protects backend calls, but UI user authentication must be configured at the gateway. Enforce shared request/body limits at the gateway for multiple replicas; built-in limits are per process. Configure trusted forwarded headers explicitly for the chosen proxy.

Request logs contain generated request IDs, route, status, latency and model version, without customer bodies. Errors log only event and exception type. Disable hosting-layer body logging. Scrape `/metrics` with authentication and alert on failures, latency and fallback rate. Select thresholds using deployment traffic.

## Model limitations

Explanations are general risk commentary based on customer details and rules, not verified reasons behind the Random Forest prediction. Model scores are uncalibrated; Brier score alone does not establish calibration. Validate reliability diagrams and calibration on representative held-out data before interpreting scores as default likelihoods. Actual lending use requires stronger data validation, fairness assessment, governance and qualified human review. This project is a learning demo.
`UI_PORT` selects the Docker UI host port (default 8501). Use 8502 if a local Streamlit process already occupies 8501.
