# Github Copilot Rules for this Repository

**Path Management:** Never use hardcoded absolute file paths (e.g. `:\Users\...`). Always use `pathlib.Path` relative to project root or import settings from `src.config`.
**Schema Consistency:** Shared data models live strictly in `src\models.py`. Do not re-define Pydantic schemas in route or client files.
**Environment & Secrets:** Load all configuration variables using `python-dotenv` or `pydantic-settings` from `.env`.
**Style & Scope:** Provide concise, targeted code snippets. Do not rewrite full files unless explicitly requested.