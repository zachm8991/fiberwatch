import argparse
import json
from pathlib import Path
from .engine import read_events, analyze

def main():
    parser = argparse.ArgumentParser(description='Analyze normalized ONT telemetry; no device connections.')
    parser.add_argument('csv')
    parser.add_argument('--window', type=int, default=120)
    parser.add_argument('--outage-min', type=int, default=3)
    parser.add_argument('--weak-rx', type=float, default=-27)
    parser.add_argument('--output', help='Write JSON report; otherwise print it')
    args = parser.parse_args()
    try:
        report = analyze(read_events(args.csv), args.window, args.outage_min, args.weak_rx)
        payload = json.dumps(report, indent=2) + '\n'
        if args.output:
            Path(args.output).write_text(payload, encoding='utf-8')
        else:
            print(payload, end='')
    except (OSError, ValueError) as exc:
        parser.exit(2, f'error: {exc}\n')
