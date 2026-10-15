# Product Catalog

A Django take-home project for browsing products by description, category, and
tags, using server-rendered Django templates and SQLite.

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

The Django admin is at <http://127.0.0.1:8000/admin/>. Create an administrator
account with:

```sh
poetry run python manage.py createsuperuser
```

## Data model

| Model      | Fields                                                              |
| ---------- | ------------------------------------------------------------------- |
| `Category` | `name` (unique, ignoring case)                                      |
| `Tag`      | `name` (unique, ignoring case)                                      |
| `Product`  | `name`, `description`, `category` (required), `tags` (zero or more) |

A product belongs to exactly one category and can have any number of tags.
A category that still has products cannot be deleted, so products are never left
without a category; remove or reassign its products first. Categories and tags
are ordered by name, and products by name then primary key so the order is
always stable.

## Admin

Add categories and tags first, then products, at
<http://127.0.0.1:8000/admin/>. The product list can be filtered by category
and searched by name, description, or tag name. Tags are chosen on the product
form with a search box, so the form stays usable with many tags.

## Search and filtering

Products are searched and filtered with these inputs, which can be combined:

| Input     | Query parameter | Behavior                                            |
| --------- | --------------- | --------------------------------------------------- |
| Search    | `q`             | Case-insensitive substring match on the description |
| Category  | `category`      | Products in the chosen category                     |
| Tags      | `tags`          | One or more tags, repeated in the query string      |
| Tag match | `tag_mode`      | `any` (default) or `all`, used when tags are set    |

- **All inputs are optional.** An empty or missing input is ignored, so a request
  with no inputs matches every product.
- **Inputs combine with AND.** A product must satisfy the search, the category,
  and the tag condition together.
- **Search covers descriptions only.** Product names are not searched, and
  leading and trailing whitespace in the search text is ignored.
- **Tag match.** With `any`, a product matches if it has at least one selected
  tag. With `all`, it must have every selected tag. A product is listed once
  however many selected tags it has. A missing `tag_mode` means `any`.
- **Invalid values are rejected, not ignored.** An unknown category or tag ID, a
  malformed ID, or an unsupported `tag_mode` makes the filter form invalid.

For example, `?q=boils&category=1&tags=2&tags=3&tag_mode=all` finds products in
category 1 whose description contains "boils" and that have both tag 2 and tag 3.

The validation lives in `ProductFilterForm` (`products/forms.py`) and the
queries in `filter_products` (`products/querysets.py`). The product page that
uses them is added in a later change.

## Scaling notes

This is a take-home project, so it favors simplicity and is sized for a catalog
of thousands of products, not millions. What would change first at larger scale:

- **Description search:** it is a substring match (`LIKE '%text%'`), which scans
  every row. Use PostgreSQL full-text search, or `pg_trgm` with a GIN index.
- **Database:** SQLite needs no setup. Use PostgreSQL for search and concurrency.
- **Tag and category pickers:** every tag and category is listed. Use type-ahead
  lookups instead.
- **All-tags matching:** it joins the tag table once per selected tag. A single
  join with `GROUP BY` and `HAVING COUNT` scales better.
- **Filter form lists:** they are loaded from the database on each request. Cache
  them, and clear the cache when tags or categories change.

Any-tag matching already uses an `Exists` subquery, which returns each product
once without a join or `DISTINCT`. The database already indexes the category
foreign key and both sides of the tag relationship. Tags are shared by all
products and managed by staff in the admin; visitors cannot create them.

Before changing a query for performance, check the generated SQL and the
database's plan with `str(queryset.query)` and `queryset.explain()`.

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
