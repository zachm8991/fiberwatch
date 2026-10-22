# Walkthrough and interview practice

## Trace the data

CSV → validated Event objects → sort/deduplicate → group by ONT/PON → correlate → JSON report.

Run the sample command from the README, inspect its output, then read the core module alongside the tests. Change one input and predict the new output before rerunning.

## Explain these decisions

### Why count unique ONTs?

Repeated alarms from one device should not look like a shared outage.

### Why cancel on recovery?

A prior LOS sample should stop contributing once a newer UP observation appears.

### What does flapping mean here?

Transitions between up and non-up, within a sliding window; not changes from LOS to down.

### What would you improve?

Represent incident lifecycle and confidence; add an inventory denominator and data quality metrics.

## Make it yours

Add a configurable maintenance suppression list, then test that it suppresses only matching ONTs during the specified time range.

## Describe the work accurately

This initial implementation was AI-assisted. Before presenting it, run it locally, understand the code, implement an extension, and record your actual changes. Describe it as a portfolio prototype and only claim design or implementation work you can explain. Do not invent production users, uptime, performance metrics, employer integration, or development history.
