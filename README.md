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
poetry run python manage.py loaddata sample_data   # optional sample catalog
poetry run python manage.py runserver
```

If you copied `.env.example`, set `DJANGO_SECRET_KEY` in `.env` to a long random
string. The project will not start without it. After `poetry install`, you can
generate one with:

```sh
poetry run python -c "from django.core.management.utils import get_random_secret_key as key; print(key())"
```

The product page is at <http://127.0.0.1:8000/> and the Django admin at
<http://127.0.0.1:8000/admin/>. Create an administrator account with:

```sh
poetry run python manage.py createsuperuser
```

### Sample data

The project includes a sample catalog of 5 categories, 10 tags, and 20 products.
It was entered by hand through the Django admin and exported to
`products/fixtures/sample_data.json`. To load it into a freshly migrated
database:

```sh
poetry run python manage.py loaddata sample_data
```

The fixture is meant for a fresh database: it keeps the original primary keys, so
loading it into a database that already has data overwrites rows with the same
keys. It contains only the `products` app, with no users or sessions. To
regenerate it after editing the data in the admin:

```sh
poetry run python manage.py dumpdata products --indent 2 --output products/fixtures/sample_data.json
```

## Assumptions

- Each product belongs to exactly one category and has any number of tags,
  including none.
- Categories and tags are global: staff manage them in the admin, and visitors
  can only filter by them. Names are unique ignoring case.
- Search matches product descriptions only, as the assignment states, using a
  case-insensitive substring match.
- The search, category, and tag filters combine with AND. Tags can match any or
  all of the selected tags, and the page offers both.
- Results are paginated at ten per page, ordered by name.
- The app is for local use: SQLite, `DEBUG` on, and no front-end build step.
  Scaling notes below cover what would change for a larger catalog.

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

For example, with the sample data loaded,
`?q=board&category=1&tags=3&tags=5&tag_mode=all` finds products in the Kitchen
category (ID 1) whose description contains "board" and that have both the `gift`
(ID 3) and `sale` (ID 5) tags: the Bamboo Cutting Board.

The validation lives in `ProductFilterForm` (`products/forms.py`) and the
queries in `filter_products` (`products/querysets.py`).

## Product page

The page at `/` is a plain Django template (`products/templates/products/`)
with a little CSS and no JavaScript, so there is no front-end build step. It
lists products with their description, category, and tags, ten to a page.

The filter form at the top uses a GET request, so every search has a shareable
URL. It has a search box, a category dropdown, a checkbox per tag, "Any" and
"All" radio buttons, a Search button, and a Reset link that clears everything.
The form keeps the submitted values after a search, and the page shows how many
products matched, or a message when none do.

If a filter value is invalid, the page shows the error next to the field and
lists no products instead of ignoring the bad value.

### Pagination

Results are paginated with Django's `Paginator`, ten products per page
(`PAGE_SIZE` in `products/views.py`). The `page` query parameter selects the
page, and results are ordered by name and then primary key, so products never
move between pages or appear twice.

- The Previous and Next links and the numbered links keep every filter, including
  repeated `tags` values, and change only `page`. Long page lists are shortened
  with an ellipsis.
- A new search starts at page 1, because the form does not submit a page number.
- A missing or non-numeric `page` shows page 1, and a number outside the range
  shows the last page.
- The links are hidden when everything fits on one page.

A page is served with three queries for products, however many products match:
the total count, the page of products with their category, and the tags for
those products. The form's category and tag choices add one query each.

The docstring on the `product_list` view describes how to add user-selectable
ordering safely. Comments in the view and in `products/forms.py` explain why
nothing is cached yet and when caching would be worth adding.

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
- **Filter form lists:** they are loaded from the database on each request. That
  is two small indexed queries, so caching them is not worth it here. Consider it
  only if profiling shows they matter, for example with a remote database under
  heavy traffic. Use a shared cache and clear it when tags or categories change,
  including bulk changes, which skip Django signals.
- **Result caching:** results are not cached. The filter, tag mode, and page
  combinations are many, so hit rates would be low, and stale results cost more
  than the queries save.
- **Pagination:** page numbers need an exact count, and `OFFSET` gets slower on
  deep pages. Use keyset pagination, or drop the total, for very large results.

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
poetry run djlint --reformat --lint products/templates
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
poetry run pre-commit run --all-files
poetry run python manage.py check
poetry run python manage.py makemigrations --check --dry-run
poetry run python manage.py test
```

`makemigrations --check` fails if a model change is missing its migration.

## AI Usage

I used an AI coding assistant while building this project, for:

- **Project scaffolding:** The Django project and app boilerplate.
- **Documentation:** Drafting and editing this README.
- **Product ideas:** Suggestions for the sample categories, tags, and products.

The design decisions (such as global tags, tag matching, SQLite, Poetry, code comments and performance considerations) were all my own.
