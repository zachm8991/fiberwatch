"""Deterministic incident correlation over normalized, synthetic ONT events."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import csv
import math

@dataclass(frozen=True)
class Event:
    timestamp: datetime
    ont: str
    pon: str
    status: str
    rx_dbm: float | None

def read_events(path):
    result = []
    with open(path, newline='', encoding='utf-8') as source:
        for line, row in enumerate(csv.DictReader(source), 2):
            try:
                timestamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    raise ValueError('timestamp needs a UTC offset')
                ont, pon = row['ont'].strip(), row['pon'].strip()
                status = row['status'].strip().lower()
                if not ont or not pon or status not in {'up', 'los', 'down'}:
                    raise ValueError('expected nonempty identifiers and up/los/down status')
                rx = float(row['rx_dbm']) if row['rx_dbm'].strip() else None
                if rx is not None and (not math.isfinite(rx) or not -60 <= rx <= 10):
                    raise ValueError('invalid receive power')
                result.append(Event(timestamp.astimezone(timezone.utc), ont, pon, status, rx))
            except (KeyError, ValueError, AttributeError) as exc:
                raise ValueError(f'CSV row {line}: {exc}') from exc
    # Duplicate samples must not manufacture flapping or inflate outage impact.
    return sorted(set(result), key=lambda e: (e.timestamp, e.pon, e.ont, e.status, str(e.rx_dbm)))

def analyze(events, window_seconds=120, outage_min=3, weak_rx=-27.0, flap_transitions=4):
    if window_seconds <= 0 or outage_min < 2 or flap_transitions < 2 or not math.isfinite(weak_rx):
        raise ValueError('invalid analysis configuration')
    events = sorted(set(events), key=lambda e: (e.timestamp, e.pon, e.ont, e.status, str(e.rx_dbm)))
    by_ont, by_pon = defaultdict(list), defaultdict(list)
    for event in events:
        by_ont[(event.pon, event.ont)].append(event)
        by_pon[event.pon].append(event)
    incidents = []
    def emit(kind, severity, pon, onts, start, end, evidence, action):
        incidents.append(dict(kind=kind, severity=severity, pon=pon, onts=sorted(onts),
                              start=start.isoformat(), end=end.isoformat(),
                              evidence=evidence, next_step=action))
    # Sliding window tracks latest observed state for each ONT within that window.
    # An UP recovery cancels its prior failed observation immediately.
    for pon, samples in sorted(by_pon.items()):
        latest = {}; previous_end = None
        for event in samples:
            cutoff = event.timestamp - timedelta(seconds=window_seconds)
            latest = {ont: sample for ont, sample in latest.items() if sample.timestamp >= cutoff}
            latest[event.ont] = event
            failed = {ont: sample for ont, sample in latest.items() if sample.status != 'up'}
            if len(failed) >= outage_min:
                start = min(s.timestamp for s in failed.values())
                if previous_end is not None and start <= previous_end:
                    current = incidents[-1]
                    current['onts'] = sorted(set(current['onts']) | set(failed))
                    current['end'] = event.timestamp.isoformat()
                    current['evidence']['max_failed_onts'] = max(current['evidence']['max_failed_onts'], len(failed))
                else:
                    emit('shared_pon_failure', 'high', pon, failed, start, event.timestamp,
                         {'max_failed_onts': len(failed), 'window_seconds': window_seconds},
                         'Check shared PON alarms and upstream equipment; verify outage before dispatch.')
                previous_end = event.timestamp
    for (pon, ont), samples in sorted(by_ont.items()):
        last = samples[-1]
        if last.status == 'up' and last.rx_dbm is not None and last.rx_dbm < weak_rx:
            emit('weak_optical_signal', 'medium', pon, [ont], last.timestamp, last.timestamp,
                 {'rx_dbm': last.rx_dbm, 'configured_threshold': weak_rx},
                 'Compare with vendor limits and historical levels; inspect optical path through approved procedures.')
        transitions = [b.timestamp for a,b in zip(samples, samples[1:]) if (a.status == 'up') != (b.status == 'up')]
        left = 0; peak = 0; peak_range = None
        for right, timestamp in enumerate(transitions):
            while timestamp - transitions[left] > timedelta(seconds=window_seconds):
                left += 1
            if right-left+1 > peak:
                peak = right-left+1; peak_range = (transitions[left], timestamp)
        if peak >= flap_transitions:
            emit('ont_flapping', 'medium', pon, [ont], *peak_range,
                 {'transitions': peak, 'window_seconds': window_seconds},
                 'Correlate power, optical, and Ethernet events before attributing a cause.')
    incidents.sort(key=lambda i: (i['start'], i['pon'], i['kind'], i['onts']))
    return {'event_count': len(events), 'incident_count': len(incidents), 'incidents': incidents}
