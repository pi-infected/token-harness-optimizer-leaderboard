Perform the migration described in `MIGRATION.md` in the current directory,
completely. Every module under `webtools/app/` (there are 24) must be
migrated; behavior must not change; the test suite must keep passing
(`python3 -m unittest discover -s tests -t .`).

In your final reply, list the files you changed.
