The `ledger` package (a double-entry accounting library) has a FAILING test
suite. A number of bugs were introduced across the modules under `ledger/`.

Find and fix EVERY bug so the whole suite passes:

    python3 -m unittest discover -s tests -t .

Rules:
- Do NOT modify anything under `tests/` — the tests are correct; the bugs
  are in `ledger/`.
- Behavior must match what the tests specify; don't special-case test inputs.
- Several bugs interact (integration tests in `test_book.py` / `test_report.py`
  only pass once the leaf modules they build on are correct), so expect to
  run the suite several times as you work.

In your final reply, list the files you changed and the bug in each.
