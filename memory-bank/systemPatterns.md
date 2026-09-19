# System Patterns

## Guiding Principles

| Principle | Manifestation |
|---|---|
| ORM abstraction over raw SQL | All persistence goes through `odoo/models.py` (`BaseModel`), `odoo/fields.py`, `odoo/api.py`; business code almost never writes raw SQL — `cr.execute` is a discouraged escape hatch |
| Modules are the unit of deployment | Every addon is self-contained under `addons/<name>/` with a `__manifest__.py` declaring identity, `depends`, `data`, `assets` |
| Explicit dependency graph | The `depends` key in each manifest drives load order (`odoo/modules/graph.py`, `loading.py`); a module may not reference another's models/views without declaring the dependency |
| Inheritance over modification | Existing models/views are extended via `_inherit` (never edit another module's file directly) — Odoo's core extensibility mechanism |
| Security is declarative | `ir.model.access.csv` (model-level CRUD by group) + `ir_rules.xml` (record-level domains) are mandatory per addon touching data |
| Convention-based directory shape | `models/`, `views/`, `controllers/`, `security/`, `data/`, `static/`, `tests/`, `i18n/`, `wizard/`, `report/` — the same skeleton recurs across all 621 addons |
| Transactional test isolation | Tests run inside a DB transaction that is rolled back (`TransactionCase`), never touching real data |
| Backend/frontend split, co-versioned | Python ORM/business logic is server-side; OWL (JS) + SCSS frontend ships inside the same addon's `static/src/` |
| License/copyright header discipline | Nearly every file starts with `# Part of Odoo. See LICENSE file for full copyright and licensing details.` |

## Architecture Overview

- `odoo/` — the **framework core**: ORM engine, HTTP layer, CLI, service layer, tooling. Imported as the `odoo` Python package.
- `odoo/addons/base/` — a special core addon bundled inside the framework package itself (defines `ir.*` meta-models: `ir_model`, `ir_actions`, `ir_cron`, `ir_attachment`, plus base security groups). Nearly every other addon depends on `base` transitively.
- `addons/` (repo root, sibling to `odoo/`) — the 621 business addon modules (accounting, sales, CRM, web client, etc.), loaded by the framework via the addons path; depend on `base` and each other via manifests.

### Standard Addon Shape

```
addon_name/
  __init__.py
  __manifest__.py       # metadata, depends, data, assets
  models/                # ORM model definitions (_name/_inherit)
  views/                 # XML view/action definitions
  controllers/           # HTTP route handlers (odoo.http.Controller)
  security/              # ir.model.access.csv, ir_rules.xml, res_groups.xml
  data/                  # XML/CSV seed data (cron jobs, sequences, templates)
  wizard/                # transient models (multi-step user actions)
  report/                # QWeb reports / report models
  static/src/            # JS (OWL components), XML (QWeb templates), SCSS
  static/tests/          # JS unit/tour tests
  tests/                 # Python test suite
  i18n/                  # .po translation files
```

`addons/web` is the reference frontend framework module (no models/security — pure UI framework); `addons/sale` is a full business module exhibiting every directory kind including `wizard/` and `report/`.

## Entry Points

- `odoo-bin` — top-level executable (sets `TZ=UTC`, calls `odoo.cli.main()`)
- `odoo/__main__.py` — allows `python -m odoo`
- `odoo/cli/` — CLI subcommand dispatch (server, shell, scaffold, etc.)
- `odoo/service/` — process/service layer: `server.py` (WSGI/worker server), `db.py`, `model.py`, `security.py`, `common.py` (XML-RPC/JSON-RPC service registrations)
- `odoo/http.py` (~2600 lines) — WSGI application, request/response objects, routing/dispatch (`Application`, `Request`, `Response`, `Dispatcher`, `HttpDispatcher`, `JsonRPCDispatcher`), the `Controller` base class + `@route()` decorator, session handling
- `odoo/modules/` — module lifecycle: `loading.py` (load order/bootstrap), `graph.py` (dependency graph), `registry.py` (in-memory model registry per DB), `module.py` (manifest parsing/discovery), `migration.py`

## Core Framework Modules

- `odoo/models.py` (~7600 lines) — the ORM: `BaseModel`, CRUD, recordset semantics, `_name`/`_inherit`/`_inherits` mechanics, compute/onchange machinery, caching
- `odoo/fields.py` (~5400 lines) — field type definitions (`Char`, `Many2one`, `One2many`, `Selection`, computed/related fields, `Command` helper for x2many writes)
- `odoo/api.py` (~1580 lines) — decorators/environment: `@api.model`, `@api.depends`, `@api.onchange`, `@api.constrains`, `Environment`/`self.env` context propagation
- `odoo/modules/registry.py` — per-database `Registry` holding the compiled/merged model classes after applying all `_inherit` chains across installed modules
- `odoo/tools/` — utilities: `safe_eval.py` (sandboxed eval for domains/expressions), `convert.py` (XML data-file importer), `translate.py`/`i18n.py`, `query.py`/`sql.py`, `cache.py`, `mail.py`, `view_validation.py`, `template_inheritance.py` (view XPath merging), `image.py`
- `odoo/tests/` — testing framework (see Testing Patterns below)

## API / Controllers / RPC

- Controllers subclass `odoo.http.Controller`, use `@route(route, type='http'|'json', auth=..., methods=..., csrf=...)` to expose endpoints
- Dispatch: `Application` → `Dispatcher` subclasses `HttpDispatcher` (form/query-string HTTP) and `JsonRPCDispatcher` (the primary API/RPC protocol used by the web client and external integrations)
- `request` (thread/context-local, `odoo.http.request`) exposes `request.env['model.name']` for ORM access inside controllers — the same environment/recordset API used everywhere else
- Controllers commonly extend other addons' controllers via subclassing (mirrors model `_inherit` at the controller layer)
- Legacy/external XML-RPC served through `odoo/service/{common,model,db}.py`

## Data Layer / ORM Model Inheritance

- Models declared as Python classes with `_name = 'model.name'` and optionally `_inherit = [...]` (mixins/parents combined by the registry)
- Extending an *existing* model without a new table: set `_inherit = 'existing.model'`, omit `_name` — the registry merges fields/methods into the same underlying table. This is the pervasive extensibility mechanism across addons.
- `_inherits` (delegation inheritance) is a distinct "has-a" composition mechanism with automatic field proxying
- `ir.model`, `ir.model.fields`, `ir.model.access`, `ir.rules` (in `odoo/addons/base/models/`) are meta-models — every user-defined model is introspectable/configurable through them at runtime
- Access control is two-layered per addon:
  - `security/ir.model.access.csv` — coarse CRUD permission per model per security group (`perm_read`/`write`/`create`/`unlink`)
  - `security/ir_rules.xml` — row-level domain filters (record rules)
  - `security/res_groups.xml` — defines the referenced security groups

## Code Organization Patterns

**Primary languages**: Python (backend, `.py`); for the web client, JS/OWL (`.js`, a small growing `.ts` subset), QWeb XML templates (`.xml`), SCSS (`.scss`).

`addons/web/static/src` file-type census: 472 `.js`, 232 `.xml`, 182 `.scss`, 15 `.ts` — confirming JS+XML+SCSS as the dominant frontend trio, with TypeScript adopted only in a small, newer subset.

**Extension by directory/role:**

| Directory | Dominant file type(s) | Role |
|---|---|---|
| `odoo/` (core) | `.py` | ORM engine, HTTP layer, CLI, services |
| `<addon>/models/` | `.py` | ORM model classes (`_name`/`_inherit`) |
| `<addon>/controllers/` | `.py` | HTTP/JSON-RPC route handlers |
| `<addon>/wizard/` | `.py` + `.xml` | Transient models for multi-step user actions |
| `<addon>/report/` | `.py` + `.xml` | Printable/PDF reports (QWeb) |
| `<addon>/views/` | `.xml` | Backend view/action/menu definitions |
| `<addon>/data/`, `demo/` | `.xml`, `.csv` | Seed/demo records |
| `<addon>/security/` | `.csv`, `.xml` | Access rights, record rules, groups |
| `<addon>/static/src/` | `.js`/`.ts`, `.xml`, `.scss` | Frontend UI (OWL components, QWeb templates, styles) |
| `<addon>/static/tests/` | `.js` | Frontend unit/tour tests |
| `<addon>/tests/` | `.py` | Backend test suite |
| `<addon>/i18n/` | `.po` | Translations |

**New-addon module shape**: `__init__.py`, `__manifest__.py` (name/version/category/depends/data/assets/license/hooks) plus whichever of `models/ views/ controllers/ security/ data/ static/ tests/ i18n/ wizard/ report/` the module needs. The manifest's `assets` dict maps bundle names (`web.assets_backend`, `web.assets_frontend`, `web.assets_tests`, `web.assets_unit_tests`) to static file lists/globs — this is how JS/SCSS/XML get wired into the web client per-addon.

## Testing Patterns

- **Location**: Co-located per addon in `<addon>/tests/` (Python) and `<addon>/static/tests/` (JS). Core framework tests live in `odoo/tests/` (`case.py`, `common.py`, `form.py`, `loader.py`, `result.py`) plus dedicated `odoo/addons/test_*` modules (e.g. `test_new_api`, `test_inherit`, `test_access_rights`, `test_performance`, `test_lint`) that exercise ORM/framework internals.
- **Naming**: files `test_<feature>.py`; classes `Test<Feature>(SomeCommonMixin)`; methods `test_<scenario>`.
- **Framework**: `unittest`-based, layered with Odoo-specific base classes in `odoo/tests/common.py`: `BaseCase` → `TransactionCase` (wraps each test in a DB transaction/savepoint, rolled back after) → `HttpCase` (adds a live test HTTP server + browser/tour support for JS integration tests). Standard `assertEqual`/`assertRaises` plus Odoo helpers (`Form` for onchange simulation).
- **Tagging**: `@tagged('post_install', '-at_install')` decorators control when/how tests run in the module-install pipeline — a distinctive Odoo convention, not plain unittest.
- **Shared fixtures**: per-addon `tests/common.py` defines reusable `*Common` mixins with `setUpClass` fixture data (e.g. `SaleCommon`, `AccountTestInvoicingCommon`, `MailCommon`), composed via multiple inheritance in concrete test classes.
- **Mocking**: standard `unittest.mock.patch`; `freezegun.freeze_time` for date-dependent logic. Odoo favors real transactional DB fixtures over mocking the ORM itself — mocks target external services/dates, not persistence.
- **Frontend tests**: `static/tests/*.test.js` (unit tests via `web.assets_unit_tests`) and `static/tests/tours/**` (scripted "tour" E2E browser walkthroughs run through `HttpCase`).
- **Scope emphasis**: heavy emphasis on integration-style tests against a real (transactional) database and full ORM/registry rather than isolated unit tests with mocks — model behavior (computes, constraints, security rules, inheritance) is only meaningfully tested through the ORM stack.

## Key File References

- `odoo-bin`, `odoo/http.py`, `odoo/models.py`, `odoo/fields.py`, `odoo/api.py`
- `odoo/modules/{loading,graph,registry,module}.py`
- `odoo/service/{server,db,model,security,common}.py`
- `odoo/tests/common.py` (`BaseCase`/`TransactionCase`/`HttpCase`)
- `odoo/addons/base/` (core `ir.*` models bundled in the framework)
- `addons/sale/` (full-featured business addon example: models, wizard, report, controllers, security)
- `addons/web/` (frontend framework addon; OWL/JS/SCSS conventions)
