FROM python:3.13-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd --create-home appuser

FROM base AS api
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY app/api.py app/api.py
COPY models/ models/
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

FROM base AS ui
COPY requirements-ui.txt .
RUN pip install --no-cache-dir -r requirements-ui.txt
COPY app/streamlit_app.py app/streamlit_app.py
USER appuser
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0"]
