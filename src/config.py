import os
import math
from pathlib import Path
from dataclasses import dataclass, field
ROOT = Path(__file__).resolve().parents[1]
@dataclass
class Settings:
    model_dir: Path = field(default_factory=lambda: Path(os.getenv("MODEL_DIR", str(ROOT / "models"))))
    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"))
    ollama_enabled: bool = field(default_factory=lambda: os.getenv("OLLAMA_ENABLED", "true").lower() in {"true", "1", "yes"})
    ollama_timeout: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT", "20")))
    api_key: str = field(default_factory=lambda: os.getenv("API_KEY", ""))
    explanation_provider: str = field(default_factory=lambda: os.getenv("EXPLANATION_PROVIDER", "ollama").lower())
    xai_api_key: str = field(default_factory=lambda: os.getenv("XAI_API_KEY", ""), repr=False)
    xai_model: str = field(default_factory=lambda: os.getenv("XAI_MODEL", "grok-4.3"))
    xai_timeout: float = field(default_factory=lambda: float(os.getenv("XAI_TIMEOUT", "20")))
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""), repr=False)
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
    groq_timeout: float = field(default_factory=lambda: float(os.getenv("GROQ_TIMEOUT", "20")))
    def __post_init__(self):
        if self.explanation_provider not in {"ollama", "grok", "groq", "fallback"}:
            raise ValueError("Unknown EXPLANATION_PROVIDER")
        if not math.isfinite(self.groq_timeout) or self.groq_timeout <= 0:
            raise ValueError("GROQ_TIMEOUT must be finite and positive")
        if not math.isfinite(self.xai_timeout) or self.xai_timeout <= 0:
            raise ValueError("XAI_TIMEOUT must be finite and positive")
        if not math.isfinite(self.ollama_timeout) or self.ollama_timeout <= 0:
            raise ValueError("OLLAMA_TIMEOUT must be finite and positive")
