The `pipeline` package is a small sales-data ETL: it parses CSV lines,
validates them, computes per-line totals with a regional discount,
aggregates by region, and reports. Its test suite is RED.

Find and fix every bug under `pipeline/` so the whole suite passes:

    python3 -m unittest discover -s tests -t .

The key test is `tests/test_integration.py`: it runs the full pipeline over
`data/input.csv` and compares every record's total (and the regional/grand
aggregates) against the expected values in `data/golden.json`. On failure it
prints the mismatching records, so use that output to track down which stage
is wrong.

Rules:
- Do NOT modify anything under `tests/` or under `data/` — the tests and the
  golden dataset are correct; the bugs are all in `pipeline/`.
- Behavior must match the spec; don't special-case individual records.
- Bugs span several stages (parse, validate, transform, aggregate, run,
  report); a record's total is only right once every stage it passes through
  is right, so expect to run the suite several times as you fix stages.

In your final reply, list the files you changed and the bug in each.
