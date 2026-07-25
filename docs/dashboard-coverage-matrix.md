# Dashboard Coverage Matrix

**Phase 9 — Operational Domain Design**

## Purpose

This document verifies that every approved Power BI report page is fully supported by the operational data model, Gold-layer outputs, and representative business scenarios.

This matrix answers a different question than the Risk Validation Matrix.

- **Risk Validation Matrix:** Does the risk engine compute the correct result?
- **Dashboard Coverage Matrix:** Does the data model contain everything required to answer each business question on every dashboard page?

---

# Locked Dashboard Pages

1. Executive Overview
2. Project Risk
3. Crew Scheduling
4. Safety
5. Equipment
6. Regional Operations
7. Pipeline Monitoring

---

# Coverage Matrix

| Dashboard Page | Business Questions | Required Data | Status |
|---------------|--------------------|---------------|--------|
| Executive Overview | Overall operational risk, tomorrow's business impact, leadership priorities | To be completed | Planned |
| Project Risk | Which projects are at risk? Continue or delay? | To be completed | Planned |
| Crew Scheduling | Which crews require rescheduling? Labor hours at risk? | To be completed | Planned |
| Safety | Which locations exceed thresholds? Who should be notified? | To be completed | Planned |
| Equipment | Which equipment is exposed? Which should be relocated? | To be completed | Planned |
| Regional Operations | Which offices and regions require attention? | To be completed | Planned |
| Pipeline Monitoring | Did ingestion succeed? Which runs failed? | To be completed | Planned |

---

# Open Items

The completed version of this document will confirm:

- Every dashboard page can be answered using the approved operational model.
- Every required metric has a supporting Gold-layer field.
- Every report page has representative validation scenarios.
- No dashboard depends on data that does not exist in the approved architecture.

---

# Status

This document will be completed before Phase 10 implementation begins.