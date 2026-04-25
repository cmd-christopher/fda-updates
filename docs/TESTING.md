<!-- generated-by: gsd-doc-writer -->
# Testing

## Test Framework and Setup

The project uses Python's built-in **`unittest`** framework — no third-party testing libraries are required. Tests are organized as standalone scripts in the project root, each named `test_*.py` and importing the module under test (`fda_approvals`) directly.

No additional setup is needed beyond having Python 3 and the project's standard library dependencies available. There are no `pyproject.toml`, `setup.py`, or `requirements.txt` files — the project relies only on Python standard library modules.

## Running Tests

**Run the full test suite (all test files):**

```bash
python3 -m unittest test_slugify.py test_cache.py test_fetch_label.py test_fda_approvals_llm.py
```

**Run a single test file:**

```bash
python3 test_slugify.py
python3 test_cache.py
python3 test_fetch_label.py
python3 test_fda_approvals_llm.py
```

**Run with verbose output:**

```bash
python3 -m unittest -v test_slugify.py
```

There are no test configuration files (no `pytest.ini`, `conftest.py`, or `setup.cfg`), and no test runner scripts in the project.

## Writing New Tests

New test files follow the `test_*.py` naming convention in the project root directory. Each test file:

- Uses `unittest.TestCase` base class
- Imports `fda_approvals` (or `build.py` functions) directly
- Can be run standalone via `python3 test_<name>.py`
- Is self-contained — uses `unittest.mock` for external dependencies (HTTP calls to the FDA API, `time.sleep`)

Example pattern from existing tests:

```python
#!/usr/bin/env python3
"""Unit tests for <feature> in fda_approvals.py."""

import unittest
from unittest.mock import patch

import fda_approvals

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        result = fda_approvals.my_function("input")
        self.assertEqual(result, "expected")

if __name__ == "__main__":
    unittest.main()
```

For tests involving FDA API calls, mock `fda_approvals.urlopen` and `fda_approvals.time.sleep` to avoid real network requests and delays:

```python
@patch('fda_approvals.urlopen')
@patch('fda_approvals.time.sleep')
def test_api_call(self, mock_sleep, mock_urlopen):
    mock_urlopen.side_effect = ...
```

Test data fixtures are stored as JSON files in `data/` (e.g., `data/test_nme.json`, `data/test_indication.json`).

## Coverage Requirements

No coverage threshold is configured. There is no `.coveragerc`, `pytest-cov` configuration, or `coverage` setup in the project.

## CI Integration

No CI pipeline is configured. There are no `.github/workflows/` files or other CI configuration files in the repository. Tests are run manually by the developer.

The weekly deployment pipeline (`run_fda_pipeline.sh`) does not include a test step — it runs `fda_approvals.py` and `build.py` directly and deploys to the Synology NAS on success.