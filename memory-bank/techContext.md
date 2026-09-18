# Tech Context

## Language & Runtime

- **Python 3.10–3.14** (Odoo 18.0). `requirements.txt` pins versions per Python version; Docker image uses `python:3.12-slim`. `setup.py` declares `python_requires='>=3.10'`.
- **JavaScript (ES6+)** for the web client, using Odoo's own **OWL** component framework — no separate npm-based build pipeline; JS/SCSS/XML assets are declared and bundled via Odoo's internal asset-bundle system (`__manifest__.py` `assets` dict → `web.assets_backend`, `web.assets_frontend`, etc.), not webpack/vite.
- **XML** (views, QWeb templates, data files) and **SQL** are core "languages" throughout addons.

## Frameworks

- **Odoo ORM/framework itself** (`odoo/models.py`, `fields.py`, `api.py`) — the primary business/web framework.
- **Werkzeug** — WSGI layer / HTTP routing underlying `odoo/http.py`.
- **QWeb** — server-side XML templating engine (views, reports, emails).
- **OWL** (Odoo Web Library) — component-based JS framework for the web client.
- **Testing**: Python's built-in `unittest`, wrapped by Odoo's own base classes in `odoo/tests/common.py` (`BaseCase` → `TransactionCase` → `HttpCase`), plus `freezegun` for time mocking.
- **Jinja2** used alongside QWeb in some templating/email contexts.

## Key Libraries

- **DB**: `psycopg2` (PostgreSQL driver)
- **Async**: `gevent`/`greenlet` (worker model for long-polling/cron)
- **XML/HTML**: `lxml`
- **Documents/Reports**: `reportlab`, `PyPDF2`/`PyPDF`, `openpyxl`, `XlsxWriter`, `xlrd`, `xlwt`, `Pillow`
- **Security**: `cryptography`, `pyOpenSSL`, `passlib`, `asn1crypto`
- **i18n**: `Babel`, `num2words`, `python-stdnum`
- **Integrations**: `zeep` (SOAP), `requests`/`urllib3`, `qrcode`, `vobject`, `geoip2`, `polib`, `pyserial`/`pyusb` (POS hardware), `ofxparse` (bank statement import), `python-ldap` (optional extra)
- **Assets**: `libsass`, `rjsmin` (server-side style/JS compilation); `npm`-installed `rtlcss`/`node-less` inside the Docker image for RTL CSS support only — not a full JS toolchain

## Build / Package Management

- **pip** + `requirements.txt` (version-pinned per Python version, targeting Ubuntu/Debian system packages) — primary dependency management
- **setuptools** via `setup.py`/`setup.cfg` (packages the `odoo` library)
- No root JS build tool (no webpack/vite/rollup config) — Odoo bundles JS/CSS internally via its asset-bundle system
- **npm** used only inside the Docker image, for `rtlcss` and `node-less`/`libsass`

## Database / Storage

- **PostgreSQL 16** — the only supported RDBMS (`psycopg2` driver; `docker-compose.yml` uses `postgres:16`)
- **Filestore** — Odoo's own filesystem-based attachment storage (`odoo-filestore` volume in docker-compose, mounted to `/var/lib/odoo`)
- No other DB/cache technology (no Redis/Elasticsearch config at repo root)

## Infrastructure

- **Docker**: root `Dockerfile` builds from `python:3.12-slim`, installs system build deps (build-essential, libxml2/libxslt/libldap/libsasl2/libssl/libjpeg/libpq/libffi/zlib headers), Node.js tooling (`npm`, `node-less`, global `rtlcss`), wkhtmltopdf-adjacent fonts; installs Python deps from `requirements.txt`; exposes port 8069; runs `odoo-bin`.
- **Docker Compose** (`docker-compose.yml`): two services —
  - `db`: `postgres:16`, creds `odoo`/`odoo`, volume `pg-data`
  - `odoo`: builds from root `Dockerfile`, depends on `db`, port `8069:8069`, mounts `./docker/odoo.conf` read-only, volume `odoo-filestore` for `/var/lib/odoo`
  - `develop.watch` block: `sync+restart` on `./addons` → `/opt/odoo/addons` and `./odoo` → `/opt/odoo/odoo`; `rebuild` on `requirements.txt` changes. `PYTHONDONTWRITEBYTECODE=1` avoids stale bytecode during live dev.
- No Kubernetes manifests in the repo.

## Development Commands

- **Run locally (direct)**: `python odoo-bin -c <config-file>` (e.g. `python odoo-bin -c docker/odoo.conf`). Common flags: `-d <db>` (database), `-u <module>` (update), `-i <module>` (install), `--addons-path=...`, `--dev=reload` (autoreload).
- **Run via Docker (first time)**: `docker compose up --build`
- **Run via Docker (live dev)**: `docker compose watch` — syncs `./addons`/`./odoo` into the container with restart-on-change; rebuilds only when `requirements.txt` changes
- **Config**: `docker/odoo.conf` (INI-style, mounted read-only to `/etc/odoo/odoo.conf`) — sets `addons_path`, `data_dir`, `admin_passwd`, `db_host`/`db_port`/`db_user`/`db_password`, `dev_mode = reload`. Config-file driven, not primarily env-var driven; the only env var used directly is `PYTHONDONTWRITEBYTECODE=1` in compose.

## Test Strategy

- **Framework**: Odoo's built-in unittest-based test runner, invoked via `odoo-bin` flags — no separate `pytest`/`tox` setup.
- **Key flags** (`odoo/tools/config.py`):
  - `--test-enable` — enable test mode
  - `--test-tags <spec>` — select tests (e.g. `--test-tags :TestClass.test_func,/test_module,external` or `--test-tags /web.test_js[mail]`)
  - `--test-file <path>` — run a specific test file
- **Typical invocation**: `python odoo-bin -c docker/odoo.conf -d <db> --test-enable --test-tags /module_name --stop-after-init`
- No dedicated test docker-compose service — tests run via the same `odoo` container/CLI against `db`.
- See `systemPatterns.md` § Testing Patterns for test organization, naming, and tagging conventions.

## Linting / Formatting

- `setup.cfg` at repo root configures **flake8** only (no `pyproject.toml`, no black/isort, no pre-commit config found):
  - `extend-exclude = .git, .tx, debian, doc, setup`
  - `extend-select = RST` (flake8-rst-docstrings checks) with explicit allow-lists for RST directives/roles (`seealso`, `deprecated`, `versionadded`, `ref`, `mod`, `class`, `meth`, `attr`, etc.)
- Run `flake8` from repo root. Docstrings should use valid RST directives/roles per the allow-list.
- No `.editorconfig` found in this checkout.

## CI/CD

- No GitHub Actions workflows in this repo snapshot (`.github/` contains only issue templates and a PR template — community contribution scaffolding, not automation).
- **Weblate** (`.weblate.json` at root) handles translation management, external to any CI pipeline.
