---
name: quality-gate   
description: Run the full quality gate: ruff lint, pytest, and bandit security scan
---

Run the full quality gate and report results:

```bash
uv run ruff check . 2>&1
uv run pytest tests/unit/ -q 2>&1
uv run bandit -r src/ -ll 2>&1
```

Report pass/fail for each layer. If any layer fails, show the specific errors. Do not claim work is complete until all three pass.

---
