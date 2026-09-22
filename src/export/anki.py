from __future__ import annotations

import html
import logging
import re
import tempfile
from pathlib import Path
from typing import Iterable

import genanki

from src.enrichment.client import EnrichedWord

logger = logging.getLogger(__name__)

_MODEL_ID = 1_948_253_761
_DECK_ID = 1_948_253_762
_TEMPLATE = """
<div class="word">{{Word}}</div>
<div class="context">{{Context}}</div>
<hr id="answer">
<div class="phonetic">{{Phonetic}}</div>
<div class="definition">{{Definition}}</div>
<div class="pos">{{PartOfSpeech}}</div>
{{#Example}}<div class="example"><strong>Example</strong><br>{{Example}}</div>{{/Example}}
"""
_CSS = """
.card { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 20px; color: #222; background: #fff; text-align: left;
  max-width: 720px; margin: 0 auto; line-height: 1.55; }
.word { font-size: 34px; font-weight: 700; color: #173f35; margin-bottom: 18px; }
.context { font-size: 21px; color: #343a40; }
.context mark { color: #173f35; background: #d8efe5; padding: 0 2px; }
.phonetic { font-size: 19px; color: #606b67; margin: 12px 0; }
.definition { font-size: 22px; }
.pos { display: inline-block; margin-top: 10px; font-size: 15px; color: #755c21; }
.example { border-left: 3px solid #9bc7b0; margin-top: 18px; padding-left: 12px;
  color: #4d5752; font-size: 18px; }
"""
_HIGHLIGHT = re.compile(r"(?<![\w])(?P<word>WORD)(?![\w])", re.IGNORECASE)


def _escaped_context(context: str, word: str) -> str:

    escaped = html.escape(context, quote=True)
    escaped_word = html.escape(word, quote=True)
    pattern = re.compile(
        rf"(?<![\w])({re.escape(escaped_word)})(?![\w])", re.IGNORECASE
    )
    return pattern.sub(r"<mark>\1</mark>", escaped)


def create_anki_deck(
    words: Iterable[EnrichedWord],
    *,
    deck_name: str = "LexiDeck Vocabulary",
    output_dir: str | Path | None = None,
) -> Path:

    entries = list(words)
    if not entries:
        raise ValueError("Cannot create an Anki deck without vocabulary entries")
    if not deck_name.strip():
        raise ValueError("deck_name cannot be empty")

    target_dir = Path(output_dir) if output_dir is not None else Path(tempfile.gettempdir())
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", deck_name.strip()).strip("._")
    if not safe_name:
        safe_name = "vocabulary"
    destination = target_dir / f"{safe_name}.apkg"

    model = genanki.Model(
        _MODEL_ID,
        "LexiDeck Vocabulary",
        fields=[
            {"name": "Word"}, {"name": "Context"}, {"name": "Phonetic"},
            {"name": "Definition"}, {"name": "PartOfSpeech"}, {"name": "Example"},
        ],
        templates=[
            {
                "name": "Vocabulary",
                "qfmt": '<div class="word">{{Word}}</div><div class="context">{{Context}}</div>',
                "afmt": _TEMPLATE,
            }
        ],
        css=_CSS,
    )
    deck = genanki.Deck(_DECK_ID, deck_name.strip())
    seen: set[str] = set()
    for entry in entries:
        word = entry.lemma.strip()
        if not word or word.casefold() in seen:
            continue
        seen.add(word.casefold())
        example = entry.examples[0] if entry.examples else ""
        note = genanki.Note(
            model=model,
            fields=[
                html.escape(word, quote=True),
                _escaped_context(entry.context, word),
                html.escape(entry.phonetic, quote=True),
                html.escape(entry.definition, quote=True),
                html.escape(entry.part_of_speech, quote=True),
                html.escape(example, quote=True),
            ],
        )
        deck.add_note(note)
    if not seen:
        raise ValueError("No non-empty vocabulary words were provided")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{safe_name}-", suffix=".apkg.tmp", dir=target_dir, delete=False
        ) as temporary:
            temp_path = Path(temporary.name)
        genanki.Package(deck).write_to_file(str(temp_path))
        temp_path.replace(destination)
        return destination
    except Exception:
        logger.exception("Unable to create Anki package")
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise RuntimeError("Failed to build the Anki package") from None

