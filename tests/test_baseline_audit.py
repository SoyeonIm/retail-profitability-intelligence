"""Tests for baseline audit invariants; known pre-opening issue is reported, not hidden."""
import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from audit_baseline import audit


def test_baseline_keys_and_amounts():
    with duckdb.connect(str(ROOT / 'data' / 'retail.duckdb'), read_only=True) as con:
        findings = audit(con)
    assert findings['Duplicate store-month keys'] == 0
    assert findings['Missing store references'] == 0
    assert findings['Missing financial amounts'] == 0
    assert findings['Negative or invalid sales/COGS'] == 0


def test_preopening_issue_is_measured():
    with duckdb.connect(str(ROOT / 'data' / 'retail.duckdb'), read_only=True) as con:
        findings = audit(con)
    assert isinstance(findings['Pre-opening financial rows'], int)
    assert findings['Pre-opening financial rows'] >= 0
