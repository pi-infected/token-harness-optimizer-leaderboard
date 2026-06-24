#!/usr/bin/env python3
"""Standalone generator for the LONG autonomous-dev bench tasks.

Kept SEPARATE from generate_fixtures.py (the bench's own code, which must
not be edited) — this only ADDS new fixtures + truth files, and is safe to
re-run. Emits:

  fixtures/out/<fixture>/        workspace the agent sees
  fixtures/truth/<task>.json     ground truth (frozen test hashes) — hidden

Tasks added (credible for a dev driving autonomous agents — long, multi-
turn, multi-file, run-fix-rerun churn):

  code-debug-ledger-py    a small accounting package whose test suite is
                          RED — 5 subtle bugs planted across 5 modules.
                          Agent runs tests, reads tracebacks, fixes, reruns
                          until green. Tests are frozen (hash-checked).

  code-feature-validate-py  implement a fully-spec'd validators module +
                          wire it into 8 request handlers so a provided
                          (currently-failing) suite passes.

Self-checks at the end: the SHIPPED state must be RED, and a reference
correct solution must be GREEN — so each task is both non-trivial and
solvable.
"""
import hashlib
import json
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


def run_suite(ws: Path):
    """Run the package's unittest suite; return (returncode, passed, total)."""
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=str(ws), capture_output=True, text=True, timeout=120,
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


# ---------------------------------------------------------------------------
# Task 1: code-debug-ledger-py — correct package + planted bugs.
# ---------------------------------------------------------------------------

LEDGER = {
    "ledger/__init__.py": "",
    "ledger/money.py": '''\
"""Integer-cents money type — no float drift."""


class Money:
    __slots__ = ("cents",)

    def __init__(self, cents: int):
        self.cents = int(cents)

    @classmethod
    def from_float(cls, value: float) -> "Money":
        # Round to the nearest cent (banker's rounding is fine here).
        return cls(round(value * 100))

    def dollars(self) -> float:
        return self.cents / 100

    def __add__(self, other: "Money") -> "Money":
        return Money(self.cents + other.cents)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.cents - other.cents)

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

# Units of currency per 1 USD.
RATES = {
    "USD": 1.0,
    "EUR": 0.90,
    "GBP": 0.80,
    "JPY": 150.0,
}


def convert(amount: Money, from_cur: str, to_cur: str) -> Money:
    """Convert via USD: to_usd = amount / rate[from]; then * rate[to]."""
    if from_cur not in RATES or to_cur not in RATES:
        raise KeyError(f"unknown currency: {from_cur}/{to_cur}")
    usd = amount.dollars() / RATES[from_cur]
    target = usd * RATES[to_cur]
    return Money.from_float(target)
''',
    "ledger/report.py": '''\
from ledger.money import Money


def trial_balance(accounts) -> Money:
    """Sum of all account balances; zero for balanced double-entry books."""
    total = Money(0)
    for acct in accounts:
        total = total + acct.balance
    return total


def format_statement(account) -> str:
    return f"{account.name}: {account.balance}"
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
        # $100 -> 90 EUR
        self.assertEqual(convert(Money(10000), "USD", "EUR"), Money(9000))

    def test_eur_to_usd(self):
        # 90 EUR -> $100
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
        # Pure double-entry postings keep the trial balance at zero.
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
    "README.md": '''\
# ledger

A tiny double-entry accounting library (integer-cents money, accounts,
postings, FX conversion, trial-balance reporting).

Run the test suite:

    python3 -m unittest discover -s tests -t .
''',
}

# 5 subtle bugs, one per module. (file -> (find, replace)).
LEDGER_BUGS = {
    "ledger/money.py": (
        "        return cls(round(value * 100))",
        "        return cls(int(value * 100))",          # truncates 19.99 -> 1998
    ),
    "ledger/account.py": (
        "    def debit(self, amount: Money):\n        self.balance = self.balance - amount",
        "    def debit(self, amount: Money):\n        self.balance = self.balance + amount",  # debit adds
    ),
    "ledger/posting.py": (
        "    tx.debit_account.debit(tx.amount)\n    tx.credit_account.credit(tx.amount)",
        "    tx.debit_account.credit(tx.amount)\n    tx.credit_account.credit(tx.amount)",  # both credit
    ),
    "ledger/fx.py": (
        "    usd = amount.dollars() / RATES[from_cur]\n    target = usd * RATES[to_cur]",
        "    usd = amount.dollars() * RATES[from_cur]\n    target = usd * RATES[to_cur]",  # wrong direction
    ),
    "ledger/report.py": (
        "    total = Money(0)\n    for acct in accounts:",
        "    total = Money(0)\n    for acct in accounts[1:]:",  # skips first account
    ),
}


def gen_debug_ledger():
    fixture = OUT / "ledger-debug"
    if fixture.exists():
        shutil.rmtree(fixture)
    # 1. write the CORRECT package, verify GREEN (suite is self-consistent).
    for rel, text in LEDGER.items():
        write(fixture / rel, text)
    rc, passed, total = run_suite(fixture)
    assert rc == 0 and passed == total and total > 0, \
        f"reference ledger NOT green: rc={rc} {passed}/{total}"
    ref_total = total
    # 2. freeze the test files (agent must not touch them).
    frozen = {}
    for rel in LEDGER:
        if rel.startswith("tests/"):
            frozen[rel] = sha(fixture / rel)
    # 3. apply the bugs -> ships RED.
    for rel, (find, repl) in LEDGER_BUGS.items():
        p = fixture / rel
        src = p.read_text()
        assert find in src, f"bug anchor not found in {rel}"
        p.write_text(src.replace(find, repl, 1))
    rc, passed, total = run_suite(fixture)
    assert rc != 0 and passed < total, \
        f"buggy ledger unexpectedly green: {passed}/{total}"
    print(f"  ledger-debug: shipped RED {passed}/{total}, ref GREEN {ref_total}/{ref_total}")
    # 4. truth + task files.
    write(TRUTH / "code-debug-ledger-py.json",
          json.dumps({"frozen_test_hashes": frozen, "total_tests": ref_total}, indent=2))
    _write_task(
        "code-debug-ledger-py",
        title="Debug a red accounting test-suite (5 bugs across 5 modules)",
        fixture="ledger-debug",
        max_turns=60, timeout_s=1800,
        prompt='''\
The `ledger` package (a small double-entry accounting library) has a FAILING
test suite. Several bugs were introduced across the modules under `ledger/`.

Find and fix every bug so the whole suite passes:

    python3 -m unittest discover -s tests -t .

Rules:
- Do NOT modify anything under `tests/` — the tests are correct; the bugs
  are in `ledger/`.
- Behavior must match what the tests specify; don't special-case test inputs.

In your final reply, list the files you changed and the bug in each.
''',
        verify='''\
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth

t = truth("code-debug-ledger-py.json")
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
''',
    )


# ---------------------------------------------------------------------------
# Task 2: code-feature-validate-py — implement validators + wire 8 handlers.
# ---------------------------------------------------------------------------

VALIDATE_SPEC = '''\
# Feature: input validation

Implement `webshop/validators.py` and wire it into every handler under
`webshop/handlers/`. A full test suite already exists under `tests/` and is
currently FAILING. Make it pass:

    python3 -m unittest discover -s tests -t .

## `webshop/validators.py`

Create this module with these functions. Each raises
`webshop.errors.ValidationError` (already provided) with any message on
invalid input, and returns the cleaned value on success.

- `valid_email(s)` -> str. Must contain exactly one "@", a non-empty local
  part, and a domain containing at least one ".". Returns `s.strip().lower()`.
- `valid_quantity(n)` -> int. Must be an int (bool is NOT allowed) and in
  the range 1..=999. Returns it.
- `valid_amount_cents(n)` -> int. Must be an int > 0. Returns it.
- `valid_currency(s)` -> str. Uppercased; must be one of USD/EUR/GBP/JPY.
- `valid_sku(s)` -> str. Pattern: 3 uppercase letters, a dash, 4 digits
  (e.g. "ABC-1234"). Returns it.
- `non_empty(s, field="value")` -> str. `s.strip()` must be non-empty.

## Handlers

Each handler module under `webshop/handlers/` has a function with a
`# TODO: validate` marker. Make each handler validate its inputs using the
functions above BEFORE doing its work, raising `ValidationError` on bad
input. The tests under `tests/test_handlers.py` pin exactly which field each
handler must validate. Behavior on valid input must be unchanged.
'''


def _vfile_handlers():
    """Return {relpath: source} for the 8 handler modules (pre-wiring)."""
    # Each handler: a function taking a dict `req`, currently doing the work
    # WITHOUT validation. The TODO marks where validation must go.
    h = {}
    h["webshop/handlers/signup.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def signup(req):
    # TODO: validate — email must be a valid address
    email = req["email"]
    return {"ok": True, "email": email}
'''
    h["webshop/handlers/order.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def place_order(req):
    # TODO: validate — quantity must be a valid quantity (1..999)
    qty = req["quantity"]
    return {"ok": True, "quantity": qty}
'''
    h["webshop/handlers/charge.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def charge(req):
    # TODO: validate — amount_cents must be a positive integer
    amount = req["amount_cents"]
    return {"ok": True, "amount_cents": amount}
'''
    h["webshop/handlers/fx_quote.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def fx_quote(req):
    # TODO: validate — currency must be a known currency
    cur = req["currency"]
    return {"ok": True, "currency": cur}
'''
    h["webshop/handlers/catalog.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def add_item(req):
    # TODO: validate — sku must match the SKU pattern
    sku = req["sku"]
    return {"ok": True, "sku": sku}
'''
    h["webshop/handlers/profile.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def update_profile(req):
    # TODO: validate — display_name must be non-empty
    name = req["display_name"]
    return {"ok": True, "display_name": name}
'''
    h["webshop/handlers/invite.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def invite(req):
    # TODO: validate — email must be a valid address
    email = req["email"]
    return {"ok": True, "email": email}
'''
    h["webshop/handlers/refund.py"] = '''\
from webshop.errors import ValidationError  # noqa: F401


def refund(req):
    # TODO: validate — amount_cents must be a positive integer
    amount = req["amount_cents"]
    return {"ok": True, "amount_cents": amount}
'''
    return h


VALIDATE_TESTS = {
    "tests/__init__.py": "",
    "tests/test_validators.py": '''\
import unittest
from webshop.errors import ValidationError
from webshop import validators as v


class TestValidators(unittest.TestCase):
    def test_email_ok(self):
        self.assertEqual(v.valid_email("  Bob@Example.COM "), "bob@example.com")

    def test_email_bad(self):
        for bad in ["", "no-at", "a@b", "@example.com", "a@@b.com"]:
            with self.assertRaises(ValidationError):
                v.valid_email(bad)

    def test_quantity_ok(self):
        self.assertEqual(v.valid_quantity(1), 1)
        self.assertEqual(v.valid_quantity(999), 999)

    def test_quantity_bad(self):
        for bad in [0, 1000, -1, True, 2.5, "3"]:
            with self.assertRaises(ValidationError):
                v.valid_quantity(bad)

    def test_amount_ok(self):
        self.assertEqual(v.valid_amount_cents(1), 1)

    def test_amount_bad(self):
        for bad in [0, -5, 1.5, True, "10"]:
            with self.assertRaises(ValidationError):
                v.valid_amount_cents(bad)

    def test_currency_ok(self):
        self.assertEqual(v.valid_currency("usd"), "USD")
        self.assertEqual(v.valid_currency("EUR"), "EUR")

    def test_currency_bad(self):
        for bad in ["", "BTC", "us"]:
            with self.assertRaises(ValidationError):
                v.valid_currency(bad)

    def test_sku_ok(self):
        self.assertEqual(v.valid_sku("ABC-1234"), "ABC-1234")

    def test_sku_bad(self):
        for bad in ["abc-1234", "AB-1234", "ABC-123", "ABC1234", "ABCD-1234"]:
            with self.assertRaises(ValidationError):
                v.valid_sku(bad)

    def test_non_empty_ok(self):
        self.assertEqual(v.non_empty("  x "), "x")

    def test_non_empty_bad(self):
        for bad in ["", "   "]:
            with self.assertRaises(ValidationError):
                v.non_empty(bad)


if __name__ == "__main__":
    unittest.main()
''',
    "tests/test_handlers.py": '''\
import unittest
from webshop.errors import ValidationError
from webshop.handlers import (signup, order, charge, fx_quote, catalog,
                              profile, invite, refund)


class TestHandlers(unittest.TestCase):
    def test_signup(self):
        self.assertEqual(signup.signup({"email": "a@b.com"})["email"], "a@b.com")
        with self.assertRaises(ValidationError):
            signup.signup({"email": "nope"})

    def test_invite(self):
        self.assertTrue(invite.invite({"email": "x@y.org"})["ok"])
        with self.assertRaises(ValidationError):
            invite.invite({"email": "bad"})

    def test_order(self):
        self.assertEqual(order.place_order({"quantity": 5})["quantity"], 5)
        with self.assertRaises(ValidationError):
            order.place_order({"quantity": 0})

    def test_charge(self):
        self.assertEqual(charge.charge({"amount_cents": 100})["amount_cents"], 100)
        with self.assertRaises(ValidationError):
            charge.charge({"amount_cents": 0})

    def test_refund(self):
        self.assertTrue(refund.refund({"amount_cents": 50})["ok"])
        with self.assertRaises(ValidationError):
            refund.refund({"amount_cents": -1})

    def test_fx_quote(self):
        self.assertEqual(fx_quote.fx_quote({"currency": "usd"})["currency"], "USD")
        with self.assertRaises(ValidationError):
            fx_quote.fx_quote({"currency": "BTC"})

    def test_catalog(self):
        self.assertEqual(catalog.add_item({"sku": "ABC-1234"})["sku"], "ABC-1234")
        with self.assertRaises(ValidationError):
            catalog.add_item({"sku": "bad"})

    def test_profile(self):
        self.assertEqual(profile.update_profile({"display_name": "Jo"})["display_name"], "Jo")
        with self.assertRaises(ValidationError):
            profile.update_profile({"display_name": "   "})


if __name__ == "__main__":
    unittest.main()
'''
}

# Reference solution (used ONLY to self-verify solvability; never shipped).
VALIDATE_REF_VALIDATORS = '''\
import re
from webshop.errors import ValidationError

_CURRENCIES = {"USD", "EUR", "GBP", "JPY"}
_SKU = re.compile(r"^[A-Z]{3}-\\d{4}$")


def valid_email(s):
    if not isinstance(s, str):
        raise ValidationError("email must be a string")
    s = s.strip().lower()
    if s.count("@") != 1:
        raise ValidationError("email must contain exactly one @")
    local, _, domain = s.partition("@")
    if not local or "." not in domain:
        raise ValidationError("invalid email")
    return s


def valid_quantity(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValidationError("quantity must be an int")
    if not (1 <= n <= 999):
        raise ValidationError("quantity out of range")
    return n


def valid_amount_cents(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValidationError("amount must be an int")
    if n <= 0:
        raise ValidationError("amount must be positive")
    return n


def valid_currency(s):
    if not isinstance(s, str):
        raise ValidationError("currency must be a string")
    s = s.strip().upper()
    if s not in _CURRENCIES:
        raise ValidationError("unknown currency")
    return s


def valid_sku(s):
    if not isinstance(s, str) or not _SKU.match(s):
        raise ValidationError("bad sku")
    return s


def non_empty(s, field="value"):
    if not isinstance(s, str) or not s.strip():
        raise ValidationError(f"{field} must be non-empty")
    return s.strip()
'''

VALIDATE_REF_HANDLERS = {
    "webshop/handlers/signup.py": ("# TODO: validate — email must be a valid address\n    email = req[\"email\"]",
                                   "email = valid_email(req[\"email\"])", "from webshop.validators import valid_email"),
    "webshop/handlers/invite.py": ("# TODO: validate — email must be a valid address\n    email = req[\"email\"]",
                                    "email = valid_email(req[\"email\"])", "from webshop.validators import valid_email"),
    "webshop/handlers/order.py": ("# TODO: validate — quantity must be a valid quantity (1..999)\n    qty = req[\"quantity\"]",
                                  "qty = valid_quantity(req[\"quantity\"])", "from webshop.validators import valid_quantity"),
    "webshop/handlers/charge.py": ("# TODO: validate — amount_cents must be a positive integer\n    amount = req[\"amount_cents\"]",
                                   "amount = valid_amount_cents(req[\"amount_cents\"])", "from webshop.validators import valid_amount_cents"),
    "webshop/handlers/refund.py": ("# TODO: validate — amount_cents must be a positive integer\n    amount = req[\"amount_cents\"]",
                                   "amount = valid_amount_cents(req[\"amount_cents\"])", "from webshop.validators import valid_amount_cents"),
    "webshop/handlers/fx_quote.py": ("# TODO: validate — currency must be a known currency\n    cur = req[\"currency\"]",
                                     "cur = valid_currency(req[\"currency\"])", "from webshop.validators import valid_currency"),
    "webshop/handlers/catalog.py": ("# TODO: validate — sku must match the SKU pattern\n    sku = req[\"sku\"]",
                                     "sku = valid_sku(req[\"sku\"])", "from webshop.validators import valid_sku"),
    "webshop/handlers/profile.py": ("# TODO: validate — display_name must be non-empty\n    name = req[\"display_name\"]",
                                     "name = non_empty(req[\"display_name\"], \"display_name\")", "from webshop.validators import non_empty"),
}


def gen_feature_validate():
    fixture = OUT / "validate-feature"
    if fixture.exists():
        shutil.rmtree(fixture)
    write(fixture / "webshop/__init__.py", "")
    write(fixture / "webshop/errors.py",
          "class ValidationError(Exception):\n    pass\n")
    write(fixture / "webshop/handlers/__init__.py", "")
    for rel, text in _vfile_handlers().items():
        write(fixture / rel, text)
    for rel, text in VALIDATE_TESTS.items():
        write(fixture / rel, text)
    write(fixture / "SPEC.md", VALIDATE_SPEC)
    write(fixture / "README.md", "# webshop\n\nSee SPEC.md for the task.\n")

    # Ships RED (validators module missing).
    rc, passed, total = run_suite(fixture)
    assert rc != 0, f"validate-feature unexpectedly green at ship: {passed}/{total}"
    shipped_passed = passed

    # Freeze tests.
    frozen = {rel: sha(fixture / rel) for rel in VALIDATE_TESTS if rel.startswith("tests/")}

    # Self-verify solvability with the reference solution on a COPY.
    refdir = OUT / "_validate-ref-check"
    if refdir.exists():
        shutil.rmtree(refdir)
    shutil.copytree(fixture, refdir)
    write(refdir / "webshop/validators.py", VALIDATE_REF_VALIDATORS)
    for rel, (find, repl, imp) in VALIDATE_REF_HANDLERS.items():
        p = refdir / rel
        src = p.read_text()
        assert find in src, f"handler anchor not found in {rel}"
        src = src.replace("from webshop.errors import ValidationError  # noqa: F401",
                          "from webshop.errors import ValidationError  # noqa: F401\n" + imp, 1)
        src = src.replace(find, repl, 1)
        p.write_text(src)
    rc, passed, total = run_suite(refdir)
    assert rc == 0 and passed == total and total > 0, \
        f"reference validate solution NOT green: {passed}/{total}\n"
    shutil.rmtree(refdir)
    print(f"  validate-feature: shipped RED {shipped_passed}/{total}, ref GREEN {total}/{total}")

    write(TRUTH / "code-feature-validate-py.json",
          json.dumps({"frozen_test_hashes": frozen, "total_tests": total}, indent=2))
    _write_task(
        "code-feature-validate-py",
        title="Implement a validators module + wire it into 8 handlers",
        fixture="validate-feature",
        max_turns=60, timeout_s=1800,
        prompt='''\
Implement the feature described in `SPEC.md` completely. The test suite
under `tests/` is currently failing; make it pass:

    python3 -m unittest discover -s tests -t .

Do NOT modify anything under `tests/`. In your final reply, list the files
you changed or created.
''',
        verify='''\
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _vlib import WS, emit, hashes_intact, run, truth

t = truth("code-feature-validate-py.json")
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
''',
    )


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


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    TRUTH.mkdir(parents=True, exist_ok=True)
    print("generating long autonomous-dev bench tasks...")
    gen_debug_ledger()
    gen_feature_validate()
    print("done.")
