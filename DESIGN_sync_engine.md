# Design Decisions --- Lead Sync Engine

Copyright 2026 Jiří Šach

This document records the key architectural decisions behind **Lead Sync
Engine**. The goal is to explain not only *what* the system does, but
*why the architecture exists in this form*. Future readers --- including
future‑me --- should be able to understand the reasoning without digging
through source code.

------------------------------------------------------------------------

## 1. Why deterministic synchronization instead of blind copy?

**Decision:** I evaluate normalization, identity signals and duplicate
detection before allowing synchronization.

**Reasoning:**

Blind copy between systems sounds simple but quickly turns into a chaos
machine. If malformed data enters one system, it can silently propagate
across every connected system.

A deterministic synchronization pipeline ensures that every record
follows the same evaluation path:

    normalize → validate → evaluate identity → detect duplicates → decide → synchronize

This approach prevents error amplification and makes the system
predictable. Predictable systems are dramatically easier to debug,
maintain and trust.

------------------------------------------------------------------------

## 2. Why idempotent operations?

**Decision:** I designed synchronization operations to be idempotent.

**Reasoning:**

In real integrations retries are unavoidable. They happen because of:

-   webhook retries
-   API retry mechanisms
-   temporary network failures
-   infrastructure hiccups

Without idempotency a retry can accidentally create duplicate records or
inconsistent state.

Idempotent operations guarantee that repeating the same request produces
the same result. This allows safe retries and graceful recovery during
failures.

In other words: retrying a request should never make the situation
worse.

------------------------------------------------------------------------

## 3. Why explicit conflict resolution instead of last‑write‑wins?

**Decision:** I explicitly detect and handle conflicts instead of
silently overwriting data.

**Reasoning:**

A last‑write‑wins strategy is simple but dangerous.\
Two systems can update the same record at the same time, and one update
silently destroys the other.

Explicit conflict handling provides:

-   traceable audit history
-   deterministic conflict resolution rules
-   the possibility for manual review

Silent data loss is worse than visible friction. Visibility keeps the
system honest.

------------------------------------------------------------------------

## 4. Why a quarantine system for problematic records?

**Decision:** I isolate problematic records in a quarantine layer.

**Reasoning:**

The worst failure mode in any data pipeline is silent data loss. If
records disappear without explanation, trust in the entire system
collapses.

A quarantine mechanism ensures that:

-   invalid records are isolated
-   valid records continue flowing
-   engineers can investigate issues later

The pipeline keeps moving, while suspicious records wait politely on the
side.

------------------------------------------------------------------------

## 5. Why privacy‑safe logging?

**Decision:** I avoid storing raw personally identifiable information in
logs.

**Reasoning:**

Logs tend to travel far --- monitoring systems, debugging tools, alert
pipelines. If raw PII appears in logs, the security blast radius grows
dramatically.

Privacy‑safe logging minimizes:

-   GDPR exposure
-   breach impact
-   operational risk

Instead of raw values, the system logs derived identifiers or hashed
signals.

------------------------------------------------------------------------

## 6. Why separate normalization from synchronization?

**Decision:** I implemented normalization as an independent layer.

**Reasoning:**

Identity signals are often messy:

-   phone numbers written in many formats
-   inconsistent email casing
-   inconsistent name formatting

Duplicate detection becomes unreliable if identity signals are not
normalized first.

Separating normalization ensures that the pipeline evaluates clean and
consistent data. This also improves modularity and testability.

------------------------------------------------------------------------

## 7. Additional design decision

**Decision:** I implemented layered duplicate detection before
synchronization.

**Reasoning:**

Duplicate detection should not rely on a single signal or lookup.

Evaluating multiple identity signals significantly reduces the chance
that duplicate records propagate across connected systems.

Stopping duplicates early is dramatically cheaper than cleaning them
later.

------------------------------------------------------------------------

*Maintained and updated by the author whenever the architecture
evolves.*
