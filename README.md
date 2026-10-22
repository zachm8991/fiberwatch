# FiberWatch

A Python CLI that turns normalized ONT telemetry into explainable incident reports.
Built around three support questions: are failures shared across a PON, is one ONT
flapping, and is the latest online optical reading below a configured threshold?

**Scope:** local portfolio prototype using fictional identifiers and synthetic data.
It does not connect to ISP equipment, issue commands, confirm root cause, or use employer data.

## Run in under a minute

Python 3.11+; no runtime dependencies. Run from this repository's root:

```bash
python -m fiberwatch examples/events.csv --output report.json
python -m unittest discover -s tests -v
```

Windows users can use `py` instead of `python`. Optional packaging:
`python -m pip install -e .`, then `fiberwatch examples/events.csv`.

## Features

- Strict CSV ingestion with row-level errors, timezone normalization, and duplicate removal.
- Sliding windows correlate distinct failed ONTs on the same PON.
- Recovery samples cancel a prior failure inside the window.
- Flap detection counts changes between up and non-up states, not repeated alarms.
- Latest-sample optical checks avoid reporting historical weak readings as current.
- Stable JSON output contains timestamps, evidence, affected ONTs, and a next diagnostic step.
- CI matrix is configured for Python 3.11–3.13; local validation is described in VALIDATION.md.

## Input contract

CSV header: `timestamp,ont,pon,status,rx_dbm`.
`timestamp` is ISO 8601 with an offset; `Z` is accepted. `ont` and `pon` are
nonempty strings; `status` is `up`, `down`, or `los`; optical power is optional
and must be finite between -60 and +10 dBm. Identical samples are collapsed.
Contradictory simultaneous samples use deterministic status sorting, not inferred causal order;
upstream normalization should resolve them before operational use.

```bash
python -m fiberwatch examples/events.csv --window 120 --outage-min 3 --weak-rx -27
```

Defaults: 120-second window, 3 failed ONTs, -27 dBm weak threshold, 4 state
transitions for flapping. These are demo settings, not universal vendor limits.
The sample produces three findings: shared PON failure, weak signal, and flapping.
`max_failed_onts` is peak simultaneous observed failures in a window; the ONT
list is the union over merged overlapping findings.

## Design

`engine.py` owns ingestion, immutable event records, and analysis; `cli.py` owns
argument parsing and report output. Observations are sorted before analysis so
replay order does not affect results. A shared-failure finding is a hypothesis
from observed states, not a measured outage duration or a verified fiber cut.

## Limits and next steps

In-memory batch processing; stale samples age out rather than being treated as
live device state. No inventory denominator, telemetry polling, or actual device adapters.
Read-window filtering can be linear in active ONTs per event; this is not a
benchmarked streaming engine. Next improvements: vendor-neutral adapters,
explicit end-of-observation handling, incident lifecycle storage, and replay benchmarks.

See [WALKTHROUGH.md](WALKTHROUGH.md) for interview practice and extension exercises.
