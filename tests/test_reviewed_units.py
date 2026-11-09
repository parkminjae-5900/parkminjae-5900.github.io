import unittest
from pathlib import Path
from unittest.mock import patch
from test_scan_official_funeral_prices import scan,record,HAS_BS4

@unittest.skipUnless(HAS_BS4,'BeautifulSoup required')
class ReviewedUnitTests(unittest.TestCase):
    def source(self,n):
        h=dict(zip(['anyang','mokpo','daejeon'],scan.REVIEWED_UNIT_HOSTS))[n]
        return (Path(__file__).parent/f'fixtures/{n}-units.html').read_text(),'https://www.'+h+scan.REVIEWED_UNIT_HOSTS[h]
    def parse(self,n,transform=lambda s:s):
        html,url=self.source(n)
        return scan.reviewed_unit_prices(scan.BeautifulSoup(transform(html),'html.parser'),url)
    def test_complete_rows(self):
        for n,count,rooms in [('anyang',24,20),('mokpo',10,8),('daejeon',26,16)]:
            p=self.parse(n);self.assertEqual(len(p),count)
            self.assertEqual(sum(x['category']=='빈소' for x in p),rooms)
            self.assertTrue(all(x['unit'] in ['1일','1시간'] for x in p if x['category']=='빈소'))
    def test_independent_day_hour_prices(self):
        p=[x for x in self.parse('anyang') if '특2호' in x['label']]
        self.assertEqual([(x['amount'],x['unit']) for x in p],[(1872000,'1일'),(75000,'1시간')])
        self.assertEqual([(x['amount'],x['unit']) for x in self.parse('mokpo')[:2]],[(50000,'1일'),(2100,'1시간')])
    def test_unconfirmed_units(self):
        for n in ['anyang','daejeon']:
            self.assertTrue(all(x['unit']=='' and '기준 확인' in x['label'] for x in self.parse(n) if x['category']=='염습/입관'))
    def test_daejeon_special_prices(self):
        p=self.parse('daejeon')
        self.assertEqual([x['amount'] for x in p if x['category']=='영결식장'],[0])
        self.assertIn((30000,'12시간 미만'),[(x['amount'],x['unit']) for x in p if '사산아' in x['label']])
        self.assertTrue(any('18:00~06:00' in x['label'] for x in p))
    def test_changes_fail_closed(self):
        for n,a,b in [('anyang','이용 요금(1일)','이용 요금'),('mokpo','시간당','금액'),('daejeon','원/시간','원'),('anyang','12시간 초과','12시간 이상'),('mokpo','12시간 이상','12시간 초과'),('daejeon','1시간 미만 = 1시간','시간 계산 변경'),('anyang','특2호','변경'),('mokpo','2호실(55평)','변경'),('daejeon','특2호실','변경')]:
            with self.subTest(n=n,a=a):self.assertEqual(self.parse(n,lambda s:s.replace(a,b)),[])
    def test_provenance_and_row_guard(self):
        for n in ['anyang','mokpo','daejeon']:
            _,url=self.source(n);p=self.parse(n);old=record(source_url=url,prices=p)
            self.assertEqual(scan.identity_guard(record(source_url=url),old,url),(False,'explicit_unit_review_required'))
            self.assertEqual(scan.identity_guard(record(source_url=url,prices=p[:-1]),old,url),(False,'reviewed_price_rows_changed'))
            self.assertTrue(scan.identity_guard(old,old,url)[0])
    def test_live_routing_preserves_notes(self):
        for n in ['anyang','mokpo','daejeon']:
            html,url=self.source(n)
            with patch.object(scan,'get_html',return_value=(html,url)) as get,patch.object(scan,'candidate_links',return_value=[]),patch.object(scan.time,'sleep'):
                res=scan.scan_hall({'homepageUrl':'https://'+url.split('/')[2]})
            self.assertEqual(get.call_args.args[1],url)
            self.assertEqual(res['status'],'priced')
            self.assertEqual(res['sourceNote'],scan.REVIEWED_UNIT_NOTES[scan.host(url)])
    def test_no_generic_fallback(self):
        html,url=self.source('anyang');html=html.replace('특2호','변경')
        with patch.object(scan,'get_html',return_value=(html,url)),patch.object(scan,'candidate_links',return_value=[]),patch.object(scan.time,'sleep'):
            self.assertEqual(scan.scan_hall({'homepageUrl':url})['status'],'no_price_found')
