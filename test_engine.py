import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fiberwatch.engine import Event, analyze, read_events
T = datetime(2026, 1, 1, tzinfo=timezone.utc)
def e(n, ont, status='los', pon='p', rx=None):
    return Event(T+timedelta(seconds=n), ont, pon, status, rx)
class EngineTests(unittest.TestCase):
    def test_demo(self):
        report = analyze(read_events('examples/events.csv'))
        self.assertEqual({i['kind'] for i in report['incidents']}, {'shared_pon_failure','weak_optical_signal','ont_flapping'})
    def test_unique_onts_and_window(self):
        self.assertEqual(analyze([e(0,'a'),e(0,'a'),e(1,'a'),e(2,'b')])['incident_count'],0)
        self.assertEqual(analyze([e(0,'a'),e(121,'b'),e(122,'c')])['incident_count'],0)
    def test_boundary_and_order(self):
        samples=[e(120,'c'),e(0,'a'),e(60,'b')]
        self.assertEqual(analyze(samples)['incident_count'],1)
        self.assertEqual(analyze(samples), analyze(list(reversed(samples))))
    def test_recovery_cancels_failure(self):
        self.assertEqual(analyze([e(0,'a'),e(1,'a','up'),e(2,'b'),e(3,'c')])['incident_count'],0)
    def test_pon_isolation(self):
        self.assertEqual(analyze([e(0,'a'),e(1,'b'),e(2,'c',pon='q')])['incident_count'],0)
    def test_weak_only_latest_and_online(self):
        self.assertEqual(analyze([e(0,'a','up',rx=-30),e(1,'a','up',rx=-18)])['incident_count'],0)
        self.assertEqual(analyze([e(0,'a','down',rx=-30)])['incident_count'],0)
    def test_flapping_uses_sliding_window(self):
        samples=[e(n,'a','up' if i%2==0 else 'down') for i,n in enumerate([0,119,120,121,122])]
        self.assertEqual(analyze(samples)['incidents'][0]['kind'],'ont_flapping')
    def test_rejects_naive_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.csv';p.write_text('timestamp,ont,pon,status,rx_dbm\n2026-01-01T00:00:00,a,p,up,-18\n')
            with self.assertRaisesRegex(ValueError,'row 2'):
                read_events(p)
    def test_invalid_options(self):
        with self.assertRaises(ValueError): analyze([],window_seconds=0)
