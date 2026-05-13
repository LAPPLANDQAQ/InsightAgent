# Harness Runtime

Harness records agent/tool lifecycle events and keeps replay-friendly traces.

Components:

- `HarnessEvent`
- `InMemoryTraceStore`
- `ToolRegistry`
- `PolicyEngine`
- `HarnessRuntime`
- `collect_harness_metrics`
- `create_replay_snapshot`

Payloads redact secret-looking keys before storage.
