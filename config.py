from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT: Path = Path(__file__).resolve().parent
SRC_DIR: Path = PROJECT_ROOT / "src"
DATA_DIR: Path = PROJECT_ROOT / "data"
OUTPUT_DIR: Path = Path(
    os.getenv("ANKI_OUTPUT_DIR", str(PROJECT_ROOT / "outputs"))
).expanduser()
FREQUENCY_WORDS_PATH: Path = DATA_DIR / "frequency_words.json"

DICTIONARY_API_BASE_URL: str = "https://api.dictionaryapi.dev/api/v2/entries/en"
DICTIONARY_API_TIMEOUT_SECONDS: float = 10.0
DEFAULT_LANGUAGE_MODEL: str = "en_core_web_sm"
DEFAULT_MIN_WORD_LENGTH: int = 4
DEFAULT_MAX_WORDS: int = 30


def ensure_runtime_directories() -> None:

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

