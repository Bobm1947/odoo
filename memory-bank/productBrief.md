# Product Brief

> This document captures the **product and project context** for development teams.
> It ensures all agents understand the product's purpose, users, constraints, **and the project's foundation**.

## Project Foundation

- **Project Name**: Odoo (community open-source ERP suite) — this repo is a fork at `github.com/DaKaZ/odoo` with local Docker dev tooling added on top of stock Odoo (currently one commit ahead: "local docker setup"). Remote `origin` = `https://github.com/DaKaZ/odoo.git`.
- **Objectives**: Provide a full business-application platform (CRM, Accounting, Inventory, Manufacturing, HR, POS, Website/eCommerce, Project, etc.) that can be run standalone per-app or combined into a full ERP. This fork's own objective so far is local containerized development setup — no Banyan-specific business logic exists yet; it is stock Odoo 18.0 core + community addons, likely intended as the base for future Banyan customization.
- **Scope**: In scope — the Odoo Python/JS web framework (`odoo/`), 621 first-party addon modules (`addons/`), CLI entrypoint (`odoo-bin`), packaging (`setup/`, `debian/`), and Docker-based local dev tooling (`Dockerfile`, `docker/`, `docker-compose.yml`). Out of scope / not present — any Banyan-specific product code, custom modules, or business logic.
- **Repository Structure**:
  - **Type**: Poly-repo (single package manifest at root; no workspace tool, no `apps/`/`packages/`/`libs/` convention)
  - **Workspace Tool**: None
  - `odoo/` — core framework (ORM, HTTP/web layer, CLI, service layer, tooling); includes `odoo/addons/base`, a special core addon bundled inside the framework package defining `res.users`/`res.groups`/security, and `odoo/release.py` (version info: **18.0**, final).
  - `addons/` (repo root, sibling to `odoo/`) — 621 first-party business modules, each self-contained with its own `__manifest__.py`. Covers CRM, Sales, Accounting/Invoicing, Inventory, Manufacturing, HR, POS, Website, Project, Marketing, Events, Fleet, Maintenance, Repair, Surveys, plus ~228 `l10n_*` country-localization packages and 17 `payment_*` provider integrations.
  - `doc/` — technical/developer documentation.
  - `docker/`, `Dockerfile`, `docker-compose.yml` — local dev tooling added by this fork.
  - `setup/`, `debian/`, `setup.py`, `odoo-bin` — packaging/installation tooling.
  - `LICENSE` (LGPLv3), `COPYRIGHT`, `SECURITY.md`, `CONTRIBUTING.md`.
- **Key Stakeholders**: Upstream owner is Odoo S.A. (copyright holder, "Odoo" trademark/SaaS business). This fork's stakeholder is the repo owner (Banyan-affiliated), currently only adding dev tooling — no named Banyan business owners yet.

## Git Configuration
- **Repository**: Yes
- **Provider**: GitHub
- **CLI Available**: gh (authenticated)
- **Remote URL**: https://github.com/DaKaZ/odoo.git
- **Default Branch**: main
- **Metadata Branch**: main
- **Routing Mode**: classic
- **Sync Automation**: none
- **Archive Strategy**: push-and-pr

## Product Overview

- **Name**: Odoo
- **Value Proposition**: A single, modular, open-source suite of web-based business applications that can be adopted one app at a time (e.g., just Invoicing, or just CRM) and combined seamlessly into a full-featured, integrated ERP — avoiding the cost and integration pain of stitching together many point solutions.
- **Product Type**: ERP / business application platform — self-hosted web application suite with a Python/PostgreSQL backend and a JS-based web client, distributed as an installable, modular addon framework.
- **Stage**: Mature, actively-maintained open source project, currently at version **18.0** (final release). This specific fork is at an early/near-zero-customization stage (one commit ahead: local Docker dev setup only).

## Key Functionality

Representative major app/module categories (out of 621 total addons; not exhaustive):

- **CRM** (`crm`) — lead tracking and opportunity/pipeline management
- **Sales** (`sale`) — quotations, sales orders, shared machinery for eCommerce
- **Invoicing/Accounting** (`account`) — invoices, payments, follow-ups, bank sync; full double-entry accounting via extensions and 228 country localization packages (`l10n_*`) for local tax/legal compliance
- **Inventory** (`stock`) — warehouse and logistics management
- **Purchase** (`purchase`) — purchase orders, tenders, vendor agreements
- **Manufacturing** (`mrp`) — manufacturing orders and bills of materials (BOMs)
- **Point of Sale** (`point_of_sale`) — retail/restaurant POS interface
- **Human Resources** (`hr` + many `hr_*` extensions) — employee records, recruitment, timesheets, fleet, maintenance
- **Website & eCommerce** (`website`, `website_sale` family) — website builder, online store
- **Project Management** (`project`) — project/task planning, timesheet integration
- **Marketing** (`mass_mailing`, event/social modules) — email marketing, event marketing, social media
- **Events** (`event` + ~30 `event_*`/`website_event_*` modules) — registration, booths, exhibitors, ticket sales
- **Other verticals**: Fleet (`fleet`), Maintenance (`maintenance`), Repair (`repair`), Surveys (`survey`), Lunch (`lunch`), Sign, Documents/Knowledge-style productivity tools
- **Payments & Delivery**: 17 payment provider connectors (Stripe, PayPal, Adyen, Mollie, Razorpay, Authorize.net, etc.) and delivery/shipping connectors
- **Core platform services** (`odoo/addons/base`): users, groups/permissions (RBAC), companies, multi-currency, translations, module/app installation and dependency management

## Markets Serviced

- **Primary Market**: Small-to-midsize businesses (SMBs) across virtually every industry — Odoo is general-purpose business software rather than a single vertical
- **Secondary Markets**: Retail/restaurants (POS), manufacturing, professional services (Project + Timesheets), events, real estate/fleet, e-commerce/website, accounting/bookkeeping practices
- **Geographic Focus**: Global — ~228 `l10n_*` localization packages cover country-specific tax, invoicing (UBL/CII/Peppol formats), and legal/fiscal requirements across dozens of countries
- **Market Size**: [To be determined] — not documented in codebase

## Competitive Landscape

- **Direct Competitors**: [To be determined] — not documented in-repo (publicly known competitors like SAP Business One, Microsoft Dynamics 365, NetSuite, Zoho One are not referenced)
- **Indirect Competitors**: [To be determined]
- **Key Differentiators**: Modularity (adopt apps standalone or combine into full ERP); open-source licensing (LGPLv3) vs. typically proprietary/licensed ERP suites
- **Competitive Advantages**: Broad first-party module coverage (621 addons) and deep localization (228 country packages) reduce need for third-party integration work

## Key Personas

### Primary Users

| Persona | Role | Goals | Pain Points | Success Metrics |
|---------|------|-------|-------------|-----------------|
| Sales Rep | Uses CRM/Sales apps | Track leads, close opportunities, issue quotations | [To be determined] | [To be determined] |
| Accountant/Bookkeeper | Uses Invoicing/Accounting app | Manage invoices, payments, bank reconciliation, follow-ups | [To be determined] | [To be determined] |
| Warehouse/Logistics Staff | Uses Inventory (`stock`) app | Manage stock movements and logistics | [To be determined] | [To be determined] |
| Cashier/Store Staff | Uses Point of Sale app | Process shop/restaurant transactions | [To be determined] | [To be determined] |
| HR Staff | Uses Employees (`hr`) app | Centralize employee info, recruitment, timesheets | [To be determined] | [To be determined] |
| Manufacturing Planner | Uses Manufacturing (`mrp`) app | Manage manufacturing orders and BOMs | [To be determined] | [To be determined] |
| Project Manager | Uses Project app | Organize and plan projects/tasks | [To be determined] | [To be determined] |
| Marketer | Uses Email Marketing/Events apps | Design/send/track campaigns, manage events | [To be determined] | [To be determined] |

### Secondary Users

| Persona | Role | Goals |
|---------|------|-------|
| Portal User (`group_portal`) | External customer/vendor with limited access | View/interact with own quotes, invoices, tickets via portal |
| Public User (`group_public`) | Anonymous website visitor | Browse website/eCommerce without authentication |

### Administrators/Operators

| Persona | Role | Responsibilities |
|---------|------|------------------|
| Internal User / Admin (base groups: "Internal User", "Settings", "Access Rights") | System administrator | Configure company settings, install/manage apps and modules, manage multi-company/multi-currency setup |
| Technical Administrator (`group_sanitize_override`, "Technical Features") | Power/technical admin | Bypass HTML sanitization, access technical/developer features, manage export permissions (`group_allow_export`) |

*(Persona goals/pain points/success metrics beyond role names are not documented in the codebase — inferred from app purpose only.)*

## User Flows

- **Primary Flow**: Install/activate one or more "Apps" (addon modules) via Settings > Apps; each app exposes menus/views for its domain (e.g., Sales quotation → order → invoice; Inventory receipt → pick → deliver)
- **Onboarding**: Standard installation follows Odoo's official Setup instructions (linked in README); new users typically start via Odoo eLearning or developer tutorials (external)
- **Key Workflows** (inferred from module relationships):
  - Quote-to-cash: CRM lead → Sales quotation/order → Invoicing → Payment (optional Inventory delivery + Manufacturing steps)
  - Procure-to-pay: Purchase order → Vendor bill (Accounting) → Payment
  - Employee lifecycle: Recruitment → Employee record (HR) → Timesheets → Payroll/Expenses (where installed)
  - Retail: POS transaction → Inventory stock update → Accounting entry

## Success Metrics & KPIs

### Business Metrics
- [To be determined] — not present in codebase

### Product Metrics
- [To be determined] — not present in codebase

### Technical Metrics
- [To be determined] — not present in codebase

## Non-Functional Requirements

### Performance
- No explicit targets found in-repo. [To be determined]

### Scalability
- No explicit targets found in-repo. [To be determined]

### Security

- **Authentication**: Multiple auth modules as installable addons: `auth_ldap` (LDAP), `auth_oauth` (OAuth2), `auth_passkey` (WebAuthn/passkeys), `auth_signup` (self-signup), `auth_totp`/`auth_totp_mail`/`auth_totp_mail_enforce`/`auth_totp_portal` (TOTP MFA variants), `auth_password_policy`/`_portal`/`_signup` (password policy enforcement)
- **Authorization**: Role-based via `res.groups`/`res.users` (defined in `odoo/addons/base`) — group/ACL-based RBAC, with per-model access (`ir.model.access`) and row-level record rules (`ir.rules`) layered per addon
- **Compliance**: Not formally documented for this codebase; localization modules (UBL/CII/Peppol e-invoicing) target country-specific legal/fiscal compliance, implying regulatory awareness — no SOC2/HIPAA/PCI-DSS certification referenced
- **Data Classification**: Not documented. [To be determined]
- **Encryption**: Not documented in-repo (typically deployment/infra-level)
- **Responsible Disclosure**: `SECURITY.md` points to Odoo's responsible disclosure process (odoo.com/security-report)

### Availability & Reliability
- Not documented in-repo. [To be determined]

### Data & Privacy
- Not documented in-repo beyond generic module functionality. [To be determined]

### Accessibility
- Not discoverable from the codebase; no explicit WCAG documentation found. [To be determined]

### Internationalization (i18n)
- Heavily localized: `.weblate.json` at repo root confirms Weblate translation-management integration
- **Localization Needs**: 228 `l10n_*` country-specific modules provide tax rules, chart of accounts, and legal/fiscal document formats (e.g., UBL/CII e-invoicing) per country
- RTL support is implied (Docker image installs `rtlcss`) but specific language/RTL matrix not enumerated here

### Browser/Platform Support
- Not explicitly documented in this codebase (modern browser assumed; no version matrix found)

## Integration Points

### External Systems

| System | Purpose | Protocol | Direction |
|--------|---------|----------|-----------|
| Payment providers (Stripe, PayPal, Adyen, Mollie, Razorpay, Authorize.net, Buckaroo, Worldline, Flutterwave, Mercado Pago, Nuvei, Xendit, AsiaPay, APS, etc.) | Online payment processing | REST (provider-specific) | Outbound |
| Delivery/shipping carriers (e.g., Mondial Relay) | Shipping rate/label integration | REST/SOAP | Outbound |
| LDAP directory servers (`auth_ldap`) | Enterprise authentication | LDAP | Outbound |
| OAuth identity providers (`auth_oauth`) | Third-party login/SSO | OAuth2 | Outbound |
| Bank synchronization services (`account` module) | Automatic bank statement import | Provider-specific | Inbound |
| E-invoicing standards (UBL, CII, Peppol via `l10n_*`, `account_edi_ubl_cii*`) | Legal/fiscal electronic invoicing per jurisdiction | XML/EDI standards | Outbound/Both |

### APIs Consumed
- Third-party payment gateway APIs, LDAP/OAuth identity provider APIs, carrier shipping APIs (abstracted per-addon)

### APIs Provided
- Odoo's own XML-RPC/JSON-RPC web services for external system integration (standard framework capability); no custom Banyan-facing API exists in this repo yet

### Data Sources

| Source | Type | Frequency |
|--------|------|-----------|
| PostgreSQL | Database | Real-time (primary datastore) |

## Constraints & Assumptions

### Business Constraints
- Licensing: Odoo core is LGPLv3 (`LICENSE`/`COPYRIGHT`); bundled third-party components may carry other GPL-compatible licenses per-file. Any Banyan customization built on this fork must respect LGPLv3 obligations. This repo appears to be Community edition only (Odoo's proprietary "Enterprise" edition is not present).
- No budget/timeline/organizational constraints documented in-repo.

### Technical Constraints
- Requires PostgreSQL + Python runtime per standard Odoo installation; this fork adds Docker-based dev tooling as the assumed local dev path.
- 621 interdependent addons imply customization should be additive (new modules depending on existing ones) rather than modifying core addons directly, per Odoo convention.

### Assumptions
- This fork is intended as an unmodified Odoo Community 18.0 base onto which Banyan-specific modules/customizations will be layered later — no such customization exists yet.
- The single commit "local docker setup" suggests the immediate goal was enabling local development, not feature work.
- Business/product framing (personas, KPIs, competitive positioning) for a future Banyan-branded product is not yet established and must be defined separately from this technical codebase.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Diverging from upstream Odoo makes future upstream security/version updates harder to merge | Medium | High | Keep Banyan-specific changes in separate addons rather than modifying core; track upstream release notes |
| LGPLv3 licensing obligations misunderstood when adding proprietary Banyan code | Low-Medium | Medium | Legal/licensing review before adding closed-source modules |
| No documented compliance (SOC2/PCI/GDPR specifics) if handling regulated data (payments, HR/PII) | Unknown | Potentially High | Formal compliance review once real data/customers are involved |
| Large addon surface (621 modules) increases attack surface / maintenance burden if broadly enabled | Medium | Medium | Enable only required apps; follow `SECURITY.md` disclosure process |

*(Risk entries are reasoned inferences, not sourced from an in-repo risk register.)*

## Open Questions

- [ ] What is the intended Banyan-specific product/business use case this Odoo fork will support?
- [ ] Will this remain Community edition only, or is Enterprise edition integration planned?
- [ ] Which subset of the 621 addons will actually be enabled/customized for the target business use case?
- [ ] Are there specific compliance requirements (industry, geography) that should shape which `l10n_*` and security modules get activated?

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-09-18 | /bmb:init (brownfield discovery) | Initial creation from codebase analysis |

## Last Refreshed

2026-09-18
