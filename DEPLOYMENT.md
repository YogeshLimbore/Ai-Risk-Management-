# Free cloud learning deployment

## Enable Groq commentary (current provider)

Set these variables in Render Environment, then save and redeploy:

```text
EXPLANATION_PROVIDER=groq
GROQ_API_KEY=<your Groq key, pasted only in Render>
GROQ_MODEL=openai/gpt-oss-120b
GROQ_TIMEOUT=20
```

Groq and xAI Grok are separate services. A Groq key cannot authenticate to xAI.
Keep the existing backend `API_KEY` unchanged. If a Groq key was stored under
`XAI_API_KEY`, move its value to `GROQ_API_KEY`; never commit it. Requests go to
`https://api.groq.com/openai/v1/chat/completions`. The response identifies `groq`
when generation succeeds and `fallback` on failure. Free-tier limits and any
paid usage depend on the Groq account. Customer inputs are sent to Groq; use
synthetic profiles for this learning app.

## Enable xAI Grok commentary

In Render → risk-insights-api → Environment, add:

```text
EXPLANATION_PROVIDER=grok
XAI_API_KEY=<paste your key directly into Render>
XAI_MODEL=grok-4.3
XAI_TIMEOUT=20
```

Save and redeploy. Keep `API_KEY` (the UI-to-backend credential) unchanged;
`XAI_API_KEY` is a separate provider secret and belongs only in Render.
Do not place either key in source code or send it in chat.
The xAI request uses `reasoning_effort=none` and a 500-token output limit.
Provider failures, missing keys and empty responses use rule-based commentary.
The response field `explanation_provider` identifies `grok` versus `fallback`.
Switch `EXPLANATION_PROVIDER=fallback` to stop external LLM calls.

Grok API calls incur xAI usage charges and transmit submitted customer values
to xAI. Use synthetic inputs for this demo and configure a provider spending
limit. Hosting remains on the existing free tiers. Generated commentary is
still not validated Random Forest attribution.

## Deployed learning environment

- UI: https://mmij9cbffgs6e4dards5wm.streamlit.app/
- API readiness: https://risk-insights-api.onrender.com/health
- GitHub: https://github.com/YogeshLimbore/Ai-Risk-Management-
- Branch: `main`; UI entrypoint: `app/streamlit_app.py`; Python: 3.13.
- API runs on Render Free; UI runs on Streamlit Community Cloud.
- The API key is stored in Render environment variables and Streamlit encrypted
  secrets, not this repository.

Verified an end-to-end hosted prediction with the default synthetic profile:
No Default, uncalibrated score 26%, Low Risk, rule-based commentary.

Browser → Streamlit Community Cloud → HTTPS → Render FastAPI.
Cloud predictions use rule-based commentary; Ollama remains local.

## GitHub

Create an empty private repository called `ai-risk-insights-system`.
Do not initialize it with a README or .gitignore. From the project directory:

```powershell
git init -b main
git add .
git status --short
git commit -m "Prepare demo for free cloud deployment"
git remote add origin https://github.com/YOUR_USERNAME/ai-risk-insights-system.git
git push -u origin main
```

Review staged files first. Include model artifacts, but exclude `.env`,
`.streamlit/secrets.toml`, `venv/` and ZIP archives. Sign in through Git's browser
prompt if needed; never paste credentials into chat.

## Render API

Sign in to Render, select **New → Blueprint**, connect this repository, and select
`render.yaml`. Review that the compute plan is **Free** before deploying.
The blueprint installs API-only dependencies, starts Uvicorn on `$PORT`, uses
`/health`, disables Ollama and generates an API key.

Wait for **Live**, then visit `https://YOUR-SERVICE.onrender.com/health`.
It should return `status: ready`. Copy the service URL. Transfer the generated
API key from Render's Environment settings directly into Streamlit secrets.

## Streamlit UI

Sign in to Streamlit Community Cloud using GitHub. Choose **Create app** and select
your repository, branch `main`, and main file `app/streamlit_app.py`.
In Advanced settings choose Python **3.13** and enter these secrets:

```toml
API_URL = "https://YOUR-SERVICE.onrender.com"
API_KEY = "YOUR_RENDER_API_KEY"
API_TIMEOUT = "120"
```

Root-level secrets become environment variables. `app/requirements.txt` provides
the UI dependencies. Keep the UI private for the initial learning deployment.

## Verify and update

Open the Streamlit URL and click **Predict Risk** using the default synthetic
values. Expect a prediction, uncalibrated score and rule-based commentary.
Fallback status is expected with Ollama disabled. Check Render logs for HTTP 200
on `/predict`. Invalid inputs should return 422; a missing API key should return 401.

Render's free service sleeps after 15 minutes without traffic and can take about
a minute to wake up. The UI timeout accommodates this. If the first request fails,
wait for `/health` to become ready, then retry.

For updates: edit locally, run `python -m unittest discover -s tests -v`, commit,
push, inspect deployment logs, then repeat the live prediction check. Training is
separate; promote a reviewed model deliberately. Review free-tier quotas and keep
paid upgrades disabled for this exercise.

Official guides:
- https://render.com/docs/deploy-fastapi
- https://render.com/docs/free
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
