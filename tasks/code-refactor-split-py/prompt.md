Perform the refactor described in `REFACTOR.md` in the current directory:
split `shapes.py` into a `shapes/` package (one submodule per class plus a
helpers module and an `__init__.py` that re-exports every public name), then
remove the old `shapes.py`. Behavior must not change and the test suite must
keep passing (`python3 -m unittest discover -s tests -t .`).

In your final reply, list the files you created and removed.
