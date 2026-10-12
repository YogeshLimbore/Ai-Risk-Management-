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
    def __post_init__(self):
        if not math.isfinite(self.ollama_timeout) or self.ollama_timeout <= 0:
            raise ValueError("OLLAMA_TIMEOUT must be finite and positive")
