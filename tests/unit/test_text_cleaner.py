"""Tests for TextCleaner."""

from app.rag.cleaners.text_cleaner import TextCleaner


def test_text_cleaner_compacts_and_removes_noise():
    """Cleaner removes standalone boilerplate and keeps body text."""
    cleaned = TextCleaner().clean("Accept cookies\n\n正文 content\n\nFooter")

    assert cleaned == "正文 content"
