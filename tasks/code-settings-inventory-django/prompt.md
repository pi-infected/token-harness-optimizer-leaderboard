Your team is writing configuration documentation for Django and needs a
ground-truth inventory of which settings the framework ACTUALLY reads.

Produce `SETTINGS_INVENTORY.md` at the repository root:

- One line per DISTINCT setting read anywhere under the `django/` package
  directory (ignore `tests/`, `docs/`): the pattern to inventory is attribute
  reads like `settings.SOMETHING`.
- Format each line exactly as: `NAME — path:line` where `path` is relative to
  the repo root and points at ONE real occurrence (any one is fine).
  Example: `USE_TZ — django/utils/timezone.py:63`
- Cover at least 90 distinct settings. Accuracy matters: every cited
  `path:line` must really contain that `settings.NAME` read.

Keep the file to one line per setting, sorted alphabetically.
