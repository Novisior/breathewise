"""Small text helpers."""
import re

# Split after . ! ? or the Hindi danda (।) when followed by whitespace.
# Requiring whitespace keeps "PM2.5" in one piece.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")


def trim_sentences(text: str, max_sentences: int = 2) -> str:
    """Keep only the first `max_sentences` sentences of `text`."""
    text = " ".join(str(text).split())
    return " ".join(_SENTENCE_SPLIT.split(text)[:max_sentences])
