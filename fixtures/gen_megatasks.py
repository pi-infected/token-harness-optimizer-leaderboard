#!/usr/bin/env python3
"""Standalone generator for the heavy (high-cost) bench tasks.

Kept SEPARATE from generate_fixtures.py and gen_longtasks.py (must not edit
the bench's own code) — this only ADDS new fixtures + truth files and is
safe to re-run. Targets the high-cost / churn regime where the tokenade
anti-derailment + output-dedup leverage is expected to dominate.

Tasks added:

  code-debug-cascade-py    a double-entry accounting package SCALED UP from
                           ledger-debug: 6 extra modules and ~10
                           interdependent bugs. Long run-fix-rerun session,
                           unittest tracebacks repeated across cycles.

  code-debug-pipeline-py   an ETL pipeline (parse -> validate -> transform
                           -> aggregate -> report) over a 200-row dataset.
                           The integration test re-runs the whole pipeline
                           and prints a VERBOSE per-record diff on every
                           failure; ~9 bugs spread across the stages mean
                           the agent runs-fixes-reruns many times, each
                           cycle re-emitting a LARGE diff. This is the regime
                           tokenade is built for (big repeated outputs +
                           re-reads), unlike a terse compiler (the dropped
                           build-storm-ts task emitted diagnostics too small
                           to compact).

Self-checks at the end: each task's SHIPPED state must be RED and its
reference solution GREEN — so each is non-trivial and solvable.
"""
import hashlib
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TRUTH = HERE / "truth"
TASKS = HERE.parent / "tasks"


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_task(task_id, *, title, fixture, max_turns, timeout_s, prompt, verify):
    d = TASKS / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "task.json").write_text(json.dumps({
        "id": task_id,
        "title": title,
        "kind": "code",
        "workspace": {"fixture": fixture},
        "max_turns": max_turns,
        "timeout_s": timeout_s,
        "success_threshold": 1.0,
        "baseline_score": 0.3,
    }, indent=2) + "\n")
    (d / "prompt.md").write_text(prompt)
    (d / "verify.py").write_text(verify)


def run_unittest(ws: Path):
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=str(ws), capture_output=True, text=True, timeout=180,
    )
    out = r.stderr + r.stdout
    import re
    ran = re.search(r"Ran (\d+) test", out)
    total = int(ran.group(1)) if ran else 0
    fails = errs = 0
    m = re.search(r"failures=(\d+)", out)
    if m:
        fails = int(m.group(1))
    m = re.search(r"errors=(\d+)", out)
    if m:
        errs = int(m.group(1))
    passed = total - fails - errs
    return r.returncode, passed, total


# ===========================================================================
# Task 1: code-debug-cascade-py  (churn-driven, Python unittest)
# ===========================================================================

CASCADE = {
    "ledger/__init__.py": "",
    "ledger/money.py": '''\
"""Integer-cents money type — no float drift."""


class Money:
    __slots__ = ("cents",)

    def __init__(self, cents: int):
        self.cents = int(cents)

    @classmethod
    def from_float(cls, value: float) -> "Money":
        return cls(round(value * 100))

    def dollars(self) -> float:
        return self.cents / 100

    def __add__(self, other: "Money") -> "Money":
        return Money(self.cents + other.cents)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.cents - other.cents)

    def __mul__(self, k) -> "Money":
        return Money(round(self.cents * k))

    def __neg__(self) -> "Money":
        return Money(-self.cents)

    def __eq__(self, other) -> bool:
        return isinstance(other, Money) and self.cents == other.cents

    def __lt__(self, other: "Money") -> bool:
        return self.cents < other.cents

    def __hash__(self):
        return hash(self.cents)

    def __repr__(self):
        return f"Money({self.cents})"

    def __str__(self):
        sign = "-" if self.cents < 0 else ""
        return f"{sign}${abs(self.cents) / 100:.2f}"
''',
    "ledger/account.py": '''\
from ledger.money import Money


class Account:
    def __init__(self, name: str):
        self.name = name
        self.balance = Money(0)

    def credit(self, amount: Money):
        self.balance = self.balance + amount

    def debit(self, amount: Money):
        self.balance = self.balance - amount
''',
    "ledger/posting.py": '''\
from ledger.money import Money
from ledger.account import Account


class Transaction:
    def __init__(self, debit_account: Account, credit_account: Account,
                 amount: Money):
        self.debit_account = debit_account
        self.credit_account = credit_account
        self.amount = amount


def post(tx: Transaction):
    """Double-entry: the debit side loses, the credit side gains."""
    tx.debit_account.debit(tx.amount)
    tx.credit_account.credit(tx.amount)
''',
    "ledger/fx.py": '''\
from ledger.money import Money

RATES = {
    "USD": 1.0,
    "EUR": 0.90,
    "GBP": 0.80,
    "JPY": 150.0,
}


def convert(amount: Money, from_cur: str, to_cur: str) -> Money:
    if from_cur not in RATES or to_cur not in RATES:
        raise KeyError(f"unknown currency: {from_cur}/{to_cur}")
    usd = amount.dollars() / RATES[from_cur]
    target = usd * RATES[to_cur]
    return Money.from_float(target)
''',
    "ledger/report.py": '''\
from ledger.money import Money


def trial_balance(accounts) -> Money:
    total = Money(0)
    for acct in accounts:
        total = total + acct.balance
    return total


def format_statement(account) -> str:
    return f"{account.name}: {account.balance}"
''',
    "ledger/budget.py": '''\
from ledger.money import Money


def variance(actual: Money, planned: Money) -> Money:
    """Positive when over plan, negative when under."""
    return actual - planned


def over_budget(actual: Money, planned: Money) -> bool:
    return planned < actual


def pct_used(actual: Money, planned: Money) -> float:
    """Fraction of the plan consumed; 0.0 when nothing was planned."""
    if planned.cents == 0:
        return 0.0
    return actual.cents / planned.cents
''',
    "ledger/interest.py": '''\
from ledger.money import Money


def simple_interest(principal: Money, rate: float, years: int) -> Money:
    return Money.from_float(principal.dollars() * rate * years)


def compound_interest(principal: Money, rate: float, years: int) -> Money:
    """Interest EARNED after annual compounding (excludes the principal)."""
    total = principal.dollars() * ((1 + rate) ** years)
    return Money.from_float(total - principal.dollars())
''',
    "ledger/depreciation.py": '''\
from ledger.money import Money


def straight_line(cost: Money, salvage: Money, life: int) -> Money:
    """Depreciation charged each year under the straight-line method."""
    return Money.from_float((cost.dollars() - salvage.dollars()) / life)


def book_value(cost: Money, salvage: Money, life: int, year: int) -> Money:
    """Remaining book value after `year` full years of depreciation."""
    annual = straight_line(cost, salvage, life)
    return cost - (annual * year)
''',
    "ledger/tax.py": '''\
from ledger.money import Money

# (exclusive upper bound in cents or None for the top band, marginal rate)
BRACKETS = [
    (1000000, 0.10),
    (4000000, 0.20),
    (None, 0.30),
]


def tax_for(income: Money) -> Money:
    cents = income.cents
    owed = 0.0
    lower = 0
    for upper, rate in BRACKETS:
        if upper is None:
            taxable = cents - lower
        else:
            taxable = min(cents, upper) - lower
        if taxable > 0:
            owed += taxable * rate
        if upper is not None and cents <= upper:
            break
        lower = upper
    return Money(round(owed))
''',
    "ledger/book.py": '''\
from ledger.money import Money
from ledger.account import Account
from ledger.posting import Transaction, post
from ledger.report import trial_balance


class Book:
    """A set of named accounts with double-entry transfers."""

    def __init__(self):
        self.accounts = {}

    def open(self, name: str) -> Account:
        acct = Account(name)
        self.accounts[name] = acct
        return acct

    def transfer(self, debit_name: str, credit_name: str, amount: Money):
        post(Transaction(self.accounts[debit_name],
                         self.accounts[credit_name], amount))

    def balance(self, name: str) -> Money:
        return self.accounts[name].balance

    def total(self) -> Money:
        return trial_balance(self.accounts.values())
''',
    "tests/__init__.py": "",
    "tests/test_money.py": '''\
import unittest
from ledger.money import Money


class TestMoney(unittest.TestCase):
    def test_from_float_cents(self):
        self.assertEqual(Money.from_float(19.99), Money(1999))

    def test_from_float_round(self):
        self.assertEqual(Money.from_float(0.014), Money(1))
        self.assertEqual(Money.from_float(0.016), Money(2))

    def test_add(self):
        self.assertEqual(Money(100) + Money(50), Money(150))

    def test_sub(self):
        self.assertEqual(Money(100) - Money(30), Money(70))

    def test_sub_negative(self):
        self.assertEqual(Money(30) - Money(100), Money(-70))

    def test_mul(self):
        self.assertEqual(Money(100) * 3, Money(300))

    def test_neg(self):
        self.assertEqual(-Money(250), Money(-250))

    def test_str_positive(self):
        self.assertEqual(str(Money(1999)), "$19.99")

    def test_str_negative(self):
        self.assertEqual(str(Money(-500)), "-$5.00")

    def test_lt(self):
        self.assertTrue(Money(100) < Money(200))
        self.assertFalse(Money(200) < Money(100))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_account.py": '''\
import unittest
from ledger.money import Money
from ledger.account import Account


class TestAccount(unittest.TestCase):
    def test_credit(self):
        a = Account("cash")
        a.credit(Money(500))
        self.assertEqual(a.balance, Money(500))

    def test_debit(self):
        a = Account("cash")
        a.credit(Money(500))
        a.debit(Money(200))
        self.assertEqual(a.balance, Money(300))

    def test_debit_into_negative(self):
        a = Account("loan")
        a.debit(Money(1000))
        self.assertEqual(a.balance, Money(-1000))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_posting.py": '''\
import unittest
from ledger.money import Money
from ledger.account import Account
from ledger.posting import Transaction, post


class TestPosting(unittest.TestCase):
    def test_double_entry(self):
        cash = Account("cash")
        revenue = Account("revenue")
        cash.credit(Money(10000))
        post(Transaction(debit_account=cash, credit_account=revenue,
                         amount=Money(2500)))
        self.assertEqual(cash.balance, Money(7500))
        self.assertEqual(revenue.balance, Money(2500))

    def test_post_conserves_total(self):
        a = Account("a")
        b = Account("b")
        a.credit(Money(5000))
        post(Transaction(a, b, Money(1234)))
        self.assertEqual((a.balance + b.balance), Money(5000))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_fx.py": '''\
import unittest
from ledger.money import Money
from ledger.fx import convert


class TestFx(unittest.TestCase):
    def test_usd_to_eur(self):
        self.assertEqual(convert(Money(10000), "USD", "EUR"), Money(9000))

    def test_eur_to_usd(self):
        self.assertEqual(convert(Money(9000), "EUR", "USD"), Money(10000))

    def test_usd_to_usd_identity(self):
        self.assertEqual(convert(Money(4242), "USD", "USD"), Money(4242))

    def test_unknown_currency(self):
        with self.assertRaises(KeyError):
            convert(Money(100), "USD", "XYZ")


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_report.py": '''\
import unittest
from ledger.money import Money
from ledger.account import Account
from ledger.posting import Transaction, post
from ledger.report import trial_balance, format_statement


class TestReport(unittest.TestCase):
    def test_balanced_books_sum_to_zero(self):
        cash = Account("cash")
        revenue = Account("revenue")
        expense = Account("expense")
        post(Transaction(debit_account=expense, credit_account=cash,
                         amount=Money(3000)))
        post(Transaction(debit_account=cash, credit_account=revenue,
                         amount=Money(8000)))
        self.assertEqual(trial_balance([cash, revenue, expense]), Money(0))

    def test_trial_balance_counts_every_account(self):
        accounts = [Account(f"a{i}") for i in range(4)]
        for a in accounts:
            a.credit(Money(100))
        self.assertEqual(trial_balance(accounts), Money(400))

    def test_format_statement(self):
        a = Account("cash")
        a.credit(Money(1250))
        self.assertEqual(format_statement(a), "cash: $12.50")


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_budget.py": '''\
import unittest
from ledger.money import Money
from ledger.budget import variance, over_budget, pct_used


class TestBudget(unittest.TestCase):
    def test_variance_over(self):
        self.assertEqual(variance(Money(1200), Money(1000)), Money(200))

    def test_variance_under(self):
        self.assertEqual(variance(Money(800), Money(1000)), Money(-200))

    def test_over_budget_true(self):
        self.assertTrue(over_budget(Money(1200), Money(1000)))

    def test_over_budget_false(self):
        self.assertFalse(over_budget(Money(900), Money(1000)))
        self.assertFalse(over_budget(Money(1000), Money(1000)))

    def test_pct_used(self):
        self.assertAlmostEqual(pct_used(Money(750), Money(1000)), 0.75)

    def test_pct_used_zero_plan(self):
        self.assertEqual(pct_used(Money(500), Money(0)), 0.0)


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_interest.py": '''\
import unittest
from ledger.money import Money
from ledger.interest import simple_interest, compound_interest


class TestInterest(unittest.TestCase):
    def test_simple(self):
        # $1000 at 5% for 2 years -> $100
        self.assertEqual(simple_interest(Money(100000), 0.05, 2), Money(10000))

    def test_simple_one_year(self):
        self.assertEqual(simple_interest(Money(100000), 0.10, 1), Money(10000))

    def test_compound(self):
        # $1000 at 5% for 2 years -> 1102.50 -> interest 102.50
        self.assertEqual(compound_interest(Money(100000), 0.05, 2),
                         Money(10250))

    def test_compound_one_year_equals_simple(self):
        self.assertEqual(compound_interest(Money(100000), 0.05, 1),
                         simple_interest(Money(100000), 0.05, 1))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_depreciation.py": '''\
import unittest
from ledger.money import Money
from ledger.depreciation import straight_line, book_value


class TestDepreciation(unittest.TestCase):
    def test_straight_line(self):
        # cost $10000, salvage $1000, life 5 -> $1800/yr
        self.assertEqual(straight_line(Money(1000000), Money(100000), 5),
                         Money(180000))

    def test_book_value_year_0(self):
        self.assertEqual(
            book_value(Money(1000000), Money(100000), 5, 0), Money(1000000))

    def test_book_value_year_2(self):
        # 1000000 - 2*180000 = 640000
        self.assertEqual(
            book_value(Money(1000000), Money(100000), 5, 2), Money(640000))

    def test_book_value_full_life(self):
        # after `life` years, book value == salvage
        self.assertEqual(
            book_value(Money(1000000), Money(100000), 5, 5), Money(100000))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_tax.py": '''\
import unittest
from ledger.money import Money
from ledger.tax import tax_for


class TestTax(unittest.TestCase):
    def test_first_bracket(self):
        # $5,000 -> 10% -> $500
        self.assertEqual(tax_for(Money(500000)), Money(50000))

    def test_second_bracket(self):
        # $25,000 -> 10%*10k + 20%*15k = 1000 + 3000 = $4000
        self.assertEqual(tax_for(Money(2500000)), Money(400000))

    def test_top_bracket(self):
        # $50,000 -> 1000 + 6000 + 3000 = $10000
        self.assertEqual(tax_for(Money(5000000)), Money(1000000))

    def test_zero(self):
        self.assertEqual(tax_for(Money(0)), Money(0))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_book.py": '''\
import unittest
from ledger.money import Money
from ledger.book import Book


class TestBook(unittest.TestCase):
    def test_transfer_moves_money(self):
        b = Book()
        b.open("cash")
        b.open("rent")
        b.accounts["cash"].credit(Money(100000))
        b.transfer("cash", "rent", Money(30000))
        self.assertEqual(b.balance("cash"), Money(70000))
        self.assertEqual(b.balance("rent"), Money(30000))

    def test_total_conserved(self):
        b = Book()
        b.open("a")
        b.open("b")
        b.accounts["a"].credit(Money(50000))
        b.transfer("a", "b", Money(12345))
        self.assertEqual(b.total(), Money(50000))

    def test_open_returns_zero_account(self):
        b = Book()
        acct = b.open("new")
        self.assertEqual(acct.balance, Money(0))

    def test_balance_lookup(self):
        b = Book()
        b.open("savings")
        b.accounts["savings"].credit(Money(9999))
        self.assertEqual(b.balance("savings"), Money(9999))


if __name__ == "__main__":
    unittest.main()
''',
    "README.md": '''\
# ledger (XL)

A double-entry accounting library: integer-cents money, accounts, postings,
FX conversion, trial-balance reporting, budgeting, interest, depreciation,
progressive tax, and a Book integration layer.
''',
}

CASCADE_BUGS = {
    "ledger/money.py": (
        "        return cls(round(value * 100))",
        "        return cls(int(value * 100))",
    ),
    "ledger/account.py": (
        "    def debit(self, amount: Money):\n        self.balance = self.balance - amount",
        "    def debit(self, amount: Money):\n        self.balance = self.balance + amount",
    ),
    "ledger/posting.py": (
        "    tx.debit_account.debit(tx.amount)\n    tx.credit_account.credit(tx.amount)",
        "    tx.debit_account.debit(tx.amount)\n    tx.credit_account.debit(tx.amount)",
    ),
    "ledger/fx.py": (
        "    usd = amount.dollars() / RATES[from_cur]\n    target = usd * RATES[to_cur]",
        "    usd = amount.dollars() * RATES[from_cur]\n    target = usd * RATES[to_cur]",
    ),
    "ledger/report.py": (
        "    total = Money(0)\n    for acct in accounts:\n        total = total + acct.balance",
        "    total = Money(0)\n    for acct in accounts:\n        total = acct.balance",
    ),
    "ledger/budget.py": (
        "def over_budget(actual: Money, planned: Money) -> bool:\n    return planned < actual",
        "def over_budget(actual: Money, planned: Money) -> bool:\n    return actual < planned",
    ),
    "ledger/interest.py": (
        "    total = principal.dollars() * ((1 + rate) ** years)",
        "    total = principal.dollars() * (1 + rate * years)",
    ),
    "ledger/depreciation.py": (
        "    return Money.from_float((cost.dollars() - salvage.dollars()) / life)",
        "    return Money.from_float(cost.dollars() / life)",
    ),
    "ledger/tax.py": (
        "            taxable = min(cents, upper) - lower",
        "            taxable = cents - lower",
    ),
    "ledger/book.py": (
        "        post(Transaction(self.accounts[debit_name],\n                         self.accounts[credit_name], amount))",
        "        post(Transaction(self.accounts[credit_name],\n                         self.accounts[debit_name], amount))",
    ),
}

CASCADE_PROMPT = '''\
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
'''

CASCADE_VERIFY = '''\
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth

t = truth("code-debug-cascade-py.json")
if not hashes_intact(WS, t["frozen_test_hashes"]):
    emit(0.0, "a frozen test file under tests/ was modified")
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
out = (r.stderr or "") + (r.stdout or "")
ran = re.search(r"Ran (\\d+) test", out)
total = int(ran.group(1)) if ran else t["total_tests"]
fails = errs = 0
m = re.search(r"failures=(\\d+)", out); fails = int(m.group(1)) if m else 0
m = re.search(r"errors=(\\d+)", out);   errs = int(m.group(1)) if m else 0
passed = total - fails - errs
score = 1.0 if r.returncode == 0 else max(0.0, passed / total)
emit(score, f"{passed}/{total} tests pass"
            + ("" if r.returncode == 0 else f"; tail: {out[-300:]}"))
'''


def gen_debug_cascade():
    fixture = OUT / "cascade-debug"
    if fixture.exists():
        shutil.rmtree(fixture)
    for rel, text in CASCADE.items():
        write(fixture / rel, text)

    rc, passed, total = run_unittest(fixture)
    assert rc == 0 and passed == total, \
        f"reference cascade NOT green: rc={rc} {passed}/{total}"
    ref_total = total

    frozen = {}
    for rel in CASCADE:
        if rel.startswith("tests/"):
            frozen[rel] = sha(fixture / rel)

    for rel, (find, repl) in CASCADE_BUGS.items():
        p = fixture / rel
        src = p.read_text()
        assert src.count(find) == 1, f"bug anchor not unique in {rel}: {src.count(find)}x"
        p.write_text(src.replace(find, repl, 1))

    rc, passed, total = run_unittest(fixture)
    assert rc != 0 and passed < total, \
        f"shipped cascade should be RED, got rc={rc} {passed}/{total}"
    print(f"  cascade-debug: shipped RED {passed}/{total}, "
          f"ref GREEN {ref_total}/{ref_total}, bugs={len(CASCADE_BUGS)}")

    write(TRUTH / "code-debug-cascade-py.json",
          json.dumps({"frozen_test_hashes": frozen, "total_tests": ref_total},
                     indent=2) + "\n")
    _write_task(
        "code-debug-cascade-py",
        title="Debug a large red accounting suite (10 bugs across 10 modules)",
        fixture="cascade-debug",
        max_turns=80, timeout_s=2400,
        prompt=CASCADE_PROMPT, verify=CASCADE_VERIFY,
    )


# ===========================================================================
# Task 2: code-debug-pipeline-py  (big-repeated-output, churn-driven)
# ===========================================================================

NAME_POOL = [
    "widget", "gadget", "sprocket", "cog", "flange", "bracket", "piston",
    "valve", "gasket", "bearing", "spindle", "rivet", "washer", "bolt",
    "nut", "screw", "spring", "lever", "hinge", "clamp",
]


def make_dataset(n=200):
    """Deterministic CSV: id,name,qty,price,region — with ~12% invalid rows."""
    rng = random.Random(20260619)
    rows = ["id,name,qty,price,region"]
    for i in range(1, n + 1):
        region = rng.choice(["N", "S", "E", "W"])
        name = rng.choice(NAME_POOL)
        qty = rng.randint(1, 50)
        price = round(rng.uniform(1.0, 99.99), 2)
        roll = rng.random()
        if roll < 0.04:
            region = "X"             # invalid region
        elif roll < 0.08:
            qty = -rng.randint(1, 9)  # invalid qty
        elif roll < 0.12:
            name = ""                # invalid name
        rows.append(f"{i},{name},{qty},{price:.2f},{region}")
    return "\n".join(rows) + "\n"


PIPELINE = {
    "pipeline/__init__.py": "",
    "pipeline/parse.py": '''\
"""Parse one raw CSV line into a record dict (money kept in integer cents)."""


def parse_line(raw: str) -> dict:
    fields = raw.split(",")
    return {
        "id": int(fields[0]),
        "name": fields[1].strip(),
        "qty": int(fields[2]),
        "price_cents": int(round(float(fields[3]) * 100)),
        "region": fields[4].strip(),
    }
''',
    "pipeline/validate.py": '''\
"""Reject malformed records before they reach the aggregates."""

VALID_REGIONS = ("N", "S", "E", "W")


def validate(rec: dict) -> list:
    errors = []
    if not rec["name"]:
        errors.append("empty name")
    if rec["qty"] < 0:
        errors.append("negative qty")
    if rec["price_cents"] < 0:
        errors.append("negative price")
    if rec["region"] not in VALID_REGIONS:
        errors.append("bad region")
    return errors
''',
    "pipeline/transform.py": '''\
"""Compute per-line totals and apply the regional discount."""

DISCOUNT = {"N": 0.0, "S": 0.05, "E": 0.10, "W": 0.15}


def line_total(rec: dict) -> int:
    return rec["qty"] * rec["price_cents"]


def apply_discount(rec: dict, total: int) -> int:
    rate = DISCOUNT[rec["region"]]
    return int(round(total * (1 - rate)))
''',
    "pipeline/aggregate.py": '''\
"""Roll the per-record totals up by region and overall."""


def by_region(records) -> dict:
    out = {}
    for r in records:
        out[r["region"]] = out.get(r["region"], 0) + r["total"]
    return out


def grand_total(records) -> int:
    return sum(r["total"] for r in records)
''',
    "pipeline/report.py": '''\
"""Render the regional aggregate as a stable, sorted text block."""


def format_report(agg: dict) -> str:
    lines = []
    for region in sorted(agg):
        lines.append(f"{region}: {agg[region]}")
    return "\\n".join(lines)
''',
    "pipeline/run.py": '''\
from pipeline.parse import parse_line
from pipeline.validate import validate
from pipeline.transform import line_total, apply_discount
from pipeline.aggregate import by_region, grand_total


def run_pipeline(lines):
    """Full ETL: returns (valid_records_with_totals, by_region, grand_total)."""
    recs = [parse_line(l) for l in lines if l.strip()]
    valid = [r for r in recs if not validate(r)]
    for r in valid:
        r["total"] = apply_discount(r, line_total(r))
    return valid, by_region(valid), grand_total(valid)
''',
    "tests/__init__.py": "",
    "tests/test_parse.py": '''\
import unittest
from pipeline.parse import parse_line


class TestParse(unittest.TestCase):
    def test_fields(self):
        r = parse_line("7,widget,3,12.50,N")
        self.assertEqual(r["id"], 7)
        self.assertEqual(r["name"], "widget")
        self.assertEqual(r["qty"], 3)
        self.assertEqual(r["region"], "N")

    def test_price_is_cents(self):
        self.assertEqual(parse_line("1,x,1,12.50,N")["price_cents"], 1250)

    def test_price_rounds(self):
        self.assertEqual(parse_line("1,x,1,0.015,N")["price_cents"], 2)

    def test_strips_name(self):
        self.assertEqual(parse_line("1, widget ,1,1.00,N")["name"], "widget")


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_validate.py": '''\
import unittest
from pipeline.validate import validate


def rec(**kw):
    base = {"id": 1, "name": "x", "qty": 1, "price_cents": 100, "region": "N"}
    base.update(kw)
    return base


class TestValidate(unittest.TestCase):
    def test_good(self):
        self.assertEqual(validate(rec()), [])

    def test_west_is_valid(self):
        self.assertEqual(validate(rec(region="W")), [])

    def test_bad_region(self):
        self.assertIn("bad region", validate(rec(region="X")))

    def test_negative_qty(self):
        self.assertIn("negative qty", validate(rec(qty=-2)))

    def test_empty_name(self):
        self.assertIn("empty name", validate(rec(name="")))


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_transform.py": '''\
import unittest
from pipeline.transform import line_total, apply_discount


class TestTransform(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total({"qty": 4, "price_cents": 250}), 1000)

    def test_discount_north_none(self):
        self.assertEqual(apply_discount({"region": "N"}, 1000), 1000)

    def test_discount_south_5pct(self):
        self.assertEqual(apply_discount({"region": "S"}, 1000), 950)

    def test_discount_east_10pct(self):
        self.assertEqual(apply_discount({"region": "E"}, 1000), 900)

    def test_discount_west_15pct(self):
        self.assertEqual(apply_discount({"region": "W"}, 1000), 850)


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_aggregate.py": '''\
import unittest
from pipeline.aggregate import by_region, grand_total


class TestAggregate(unittest.TestCase):
    def test_by_region_accumulates(self):
        recs = [
            {"region": "N", "total": 100},
            {"region": "N", "total": 50},
            {"region": "S", "total": 200},
        ]
        self.assertEqual(by_region(recs), {"N": 150, "S": 200})

    def test_grand_total_sums_all(self):
        recs = [{"total": 100}, {"total": 50}, {"total": 200}]
        self.assertEqual(grand_total(recs), 350)

    def test_grand_total_includes_first(self):
        recs = [{"total": 7}, {"total": 3}]
        self.assertEqual(grand_total(recs), 10)

    def test_empty(self):
        self.assertEqual(by_region([]), {})
        self.assertEqual(grand_total([]), 0)


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_report.py": '''\
import unittest
from pipeline.report import format_report


class TestReport(unittest.TestCase):
    def test_sorted_regions(self):
        out = format_report({"S": 200, "N": 100})
        self.assertEqual(out, "N: 100\\nS: 200")


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_run.py": '''\
import unittest
from pipeline.run import run_pipeline


class TestRun(unittest.TestCase):
    def test_filters_invalid(self):
        lines = [
            "1,widget,2,10.00,N",   # valid -> total 2000
            "2,,3,5.00,S",          # invalid: empty name
            "3,gadget,-1,5.00,E",   # invalid: negative qty
            "4,cog,1,4.00,X",       # invalid: bad region
        ]
        valid, agg, gt = run_pipeline(lines)
        self.assertEqual([r["id"] for r in valid], [1])
        self.assertEqual(agg, {"N": 2000})
        self.assertEqual(gt, 2000)


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_integration.py": '''\
import json
import unittest
from pathlib import Path
from pipeline.run import run_pipeline

ROOT = Path(__file__).resolve().parent.parent


class TestIntegration(unittest.TestCase):
    def test_pipeline_matches_golden(self):
        lines = (ROOT / "data" / "input.csv").read_text().splitlines()[1:]
        golden = json.loads((ROOT / "data" / "golden.json").read_text())
        valid, agg, gt = run_pipeline(lines)

        got = {r["id"]: r["total"] for r in valid}
        exp = {int(e["id"]): e["total"] for e in golden["records"]}

        problems = []
        for rid in sorted(exp):
            if got.get(rid) != exp[rid]:
                problems.append(
                    f"  id {rid}: expected total {exp[rid]}, got {got.get(rid)}")
        extra = sorted(set(got) - set(exp))
        missing = sorted(set(exp) - set(got))

        detail = problems[:60]
        if len(problems) > 60:
            detail.append(f"  ... and {len(problems) - 60} more record mismatches")
        if extra:
            detail.append(f"  invalid records leaked into output: ids {extra[:25]}")
        if missing:
            detail.append(f"  valid records dropped from output: ids {missing[:25]}")
        if agg != golden["by_region"]:
            detail.append(f"  by_region: expected {golden['by_region']}, got {agg}")
        if gt != golden["grand_total"]:
            detail.append(f"  grand_total: expected {golden['grand_total']}, got {gt}")

        self.assertEqual(
            detail, [],
            "pipeline output does not match the golden dataset:\\n"
            + "\\n".join(detail))


if __name__ == "__main__":
    unittest.main()
''',
    "README.md": '''\
# sales-pipeline

A small ETL pipeline over a CSV of sales lines:

    parse -> validate -> transform (line total + regional discount)
          -> aggregate (by region + grand total) -> report

`data/input.csv` is the dataset; `data/golden.json` is the expected output
the integration test checks against. Money is kept in integer cents.
'''
}

PIPELINE_BUGS = {
    "pipeline/parse.py": (
        '        "price_cents": int(round(float(fields[3]) * 100)),',
        '        "price_cents": int(float(fields[3])),',
    ),
    "pipeline/validate.py": (
        'VALID_REGIONS = ("N", "S", "E", "W")',
        'VALID_REGIONS = ("N", "S", "E")',
    ),
    "pipeline/transform.py": (
        '    return rec["qty"] * rec["price_cents"]',
        '    return rec["qty"] + rec["price_cents"]',
    ),
    "pipeline/transform.py#2": (
        '    return int(round(total * (1 - rate)))',
        '    return int(round(total * (1 + rate)))',
    ),
    "pipeline/transform.py#3": (
        'DISCOUNT = {"N": 0.0, "S": 0.05, "E": 0.10, "W": 0.15}',
        'DISCOUNT = {"N": 0.0, "S": 0.10, "E": 0.05, "W": 0.15}',
    ),
    "pipeline/aggregate.py": (
        '        out[r["region"]] = out.get(r["region"], 0) + r["total"]',
        '        out[r["region"]] = r["total"]',
    ),
    "pipeline/aggregate.py#2": (
        '    return sum(r["total"] for r in records)',
        '    return sum(r["total"] for r in records[1:])',
    ),
    "pipeline/run.py": (
        '    valid = [r for r in recs if not validate(r)]',
        '    valid = recs',
    ),
    "pipeline/report.py": (
        '    for region in sorted(agg):',
        '    for region in agg:',
    ),
}

PIPELINE_PROMPT = '''\
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
'''

PIPELINE_VERIFY = '''\
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth

t = truth("code-debug-pipeline-py.json")
if not hashes_intact(WS, t["frozen_hashes"]):
    emit(0.0, "a frozen file under tests/ or data/ was modified")
r = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."])
out = (r.stderr or "") + (r.stdout or "")
ran = re.search(r"Ran (\\d+) test", out)
total = int(ran.group(1)) if ran else t["total_tests"]
fails = errs = 0
m = re.search(r"failures=(\\d+)", out); fails = int(m.group(1)) if m else 0
m = re.search(r"errors=(\\d+)", out);   errs = int(m.group(1)) if m else 0
passed = total - fails - errs
score = 1.0 if r.returncode == 0 else max(0.0, passed / total)
emit(score, f"{passed}/{total} tests pass"
            + ("" if r.returncode == 0 else f"; tail: {out[-300:]}"))
'''


def gen_debug_pipeline():
    fixture = OUT / "pipeline-debug"
    if fixture.exists():
        shutil.rmtree(fixture)
    for rel, text in PIPELINE.items():
        write(fixture / rel, text)
    write(fixture / "data" / "input.csv", make_dataset(200))

    # compute the golden output from the CORRECT pipeline.
    gold_src = (
        "import json,sys; sys.path.insert(0,'.')\n"
        "from pipeline.run import run_pipeline\n"
        "lines=open('data/input.csv').read().splitlines()[1:]\n"
        "valid,agg,gt=run_pipeline(lines)\n"
        "print(json.dumps({'records':[{'id':r['id'],'total':r['total']} for r in valid],"
        "'by_region':agg,'grand_total':gt}))\n"
    )
    res = subprocess.run([sys.executable, "-c", gold_src], cwd=str(fixture),
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, f"golden compute failed: {res.stderr}"
    golden = json.loads(res.stdout)
    write(fixture / "data" / "golden.json", json.dumps(golden, indent=2) + "\n")
    n_valid = len(golden["records"])

    rc, passed, total = run_unittest(fixture)
    assert rc == 0 and passed == total, \
        f"reference pipeline NOT green: rc={rc} {passed}/{total}"
    ref_total = total

    frozen = {}
    for rel in list(PIPELINE) + ["data/input.csv", "data/golden.json"]:
        if rel.startswith("tests/") or rel.startswith("data/"):
            frozen[rel] = sha(fixture / rel)

    for key, (find, repl) in PIPELINE_BUGS.items():
        rel = key.split("#")[0]
        p = fixture / rel
        src = p.read_text()
        assert src.count(find) == 1, f"bug anchor not unique in {key}: {src.count(find)}x"
        p.write_text(src.replace(find, repl, 1))

    rc, passed, total = run_unittest(fixture)
    assert rc != 0 and passed < total, \
        f"shipped pipeline should be RED, got rc={rc} {passed}/{total}"
    print(f"  pipeline-debug: shipped RED {passed}/{total}, ref GREEN "
          f"{ref_total}/{ref_total}, bugs={len(PIPELINE_BUGS)}, valid_rows={n_valid}")

    write(TRUTH / "code-debug-pipeline-py.json",
          json.dumps({"frozen_hashes": frozen, "total_tests": ref_total},
                     indent=2) + "\n")
    _write_task(
        "code-debug-pipeline-py",
        title="Debug a red sales-ETL pipeline (9 bugs across 6 stages, 200-row golden)",
        fixture="pipeline-debug",
        max_turns=80, timeout_s=2400,
        prompt=PIPELINE_PROMPT, verify=PIPELINE_VERIFY,
    )


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    TRUTH.mkdir(parents=True, exist_ok=True)
    print("generating heavy bench tasks...")
    gen_debug_cascade()
    gen_debug_pipeline()
    print("done.")
