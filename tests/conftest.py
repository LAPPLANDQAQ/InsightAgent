"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def fake_llm():
    from tests.fixtures.fake_llm import FakeLLMClient

    return FakeLLMClient()


@pytest.fixture
def stub_search():
    from tests.fixtures.stub_search import StubSearchProvider

    return StubSearchProvider()


@pytest.fixture
def stub_fetch():
    from tests.fixtures.stub_fetch import StubFetchClient

    return StubFetchClient()
