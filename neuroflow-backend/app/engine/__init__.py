"""The execution engine. Runs only in worker processes -- `app.api`/
`app.main` must never import this package, enforced by the import-linter
contract in `pyproject.toml`. See docs/12-execution-engine.md.
"""
