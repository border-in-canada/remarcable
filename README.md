# Product Catalog

A Django take-home project for browsing products by description, category, and
tags, using server-rendered Django templates and SQLite.

## Status

The Django project (`config`) and the `products` app are scaffolded, with
linting, formatting, and pre-commit hooks configured. Models, admin
configuration, and the search page are added in later changes.

## Prerequisites

- Python 3.12
- [Poetry](https://python-poetry.org/) 2.x

The `.tool-versions` file pins Python and Poetry for [asdf](https://asdf-vm.com/).
Any other way of providing Python 3.12 and Poetry works equally well.

## Setup

From the project root:

```sh
cp .env.example .env   # or use the .env file you were given
poetry install
poetry run python manage.py migrate
poetry run python manage.py runserver
```

If you copied `.env.example`, set `DJANGO_SECRET_KEY` in `.env` to a long random
string. The project will not start without it.

The site is served at <http://127.0.0.1:8000/> and the Django admin at
<http://127.0.0.1:8000/admin/>. Create an administrator account with:

```sh
poetry run python manage.py createsuperuser
```

## Working with Poetry

Poetry manages the virtual environment and the dependencies. You do not need to
create or activate a virtual environment yourself.

- **Environment:** `poetry install` creates `.venv/` in the project (configured
  by `poetry.toml`) and installs the exact versions in `poetry.lock`, including
  the development tools. Run `poetry env info` to see which environment and
  Python Poetry is using.
- **Running commands:** prefix them with `poetry run`, for example
  `poetry run python manage.py test`. Every command in this README assumes this.
- **Optional shell activation:** `eval "$(poetry env activate)"` activates the
  environment in your current shell, after which you can drop the `poetry run`
  prefix. Use `deactivate` to leave it. Deactivate any other virtual
  environment first, or Poetry will use that one instead of `.venv/`.
- **Dependencies:** they are declared in `pyproject.toml` and locked in
  `poetry.lock`. This is an application, not a package, so `poetry install`
  only installs dependencies.

```sh
poetry add <package>               # add a runtime dependency
poetry add --group dev <package>   # add a development tool
poetry update <package>            # upgrade one dependency within its constraint
poetry lock                        # refresh poetry.lock after editing pyproject.toml
poetry install                     # sync the environment with poetry.lock
```

Commit `pyproject.toml` and `poetry.lock` together whenever a dependency changes.

## Configuration

Settings are for local development only (`DEBUG = True`, SQLite database
`db.sqlite3`, ignored by Git). Secrets are read from environment variables. A
`.env` file in the project root is loaded automatically; real environment
variables take precedence. `.env` is ignored by Git, and `.env.example` lists
the variables to set:

| Variable            | Purpose                      |
| ------------------- | ---------------------------- |
| `DJANGO_SECRET_KEY` | Django cryptographic signing |

## Linting and formatting

| Tool                                   | Purpose                                |
| -------------------------------------- | -------------------------------------- |
| [Black](https://black.readthedocs.io/) | Python formatting                      |
| [Ruff](https://docs.astral.sh/ruff/)   | Python linting and import ordering     |
| [djLint](https://djlint.com/)          | Django template formatting and linting |

Black is the only Python formatter; Ruff's formatter is not used. Settings live
in `pyproject.toml`, and tool versions come from `poetry.lock`. Run the tools
directly with:

```sh
poetry run ruff check --fix .
poetry run black .
poetry run djlint --reformat --lint products/templates   # once templates exist
```

### Pre-commit hooks

Hooks run on staged files at commit time and also check whitespace, file
endings, YAML/TOML/JSON syntax, and merge-conflict markers. Install them once
per clone, after `poetry install`:

```sh
poetry run pre-commit install
poetry run pre-commit run --all-files   # optional: check the whole project
```

The Black, Ruff, and djLint hooks are local hooks that call `poetry run`, so
they use the versions in `poetry.lock`. This means `poetry` must be on the
`PATH` that Git sees, and `poetry install` must have been run. The first run
downloads the environment for the file-check hooks and needs network access.

If a hook changes files, the commit is aborted so you can review the changes,
stage them again, and retry the commit. Lint errors that cannot be fixed
automatically also abort the commit. Hooks do not run the test suite.

To avoid aborted commits, apply the fixes before staging: run
`poetry run pre-commit run --all-files`, or format on save in your editor.
`.editorconfig` makes editors that support it add a final newline and trim
trailing whitespace, and Black and Ruff editor integrations handle Python.

## Checks

```sh
poetry run python manage.py check
poetry run python manage.py test
```
