"""Rule-based text cleaner for fetched pages."""

import re

NOISE_PATTERNS = (
    "accept cookies",
    "cookie settings",
    "privacy policy",
    "terms of use",
    "subscribe",
    "sign up",
    "navigation",
    "footer",
)


class TextCleaner:
    """Normalize page text and remove common standalone boilerplate."""

    def clean(self, text: str) -> str:
        """Return cleaned text with compact whitespace."""
        lines = []
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            if self._is_noise(line):
                continue
            lines.append(line)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    @staticmethod
    def _is_noise(line: str) -> bool:
        lower = line.lower()
        if len(lower) <= 40 and any(pattern in lower for pattern in NOISE_PATTERNS):
            return True
        return lower in {"menu", "nav", "home", "footer"}
