"""Dated evidence stays immutable even when the live scanner updates prices."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/priority-official-price-audit-20261026.json'


def validate(audit):
    facilities = audit['facilities']
    keys = [(f['facilityName'], f['address']) for f in facilities]
    assert len(keys) == len(set(keys)) == 47
    known = dict(zip(keys, facilities))
    evidence_keys = set()
    for e in audit['verifiedEvidence']:
        key = (e['facilityName'], e['address'])
        assert key in known and key not in evidence_keys
        evidence_keys.add(key)
        f, r = known[key], e['record']
        assert f['status'] in ('newly_verified', 'reverified', 'reverified_expanded')
        assert (r['facilityName'], r['address']) == key
        assert e['officialFacilityName'] and e['officialAddress'] and e['identityBasis']
        assert e['sourcePriceTables'] and len(e['retrievedTextSha256']) == 64
        assert r['sourceUrl'] == e['sourceUrl']
        assert urlparse(r['sourceUrl']).scheme in ('http', 'https')
        assert r['verifiedAt'] == e['checkedAt'] == audit['checkedAt']
        assert r['sourceGrade'] == 'A' and r['sourceNote']
        assert len(r['prices']) == f['verifiedPriceCount']
        for p in r['prices']:
            assert p['category'] and p['label']
            assert type(p['amount']) is int and 1000 <= p['amount'] <= 20000000
            assert p['unit'] in ('1시간', '1일', '1회', '1건', '3일')
        if 'kyowonyeum.co.kr' in r['sourceUrl']:
            expected = {'인천사랑병원장례식장': '1009', '교원예움 서서울장례식장': '1000'}
            assert parse_qs(urlparse(r['sourceUrl']).query)['fnrCd'] == [expected[key[0]]]
    assert len(evidence_keys) == 6
    for s in audit['summary']:
        fs = [f for f in facilities if (f['region'] == '인천광역시' if s['region'] == '인천' else f['district'] == s['region'].split()[1] + '구')]
        assert len(fs) == s['totalFacilities']
        assert sum(f['hadExistingPrice'] for f in fs) == s['existingPriceFacilities']
        for status, field in [('newly_verified', 'newlyVerifiedFacilities'), ('unverified', 'unverifiedFacilities'), ('existing_not_reverified', 'existingAwaitingReverification')]:
            assert sum(f['status'] == status for f in fs) == s[field]
        assert sum(f['status'].startswith('reverified') for f in fs) == s['reverifiedFacilities']


class PriorityPriceAuditTests(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads(AUDIT.read_text())

    def test_complete_evidence_and_summary(self):
        validate(self.audit)

    def test_wrong_address_rejected(self):
        self.audit['verifiedEvidence'][0]['record']['address'] = '다른 지점'
        with self.assertRaises(AssertionError): validate(self.audit)

    def test_missing_unit_rejected(self):
        self.audit['verifiedEvidence'][0]['record']['prices'][0]['unit'] = ''
        with self.assertRaises(AssertionError): validate(self.audit)

    def test_other_branch_rejected(self):
        e = next(e for e in self.audit['verifiedEvidence'] if e['facilityName'] == '인천사랑병원장례식장')
        e['sourceUrl'] = e['record']['sourceUrl'] = e['sourceUrl'].replace('1009', '1000')
        with self.assertRaises(AssertionError): validate(self.audit)

    def test_ambiguous_items_excluded(self):
        records = {e['facilityName']: e['record'] for e in self.audit['verifiedEvidence']}
        self.assertFalse(any(p['category'] == '빈소' for p in records['인천사랑병원장례식장']['prices']))
        self.assertFalse(any('VIP' in p['label'] for p in records['(주)세종병원장례식장']['prices']))
        self.assertFalse(any(p['category'] == '청소/관리' for p in records['인천광역시의료원 장례식장']['prices']))


if __name__ == '__main__':
    unittest.main()
