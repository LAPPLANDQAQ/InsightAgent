# InsightAgent

InsightAgent is a LangGraph-based multi-agent competitive analysis system.

## Status

V0 development is in progress. This workspace currently contains commit1 to
commit3 from the execution spec: project skeleton, runtime configuration,
schemas, and L0 protocol interfaces.

## Quick Start

```bash
cp .env.example .env
# Fill in DASHSCOPE_API_KEY before using live Qwen calls.
pip install -e ".[dev]"
pytest
```

## Documentation

The authoritative execution spec is
`InsightAgent_Codex执行规约_v6_审查修复版.md`.
