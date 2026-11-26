# PermitMe — Civic Licensing & Regulatory Suite

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20Supabase-336791?logo=postgresql&logoColor=white)](https://supabase.com/)
[![Cryptography](https://img.shields.io/badge/Security-HMAC--SHA256%20%7C%20SHA--256%20Hash%20Chain-0D9488)](#cryptographic--audit-architecture)
[![License: MIT](https://img.shields.io/badge/License-MIT-5EEAD4.svg)](LICENSE.md)

**PermitMe** is a desktop civic licensing, field inspection, and regulatory compliance workstation engineered with **PyQt6** and **PostgreSQL / Supabase** (isolated under the `permitme` schema). It manages the complete lifecycle of municipal and regulatory permits—from intake and SLA-tracked case routing to field inspection logging, cryptographic credential issuance, renewal lineage tracking, and tamper-evident hash-chained audit trails.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Capabilities](#core-capabilities)
3. [Database Schema & Stored Procedures](#database-schema--stored-procedures)
4. [Cryptographic & Audit Architecture](#cryptographic--audit-architecture)
5. [Repository Structure](#repository-structure)
6. [Prerequisites](#prerequisites)
7. [Installation & Configuration](#installation--configuration)
8. [Database Bootstrap & Verification](#database-bootstrap--verification)
9. [Running the Workstation](#running-the-workstation)
10. [Keyboard Shortcuts & UI Workflows](#keyboard-shortcuts--ui-workflows)
11. [Troubleshooting](#troubleshooting)
12. [License](#license)

---

## System Architecture

PermitMe uses a three-tier desktop architecture that separates presentation, domain/cryptographic services, and transactional database logic:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                     PyQt6 Desktop Workstation (src/ui/)                      │
│  ┌─────────────────────┐ ┌────────────────────────┐ ┌─────────────────────┐  │
│  │ Executive Overview  │ │ Inspections & Licensing│ │ Credential Verifier │  │
│  └──────────┬──────────┘ └───────────┬────────────┘ └──────────┬──────────┘  │
└─────────────┼────────────────────────┼─────────────────────────┼─────────────┘
              │                        │                         │
              ▼                        ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                Application & Cryptographic Service Layer                     │
│             src/services/credential_service.py (CredentialService)           │
│   • SLA Queue Aggregation  • Inspection & Renewal Calls  • HMAC-SHA256 Sign  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ psycopg / Connection Context Manager
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              Database Access Layer (database/db_manager.py)                  │
│                        PermitMeDatabaseManager                               │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ TLS / SSL (PostgreSQL Pooler)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│             PostgreSQL / Supabase (Schema: permitme + pgcrypto)              │
│  Tables: applicants, permit_types, offices, permit_applications,             │
│          inspection_logs, credentials, audit_logs                            │
│  Procedures: sp_submit_application, sp_record_inspection, sp_issue_credential│
│  Trigger: fn_chained_audit_log() -> SHA-256 prev_hash/row_hash ledger        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Capabilities

### 1. Executive Overview & SLA Risk Monitoring
- **Real-Time KPI Telemetry:** Aggregates active queue volume, overdue SLA cases, watchlist cases (`BREACHED` or `< 24 hours` remaining), and credentials expiring within 30 days.
- **Department & Office Queue Breakdown:** Summarizes open case counts and SLA breaches grouped by processing office (`office_code`) and workflow state.
- **Click-Through Triage:** Clicking any row in the **Priority SLA Risk Monitor** populates the case in **Inspections & Licensing** and switches workspaces immediately.

### 2. New Permit Application Intake (`Ctrl+N` / `⌘N`)
- **Validated Lookup Modal:** Loads active applicants, permit types (with base fee display), and regional processing offices asynchronously with non-blocking spinner feedback.
- **Transactional Submission:** Inserts a draft record into `permitme.permit_applications` and invokes `CALL permitme.sp_submit_application(new_id, NULL)` inside a single database transaction to generate official reference numbers and assign SLA deadlines.

### 3. Field & Technical Inspections + Credential Lifecycle
- **Inspection Recording:** Logs inspection types (`site_safety`, `pre_license_audit`, `hygiene_and_cold_chain`, `fire_code_compliance`, `re_inspection`) and outcomes (`passed`, `conditional`, `failed`) via `permitme.sp_record_inspection`.
- **Live Transition Preview:** Displays the exact database state transition before submission:
  - `passed` → `fee_pending` (eligible for credential issuance)
  - `conditional` → `rfi_pending` (Request for Information)
  - `failed` → `rejected` (compliance failure recorded)
- **Digital Credential Issuance & Renewal:** Issues active credentials (`sp_issue_credential`) with automated fee settlement and expiration calculation, or initiates renewal applications linked back to `renewed_from_credential_id`.

### 4. Cryptographic Credential Verifier
- **Canonical HMAC-SHA256 Signing & Verification:** Computes and verifies tamper-evident HMAC-SHA256 signatures over `permit_number|verification_code|expires_at` using constant-time digest comparison (`hmac.compare_digest`).
- **Full Certificate Inspection:** Displays holder identity, permit classification, active/revoked status, revocation reason, fee settlement, and renewal lineage, with one-click clipboard export of the canonical HMAC hex digest.

---

## Database Schema & Stored Procedures

All database objects are encapsulated within the `permitme` PostgreSQL schema:

| Object | Type | Purpose |
|---|---|---|
| `permitme.applicants` | Table | Stores registered individuals, sole proprietors, and business entities (`applicant_type` constrained to `individual`, `sole_proprietor`, `business`). |
| `permitme.permit_types` | Table | Catalog of regulatory permits/licenses, base fees, validity durations, and active flags. |
| `permitme.offices` | Table | Municipal/regional processing hubs (`code`, `name`, `is_active`). |
| `permitme.permit_applications` | Table | Core workflow entity tracking `reference_no`, `status`, `priority_score`, `sla_due_at`, and inspection notes. |
| `permitme.inspection_logs` | Table | Historical log of field inspections, inspector IDs, outcomes, and findings. |
| `permitme.credentials` | Table | Issued digital permits/licenses (`permit_number`, `verification_code`, `expires_at`, `is_active`, `revoked_at`, `renewed_from_credential_id`). |
| `permitme.audit_logs` | Table | Immutable append-only audit ledger (`table_name`, `record_id`, `action`, `old_data`, `new_data`, `actor_id`, `logged_at`, `prev_hash`, `row_hash`). |
| `permitme.sp_submit_application` | Procedure | Transitions a draft application into active review and initializes its SLA deadline. |
| `permitme.sp_record_inspection` | Procedure | Inserts an inspection record and advances `permit_applications.status` based on outcome. |
| `permitme.sp_issue_credential` | Procedure | Generates or updates an active credential in `permitme.credentials` and marks the application approved. |
| `permitme.fn_chained_audit_log` | Trigger Function | Computes chained SHA-256 hashes on data mutations using `extensions.digest(convert_to(..., 'UTF8'), 'sha256')`. |

---

## Cryptographic & Audit Architecture

### 1. Digital Credential HMAC-SHA256 Signature
Credentials are signed in `CredentialService.sign_credential()` using a server/workstation secret (`PERMITME_SIGNING_SECRET`):

```text
canonical_payload = "<permit_number>|<verification_code>|<expires_at_iso8601>"
signature_hex     = HMAC-SHA256(key=PERMITME_SIGNING_SECRET, msg=canonical_payload)
```

Verification uses `hmac.compare_digest()` to prevent timing side-channel attacks.

### 2. Chained SHA-256 Audit Ledger (`fn_chained_audit_log`)
Every `INSERT`, `UPDATE`, or `DELETE` on audited `permitme` tables triggers `permitme.fn_chained_audit_log()`:
1. Fetches the most recent `row_hash` from `permitme.audit_logs` (defaulting to `'GENESIS'` for the initial entry).
2. Serializes `prev_hash`, `TG_TABLE_NAME`, `TG_OP`, `record_id`, `old_data` (`jsonb`), `new_data` (`jsonb`), and `clock_timestamp()`.
3. Computes `row_hash = encode(extensions.digest(convert_to(v_payload, 'UTF8'), 'sha256'), 'hex')`.
4. Persists the linked record into `permitme.audit_logs`, creating a verifiable hash chain across all regulatory state transitions.

---

## Repository Structure

```text
permitme/
├── main.py                              # Entry point: loads .env, initializes DB manager & Qt event loop
├── database/
│   └── db_manager.py                    # PermitMeDatabaseManager (fetch_all, connection(), stored procedure wrappers)
├── src/
│   ├── img/
│   │   ├── permit.jpg                   # Workstation ambient backdrop
│   │   └── nice_profile.jpg             # Officer profile avatar
│   ├── services/
│   │   └── credential_service.py        # SLA queue queries, inspection/renewal orchestration, HMAC-SHA256 signing
│   └── ui/
│       ├── svg_icons.py                 # Programmatic SVG icon & pixmap rendering
│       ├── theme.py                     # Frosted-glass dark QSS stylesheet & custom control styling
│       └── workstation_app.py           # PermitMeEnterpriseWorkstation, NewApplicationDialog, custom delegates
├── README.md                            # Technical documentation
└── LICENSE.md                           # MIT License terms
```

---

## Prerequisites

- **Python:** `3.10` or higher
- **Database:** PostgreSQL `14+` or a **Supabase** project with:
  - The `permitme` schema and stored procedures deployed
  - The `pgcrypto` extension enabled (`CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;`)
- **Operating System:** macOS, Linux, or Windows (includes custom `Fusion` style overrides and `DarkComboItemDelegate` for consistent dark-mode rendering on macOS)

---

## Installation & Configuration

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/permitme.git
   cd permitme
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # .venv\Scripts\activate         # Windows (PowerShell / CMD)
   ```

3. **Install Python dependencies**
   ```bash
   pip install PyQt6 "psycopg[binary]" python-dotenv
   ```

4. **Configure environment variables**
   Create a `.env` file in the repository root (do not commit `.env` to version control):
   ```env
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
   PERMITME_SIGNING_SECRET=replace-with-a-64-char-cryptographically-random-hex-secret
   ```

---

## Database Bootstrap & Verification

Run the following SQL in your PostgreSQL / Supabase SQL Editor to verify that `pgcrypto` and the chained audit trigger are configured properly:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

-- Verify the latest chained audit entries
SELECT
    id,
    table_name,
    record_id,
    action,
    prev_hash,
    row_hash,
    logged_at
FROM permitme.audit_logs
ORDER BY id DESC
LIMIT 10;
```

---

## Running the Workstation

Start the desktop client from the project root:

```bash
python main.py
```

On startup, the workstation connects to PostgreSQL/Supabase, renders the **Executive Overview**, and synchronizes office queue metrics, SLA risk alerts, active applications, and issued credentials.

---

## Keyboard Shortcuts & UI Workflows

| Shortcut | Scope | Action |
|---|---|---|
| `Ctrl+N` / `⌘N` | Global | Launch **New Permit Application Intake** modal |
| `Ctrl+R` / `⌘R` | Global | Trigger **Sync Live Data** across all tables and KPI cards |
| `Ctrl+1` / `⌘1` | Navigation | Switch to **Executive Overview** |
| `Ctrl+2` / `⌘2` | Navigation | Switch to **Inspections & Licensing** |
| `Ctrl+3` / `⌘3` | Navigation | Switch to **Credential Verifier** |

### Standard End-to-End Case Flow
1. **Intake:** Press `Ctrl+N` / `⌘N`, select an applicant, permit type, and office, and click **Create & Submit Application**.
2. **Inspection:** Open **Inspections & Licensing**, select the new row in **Applications Registry**, choose an inspection type and outcome (`Passed`), and click **Record Inspection & Advance Case**.
3. **Issuance:** Click **Approve & Issue Digital Credential** to settle fees and generate an active permit number and verification code.
4. **Verification:** Select the issued row in **Issued Permits & Licenses**, click **Open Selected Permit in Verifier**, and copy or validate its canonical **HMAC-SHA256** signature.

---

## Troubleshooting

- **`function digest(text, unknown) does not exist` or `invalid input syntax for type bytea`:**
  Ensure `pgcrypto` is installed in `extensions` and `permitme.fn_chained_audit_log()` calls `extensions.digest(convert_to(v_payload, 'UTF8'), 'sha256')` with `SET search_path = permitme, extensions, public`.
- **`null value in column "applicant_type" of relation "applicants"`:**
  When seeding `permitme.applicants` directly via SQL, always supply `applicant_type` as one of `'individual'`, `'sole_proprietor'`, or `'business'`.
- **Empty Applications Registry:**
  Click **Sync Live Data** (`Ctrl+R`) or verify that `permitme.permit_applications` contains records and your `DATABASE_URL` points to the target Supabase instance.

---

## License

This project is licensed under the **MIT License**. See [LICENSE.md](LICENSE.md) for the full license text.