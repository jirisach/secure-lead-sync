
# Secure Lead Synchronization Engine

![Python](https://img.shields.io/badge/python-3.11+-blue)
![CLI](https://img.shields.io/badge/interface-CLI-black)
![Tests](https://img.shields.io/badge/tests-pytest-green)
![Status](https://img.shields.io/badge/status-active-success)

**Plan before you sync.**

Deterministic CRM synchronization.

Secure Lead Synchronization Engine (SLS) is a Python CLI tool designed to safely synchronize lead data into CRM systems.

Instead of blindly pushing data into CRM systems, SLS enforces a controlled workflow:

```
CSV → PLAN → VALIDATE → SYNC
```

The goal is to make CRM integrations predictable, inspectable, and safe.

---

## 🚀 Quick demo

Run the full local demo:

```
python -m sls.cli demo --input samples/leads_input.csv
```

This command runs:

- doctor
- data quality analysis
- sync planning
- dedupe analysis
- Close CRM dry-run planning

---

## 🖥️ Example CLI output

Example output from:

```bash
python -m sls.cli demo --input samples/leads_input.csv
```

```json
{
  "demo": "Secure Lead Synchronization Engine",
  "input_path": "samples\\leads_input.csv",
  "steps": {
    "doctor": {
      "doctor_status": "ok"
    },
    "data_quality": {
      "summary": {
        "rows_total": 10,
        "missing_email": 2,
        "missing_phone": 1,
        "duplicate_email_count": 1,
        "duplicate_phone_count": 3
      }
    },
    "plan": {
      "summary": {
        "creates": 0,
        "updates": 7,
        "duplicates_in_input": 3,
        "skips": 0
      }
    },
    "dedupe": {
      "summary": {
        "rows_total": 10,
        "candidate_pairs": 4,
        "high_confidence": 4
      }
    },
    "close_plan": {
      "status": "ok",
      "summary": {
        "would_create": 7,
        "would_match_by_email": 1,
        "would_match_by_phone": 2
      }
    }
  }
}
```

## 📦 Installation

Clone the repository:

```
git clone https://github.com/YOUR_USERNAME/secure-lead-sync.git
cd secure-lead-sync
```

Install dependencies:

```
pip install -e .
```

Run the CLI:

```
python -m sls.cli --help
```

---

## ❓ Why this project exists

Many CRM integrations fail because:

- lead imports create duplicates
- bad data reaches the CRM
- integrations write data blindly
- debugging integrations is difficult
- automation lacks safety controls

Secure Lead Synchronization Engine solves this by introducing a deterministic synchronization workflow where every step can be inspected before execution.

---

## 🧠 Core principles

### Deterministic synchronization

Always inspect what will happen before data is written.

```
plan → review → sync
```

### Safe automation

Automation should not remove visibility or control.

SLS provides:

- dry-run planners
- structured logging
- retry logic
- diagnostic tools

### Data hygiene

Data quality problems should be detected before data reaches the CRM.

---

## 🏗️ Architecture overview

```text
                       +----------------------+
                       |   Input CSV / API    |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       |   Normalization      |
                       | email / phone / text |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       | Identity / Fingerprint|
                       +----------+-----------+
                                  |
                +-----------------+------------------+
                |                                    |
                v                                    v
    +--------------------------+         +--------------------------+
    |   Advisor Layer          |         |   Planning Engine        |
    |                          |         |                          |
    | - quality advisor        |         | - create/update          |
    | - mapping advisor        |         | - match by email/phone   |
    | - dedupe advisor         |         | - duplicate detection    |
    +------------+-------------+         +-------------+------------+
                 |                                         |
                 v                                         v
    +--------------------------+         +--------------------------+
    |   Human review / CLI     |         |   Sync Engine            |
    |                          |         |                          |
    | sls advise               |         | sls sync                 |
    | sls plan                 |         | mock target / CRM target |
    | sls close-plan           |         +-------------+------------+
    +------------+-------------+                       |
                 |                                     v
                 |                        +--------------------------+
                 |                        | Target Connectors        |
                 |                        | - mock CRM               |
                 |                        | - Close CRM              |
                 |                        +-------------+-----------+
                 |                                      |
                 +------------------+-------------------+
                                    |
                                    v
                       +------------------------------+
                       | Observability / Reliability  |
                       |                              |
                       | - JSON logs                  |
                       | - PII redaction              |
                       | - retry / backoff            |
                       | - state tracking             |
                       | - doctor command             |
                       +------------------------------+
```

---

## ⚙️ Features

### CLI interface

All operations are available via CLI.

```
sls plan
sls sync
sls advise
sls doctor
```

---

### Sync planning engine

The planner determines what actions should happen before synchronization:

- create
- update
- match by email
- match by phone
- skip duplicates

Example:

```
python -m sls.cli plan --input leads.csv
```

---

## 🔍 Data advisors

The advisor layer analyzes data before synchronization.

### Data quality advisor

Detects:

- missing email
- missing phone
- invalid email
- suspicious phone numbers

Example:

```
sls advise --input leads.csv
```

### Mapping advisor

Suggests field mapping between CSV columns and CRM fields.

```
sls map-advise --input leads.csv
```

### Duplicate advisor

Detects likely duplicate leads using heuristics.

```
sls dedupe-advise --input leads.csv
```

---

## 🔌 CRM connector framework

The project currently includes a Close CRM connector skeleton.

Capabilities include:

- configuration validation
- dry-run sync planning
- read-only search skeleton
- API error handling
- retry integration

Example:

```
sls close-ping
```

---

## 🔁 Retry framework

External API operations use retry logic with exponential backoff.

Handles:

- temporary API failures
- network errors
- rate limits

Example demo:

```
sls retry-demo
```

---

## 📊 Structured logging

Logs are stored as JSON lines in:

```
data/logs/sls.log.jsonl
```

Properties:

- structured events
- safe for log ingestion systems
- PII redaction

---

## 🩺 Doctor command

Environment diagnostics.

```
sls doctor
```

Checks:

- project structure
- environment configuration
- CSV schema
- log files
- state files

---

## 🔄 Example workflow

1️⃣ Inspect incoming data

```
sls advise --input leads.csv
```

2️⃣ Review sync plan

```
sls plan --input leads.csv
```

3️⃣ Execute synchronization

```
sls sync --input leads.csv
```

---

## 🧪 Testing

Run tests with:

```
pytest
```

Example output:

```
10 passed in 3.9s
```

---

## 🔐 Security considerations

Security was considered during design.

Measures include:

- environment-based API keys
- structured logging
- PII redaction
- dry-run planners before write operations

---

## 🗺️ Future roadmap

Potential improvements include:

- additional CRM connectors
- connector plugin architecture
- advanced deduplication heuristics
- streaming ingestion
- CI pipeline integration

---

## 👤 Author

Jiří Šach  
Automation & Systems Builder
