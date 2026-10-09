# V-TO-V Master Backend Roadmap
Updated: 2026-10-09

## 1. Purpose and working rules

This document is the master sequence for completing the V-TO-V backend,
research experiments, hardening, certification and subsequent frontends.

Preserve existing implementation and completed work. Audit before changing
code. Do not weaken authentication, authorization, database authority,
realtime consistency or research-only boundaries.

A proposed change is not an implementation. An implementation is not
verification. Verification is not acceptance. A PASS requires evidence
appropriate to the claim.

Limit each stage to four meaningful operations wherever practical.
Use real runtime evidence for runtime claims and preserve existing local
changes, scripts, backups and evidence.

## 2. Non-negotiable research model

Vehicle identity, convoy role, communication mechanism, experiment and run
are separate concepts.

- Vehicle identity: V001, V002, V003, and additional registered vehicles.
- Convoy role: LEADER or FOLLOWER, determined by convoy membership and
  administrator-authorized configuration.
- Mechanism: BASELINE or CANDIDATE, selected for a research run.
- Experiment: a defined research question and experimental configuration.
- Run: one execution of an experiment, with its own observations and evidence.

V001 is not inherently the baseline vehicle. V002 is not inherently the
candidate vehicle. The same selected vehicles must be used for both
mechanisms in comparable experiments.

The administrator configures the participating vehicles, leader, route,
waypoints and planned stoppages. The selected convoy configuration should
remain fixed across paired runs unless it is an explicitly studied variable.

The researcher selects the mechanism and fault configuration. Record
actual route progress, arrival/departure, stoppages, deviations, timestamps,
faults, recovery, observations, metrics and provenance when supported.

Compare evidence; do not automatically declare a winning mechanism.
Researchers interpret findings. Mechanism refinement must be versioned and
tested in a new traceable run without overwriting prior evidence.

## 3. Architecture invariants

- The authoritative database remains the source of truth for vehicle state.
- Vehicle identity is independent of display numbering and convoy role.
- Only authorized operations may assign or reassign a convoy leader.
- Telemetry must not silently assign convoy roles.
- Device timestamps are preserved for telemetry ordering and analysis.
- Server receipt/update time is used for communication freshness.
- A successfully accepted current packet establishes current communication.
- Background monitoring persists events and alerts transactionally.
- Research adapters and analysis must not mutate operational vehicle state.
- Baseline/candidate comparison remains research-only.
- Preserve API contracts, authentication, authorization and realtime authority.
- Render's current SQLite deployment is a research connectivity environment,
  not a claim of production-grade persistent storage.

## 4. Existing status snapshot

Reported previously completed:
- Stages 1-9: device authentication, location/routing, route progress,
  route deviation, map-ready APIs, convoy intelligence, monitoring,
  realtime and synchronization/recovery.
- Stages 10.1-10.6: research framework, mechanism inventory and definition,
  fault framework, integrated research mechanism, vehicle/experiment contract.
- Dynamic convoy implementation and Alembic migration a71c4e8d2f10.
- V001 public ingestion and authenticated state retrieval were demonstrated.
- V001 baseline, fault detection, recovery and alert behavior were observed.

Current Git checkpoint observed on 2026-10-09:
74509ea - Fix communication freshness to use server receipt time
origin/main was at the same commit during the audit.

Evidence qualification:
- A Stage 10.7.3 baseline evidence file exists.
- Stage 10.7.4 fault-engine runtime evidence exists.
- Stage 10.7.4 monitor forensic evidence exists.
- Stage 10.7.5 acceptance file exists, but its PASS labels were written by
  a command and are not independent verification.
- Previously observed Wokwi/Render runtime results should be reconciled into
  a traceable evidence package where source logs and outputs are available.
- Do not repeat Wokwi experiments unless evidence cannot otherwise be
  validated or a genuine unresolved behavior requires retesting.

Statuses in this document are a planning snapshot, not a substitute for
current source inspection or acceptance testing.

## 5. Stage 10 - Research and experimental mechanism

### 10.1-10.6 - Research architecture and contract
Reported COMPLETE/FROZEN. Preserve the existing research modules, approved
mechanism definitions, fault framework, observation/metrics/evidence pipeline,
vehicle contract and research-only boundary. Audit before any changes.

### 10.7 - V001 technical integration and baseline evidence
Technical integration and runtime behaviors have been demonstrated.
Reconcile evidence packaging and acceptance claims before treating the
entire stage as formally frozen. Do not redo successful experiments without
a specific evidence or behavior reason.

### 10.8 - Multi-vehicle experimental readiness
Status: NEXT; audit first.

Operation 1: inspect current Git state, roadmap, source and evidence.
Operation 2: audit registered vehicles, stable identities, display numbering,
dynamic convoy membership, leader/follower invariants and admin authorization.
Operation 3: audit administrator route, waypoint, stoppage and journey
configuration, plus experiment/run configuration and their relationships.
Operation 4: document gaps; implement only verified missing requirements
and run focused acceptance tests.

Required outcomes:
- Multiple registered vehicles without hardcoded V001/V002 role assumptions.
- One eligible leader per active convoy; other active members are followers.
- Route and planned stoppage configuration is associated with the journey/run.
- Mechanism selection is separate from vehicle identity and convoy role.
- Runs retain configuration, timestamps, observations and evidence references.
- Existing authorization and operational-state boundaries remain intact.

Do not start paired experiments until the configuration audit passes.

### 10.9 - Paired baseline and candidate experiments
Status: NOT STARTED.

Use the same selected vehicles, convoy roles, route, waypoints, stoppages,
and comparable test conditions for both mechanisms.

Operation 1: define and validate paired run configurations and metric rules.
Operation 2: execute the baseline and candidate runs, including approved
normal-operation and controlled-fault scenarios; capture observations.
Operation 3: validate run completeness, configuration provenance, timing,
fault severity, recovery and evidence integrity.
Operation 4: accept or reject the experiment dataset based on explicit checks.

Do not change the approved candidate mechanism silently during the runs.
Record deviations and environmental differences. One run per mechanism is
an initial comparison, not proof of general superiority.

### 10.10 - Comparison, research conclusion and refinement
Status: NOT STARTED.

Operation 1: calculate approved metrics and compare valid paired runs.
Operation 2: analyze improvements, regressions, fault/recovery behavior,
contradictions, missing data, limitations and uncertainty.
Operation 3: prepare a reproducible evidence and provenance package.
Operation 4: researcher decides whether a controlled mechanism refinement
is justified; if so, version it and create new traceable runs.

No automatic winner. Preserve prior runs and results.

## 6. Backend hardening and certification

### Stage 11 - Security hardening
Status: NOT STARTED.

1. Audit authentication, authorization, device identity, input validation,
   secrets, rate limiting, idempotency and audit logging.
2. Implement only verified gaps.
3. Test unauthorized access, invalid inputs, replay/duplicate handling and
   security boundaries without weakening existing controls.
4. Produce evidence-backed security acceptance.

### Stage 12 - Full automated regression testing
Status: NOT STARTED.

1. Inventory existing tests and identify coverage gaps.
2. Cover API, database/migrations, ingestion, state authority, monitoring,
   realtime, synchronization/recovery, convoy, routes, research, evidence,
   experiments, security and device compatibility.
3. Run the full suite; fix failures and repeat.
4. Preserve reproducible test results and complete regression acceptance.

### Stage 13 - Final Wokwi compatibility certification
Status: NOT STARTED.

This is final compatibility/regression certification, not the research run.
Verify V001 and V002 compatibility with finalized contracts, timestamps,
sequence behavior, authentication configuration, fault/recovery handling
and ingestion. Preserve actual device output and backend evidence.

### Stage 14 - Final comprehensive backend audit
Status: NOT STARTED.

Audit architecture, source, database and migrations, API contracts, identity,
authentication/authorization, ingestion, routing/progress/deviation, convoy,
monitoring, realtime, recovery, research isolation, evidence, security,
automated tests, Wokwi, deployment and documentation. Resolve blockers or
document accepted limitations explicitly.

### Stage 15 - Backend V1 freeze
Status: NOT STARTED.

1. Verify all required stage acceptances and known limitations.
2. Run release-candidate regression and deployment smoke tests.
3. Verify versioned documentation, migration head, API contracts and evidence.
4. Record final acceptance and freeze Backend V1.

No frontend is considered complete merely because the backend is frozen.

## 7. Frontend roadmap after Backend V1 freeze

### Phase A - Streamlit frontend
Backend integration, authentication, vehicle dashboard, live state, map and
route visualization, convoy view, alerts/events, history, research views,
realtime, error/recovery behavior and acceptance.

### Phase B - Advanced React dashboard
React architecture and shared backend integration, authentication and
authorization UI, live map, convoy and journey views, alerts/events, history,
research/experiment views, realtime synchronization, recovery/offline behavior,
responsive design, performance and complete frontend acceptance.

Both frontends use the same backend business logic and API contracts.

## 8. Stage acceptance and evidence rules

Each stage must record:
- Scope and exact requirements.
- Source changes, if any, and the commit/version.
- Commands/tests actually executed and their real outputs.
- Runtime evidence separately from source/structural checks.
- Failures, limitations and unresolved items.
- Database/migration state where relevant.
- Final PASS/FAIL/OPEN decision and evidence locations.

Do not create PASS labels before checking the corresponding evidence.
A generated report is a record, not proof of the behaviors it describes.
Do not delete unrelated work or rewrite history to make an audit look clean.

## 9. Immediate next action

Start Stage 10.8 with a read-only audit of the existing convoy, route,
stoppage, experiment/run and research configuration implementations.
Do not implement a vehicle-specific baseline/candidate split.
