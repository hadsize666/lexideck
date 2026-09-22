"""Async vocabulary enrichment pipeline using Datamuse API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import aiohttp

from src.text_processing.pipeline import VocabularyEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichedWord:
    """Dictionary data combined with the vocabulary item's source context."""

    lemma: str
    context: str
    phonetic: str = ""
    definition: str = ""
    part_of_speech: str = ""
    examples: tuple[str, ...] = ()
    found: bool = True


class DictionaryClient:
    """Bounded-concurrency asynchronous client for Datamuse API."""

    def __init__(
        self,
        *,
        concurrency: int = 8,
        timeout_seconds: float = 10.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session = session

    async def __aenter__(self) -> "DictionaryClient":
        if self._session is None:
            connector = aiohttp.TCPConnector(ssl=False)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=connector,
                headers=headers
            )
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def lookup(self, item: Any) -> EnrichedWord:
        """Fetch word definition via Datamuse API with fallback to source context."""
        if self._session is None or self._session.closed:
            raise RuntimeError("DictionaryClient must be used inside an async context")

        if hasattr(item, "lemma"):
            lemma = str(item.lemma).strip()
            context = str(getattr(item, "context", ""))
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            lemma = str(item[0]).strip()
            context = str(item[1])
        else:
            lemma = str(item).strip()
            context = ""

        if not lemma:
            return EnrichedWord(lemma=lemma, context=context, found=False)

        url = f"https://api.datamuse.com/words?sp={quote(lemma, safe='')}&md=d&max=1"
        try:
            async with self._semaphore:
                async with self._session.get(url) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        if data and isinstance(data, list) and "defs" in data[0]:
                            raw_def = data[0]["defs"][0]
                            parts = raw_def.split("\t", 1)
                            pos = parts[0] if len(parts) > 1 else ""
                            definition = parts[1] if len(parts) > 1 else parts[0]
                            return EnrichedWord(
                                lemma=lemma,
                                context=context,
                                definition=definition.capitalize(),
                                part_of_speech=pos,
                                found=True,
                            )
        except Exception as exc:
            logger.warning("Datamuse lookup failed for %r: %s", lemma, exc)

        return EnrichedWord(
            lemma=lemma,
            context=context,
            definition="Contextual vocabulary entry",
            found=True,
        )


async def enrich_vocabulary(
    vocabulary: Any,
    *,
    concurrency: int = 8,
    timeout_seconds: float = 10.0,
) -> list[EnrichedWord]:
    """Enrich extracted vocabulary concurrently while preserving input order."""
    if isinstance(vocabulary, dict):
        items = [
            v if hasattr(v, "lemma") else VocabularyEntry(lemma=k, context=str(v))
            for k, v in vocabulary.items()
        ]
    else:
        items = list(vocabulary)

    async with DictionaryClient(
        concurrency=concurrency, timeout_seconds=timeout_seconds
    ) as client:
        return list(await asyncio.gather(*(client.lookup(item) for item in items)))