The `ledger` package (a small double-entry accounting library) has a FAILING
test suite. Several bugs were introduced across the modules under `ledger/`.

Find and fix every bug so the whole suite passes:

    python3 -m unittest discover -s tests -t .

Rules:
- Do NOT modify anything under `tests/` — the tests are correct; the bugs
  are in `ledger/`.
- Behavior must match what the tests specify; don't special-case test inputs.

In your final reply, list the files you changed and the bug in each.
