<!-- generated-by: gsd-doc-writer -->

# Development

## Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/cmd-christopher/fda-updates.git
   cd fda-updates
   ```

2. **Ensure Python 3.14+ is available.** The project uses standard library modules only for the data fetching script (`fda_approvals.py`). The site builder (`build.py`) requires two additional packages:
   ```bash
   pip install jinja2 markupsafe
   ```

3. **Create the data directory** (used for cached output and label data):
   ```bash
   mkdir -p data
   ```

4. **Optional — Configure environment variables** for the full pipeline. Copy or create `~/.config/fda-pipeline/.env` with Pushover notification keys and the LLM API key (see [CONFIGURATION.md](CONFIGURATION.md) for details).

5. **Verify the setup** with a quick test run that skips the slow label-fetching step:
   ```bash
   python3 fda_approvals.py --from 2026-03-01 --to 2026-04-22 --type nme --skip-labels
   ```

## Build Commands

| Command | Description |
|---------|-------------|
| `python3 fda_approvals.py --from DATE --to DATE` | Fetch drug approval data from openFDA (full run with label enrichment) |
| `python3 fda_approvals.py --from DATE --to DATE --skip-labels` | Quick fetch without label data (fastest) |
| `python3 fda_approvals.py --from DATE --to DATE --cache` | Incremental fetch — reuses cached labels from previous runs |
| `python3 fda_approvals.py --from DATE --to DATE --summarize` | Fetch with LLM-generated concise indication summaries |
| `python3 build.py` | Build the static site from `data/approvals.json` into `site/` |
| `bash run_fda_pipeline.sh` | Full pipeline: fetch → build → deploy to Synology |
| `python3 -m unittest discover -s . -p 'test_*.py'` | Run all unit tests |
| `python3 -m unittest test_slugify.py` | Run slugify tests alone |
| `python3 -m unittest test_cache.py` | Run label cache tests alone |
| `python3 -m unittest test_fetch_label.py` | Run fetch_label HTTP error tests alone |
| `python3 -m unittest test_fda_approvals_llm.py` | Run LLM summarization fallback tests alone |

## Code Style

The project follows **PEP 8** conventions for Python. No formal linting or formatting tools are configured in the repository.

- **No linter config found** — there are no `.flake8`, `pyproject.toml` linting sections, `ruff.toml`, or `mypy.ini` files in the project.
- **No formatter config found** — there are no `black`, `isort`, or `autopep8` configuration files.
- **Conventions observed in the codebase:** 4-space indentation, 79–99 character line length, descriptive function and variable names, docstrings on public functions.

## Branch Conventions

The default branch is `main`. Remote branches follow a loose prefix naming pattern:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `add/` | New feature or test additions | `add-fetch-label-http-error-tests-*` |
| `fix/` | Bug fixes | `fix/command-injection-*` |
| `perf-` | Performance improvements | `perf-parallel-label-fetching-*` |
| `testing-` | Test coverage improvements | `testing-improvement-llm-fallback-*` |

Feature branches are merged into `main` via GitHub pull requests. No formal branch naming rules are documented.

## PR Process

No PR template or formal contribution guidelines exist in the repository. Based on the observed workflow:

- Create a feature branch from `main` with a descriptive name using one of the prefixes above.
- Open a pull request on GitHub against `main`.
- Ensure existing tests pass (`python3 -m unittest discover -s . -p 'test_*.py'`).
- Add tests for any new functionality.
- The maintainer reviews and merges.