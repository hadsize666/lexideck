from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import spacy
from spacy.language import Language
from spacy.tokens import Doc

import config

logger = logging.getLogger(__name__)
ALLOWED_POS: frozenset[str] = frozenset({"NOUN", "VERB", "ADJ", "ADV"})
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class VocabularyEntry:

    lemma: str
    context: str


def clean_text(text: str) -> str:

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(
        char for char in normalized
        if unicodedata.category(char) not in {"Cc", "Cf"} or char.isspace()
    )
    return _WHITESPACE.sub(" ", normalized).strip()


@lru_cache(maxsize=1)
def _load_nlp() -> Language:

    model_name = config.DEFAULT_LANGUAGE_MODEL
    try:
        return spacy.load(model_name)
    except (OSError, ImportError) as exc:
        raise RuntimeError(
            f"spaCy model {model_name!r} is unavailable. Install it with: "
            f"python -m spacy download {model_name}"
        ) from exc


@lru_cache(maxsize=1)
def _load_frequency_words(path: str) -> frozenset[str]:

    frequency_path = Path(path)
    try:
        with frequency_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except OSError as exc:
        raise RuntimeError(f"Cannot read frequency word list: {frequency_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in frequency word list: {frequency_path}") from exc

    if not isinstance(payload, list) or any(not isinstance(word, str) for word in payload):
        raise ValueError("Frequency word list must be a JSON array of strings")
    return frozenset(word.strip().casefold() for word in payload if word.strip())


def _sentence_contexts(doc: Doc) -> Iterable[tuple[object, str]]:

    for sentence in doc.sents:
        context = sentence.text.strip()
        for token in sentence:
            yield token, context


def extract_vocabulary(text: str) -> dict[str, VocabularyEntry]:

    cleaned = clean_text(text)
    if not cleaned:
        return {}

    nlp = _load_nlp()
    frequent_words = _load_frequency_words(str(config.FREQUENCY_WORDS_PATH))
    try:
        doc = nlp(cleaned)
        results: dict[str, VocabularyEntry] = {}
        for token, context in _sentence_contexts(doc):
            if (
                token.is_space
                or token.is_punct
                or token.like_num
                or token.is_stop
                or token.pos_ not in ALLOWED_POS
            ):
                continue
            lemma = token.lemma_.casefold().strip()
            if not lemma or not any(char.isalpha() for char in lemma):
                continue
            if lemma in frequent_words or lemma in results:
                continue
            results[lemma] = VocabularyEntry(lemma=lemma, context=context)
        return results
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        logger.exception("spaCy failed while extracting vocabulary")
        raise RuntimeError("Unable to process the supplied English text") from exc

