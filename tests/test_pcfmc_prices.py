import json
import unittest
from pathlib import Path
from unittest.mock import patch
from test_scan_official_funeral_prices import scan,record,HAS_BS4,key

@unittest.skipUnless(HAS_BS4,'BeautifulSoup required')
class PcfmcPriceTests(unittest.TestCase):
    def hall(self,name='진부장례식장'):
        target=scan.PCFMC_TARGETS[name]
        return {'fcltNm':name,'addr':'강원도 '+target['address']+' (건물명)','homepageUrl':'https://www.pcfmc.or.kr/facilities07'}
    def html(self,name='jinbu'):
        return (Path(__file__).parent/f'fixtures/pcfmc-{name}.html').read_text()
    def parse(self,name,html):
        h=self.hall(name)
        return scan.pcfmc_prices(scan.BeautifulSoup(html,'html.parser'),name,scan.pcfmc_target(h['fcltNm'],h['addr']))
    def test_current_jinbu_page_price_title_mismatch_is_rejected(self):
        self.assertEqual(self.parse('진부장례식장',self.html()),([], 'facility_price_table_name_mismatch'))
    def test_pyeongchang_rows_keep_area_and_explicit_unit(self):
        rows,reason=self.parse('평창장례식장',self.html('pyeongchang'))
        self.assertEqual(reason,'guard_passed');self.assertEqual(len(rows),8)
        self.assertEqual([(r['amount'],r['unit']) for r in rows],[(40000,'1일'),(53000,'1일'),(120000,'1일'),(160000,'1일'),(40000,'1일'),(53000,'1일'),(100000,'1회'),(130000,'1회')])
        self.assertEqual([r['label'] for r in rows[:2]],['분향실 · 관내','분향실 · 관외'])
    def test_future_corrected_jinbu_title_can_parse_but_not_unreviewed_data(self):
        html=self.html().replace('평창장례식장 사용료','진부장례식장 사용료')
        self.assertEqual(len(self.parse('진부장례식장',html)[0]),8)
    def test_navigation_name_alone_does_not_identify_page(self):
        html=self.html('pyeongchang')+'<a>진부장례식장</a>'
        self.assertEqual(self.parse('진부장례식장',html)[1],'facility_page_name_mismatch')
    def test_page_identity_address_and_table_structure_fail_closed(self):
        original=self.html('pyeongchang')
        for a,b in [('평창군 종부로 61','평창군 종부로 610'),('금액(1일 사용료)','금액'),('관외','기타'),('53,000원','문의'),('오전 12시부터 다음 날','다음 날'),('접객실(일반)','특실')]:
            with self.subTest(a=a):self.assertEqual(self.parse('평창장례식장',original.replace(a,b))[0],[])
    def test_feed_identity_is_required_and_province_rename_is_supported(self):
        h=self.hall()
        self.assertIsNotNone(scan.pcfmc_target(h['fcltNm'],h['addr'].replace('강원도','강원특별자치도')))
        for name,addr in [('평창장례식장',h['addr']),(h['fcltNm'],h['addr'].replace('1958-21','1958-210')),(h['fcltNm'],'')]:
            self.assertIsNone(scan.pcfmc_target(name,addr))
    def test_stale_feed_path_routes_to_exact_hall_without_candidate_links(self):
        with patch.object(scan,'get_html',return_value=(self.html(),'https://www.pcfmc.or.kr/facilities09')) as get,patch.object(scan,'candidate_links') as links,patch.object(scan,'table_prices') as generic:
            result=scan.scan_hall(self.hall())
        self.assertEqual(get.call_args.args[1],'https://www.pcfmc.or.kr/facilities09')
        self.assertEqual(result['reviewReason'],'facility_price_table_name_mismatch')
        self.assertNotIn('prices',result);links.assert_not_called();generic.assert_not_called()
    def test_redirect_to_other_facility_or_host_is_rejected(self):
        for url in ['https://www.pcfmc.or.kr/facilities08','https://example.test/facilities09','https://pcfmc.or.kr/facilities09?other=1']:
            with patch.object(scan,'get_html',return_value=(self.html(),url)):
                self.assertEqual(scan.scan_hall(self.hall())['reviewReason'],'facility_source_path_mismatch')
    def test_unknown_identity_is_not_fetched(self):
        with patch.object(scan,'get_html') as get:
            result=scan.scan_hall({**self.hall(),'addr':'다른 주소'})
        self.assertEqual(result['reviewReason'],'facility_identity_unverifiable');get.assert_not_called()
    def test_saved_wrong_source_rejected_even_if_categories_are_complete(self):
        h=self.hall();old=record(name=h['fcltNm'],address=h['addr'],source_url='https://www.pcfmc.or.kr/facilities08')
        self.assertEqual(scan.identity_guard(old,old,h['homepageUrl']),(False,'facility_source_path_mismatch'))
        saved={**old,'status':'priced','homepage':h['homepageUrl']}
        scan.reevaluate_saved_promotions({'x':saved},{key(old):old},key,[])
        self.assertFalse(saved['promotion']['eligible']);self.assertEqual(saved['promotion']['reason'],'facility_source_path_mismatch')
    def test_generic_and_incomplete_rows_cannot_replace_reviewed_source(self):
        h=self.hall('평창장례식장');url='https://www.pcfmc.or.kr/facilities08'
        rows,_=self.parse(h['fcltNm'],self.html('pyeongchang'))
        rec=record(name=h['fcltNm'],address=h['addr'],source_url=url,prices=rows)
        self.assertEqual(scan.identity_guard(rec,rec,h['homepageUrl']),(True,'guard_passed'))
        self.assertEqual(scan.identity_guard({**rec,'prices':rows[:-1]},rec,h['homepageUrl'])[1],'reviewed_price_rows_changed')
        self.assertEqual(scan.identity_guard({**rec,'prices':[{k:v for k,v in r.items() if k!='sourceParser'} for r in rows]},rec,h['homepageUrl'])[1],'facility_price_table_review_required')
    def test_quarantined_record_never_promoted(self):
        h=self.hall();rec=record(name=h['fcltNm'],address=h['addr'],source_url='https://www.pcfmc.or.kr/facilities09')
        self.assertEqual(scan.identity_guard(rec,{**rec,'sourceReviewRequired':True},h['homepageUrl']),(False,'facility_source_review_required'))
    def test_operational_jinbu_has_no_ambiguous_numeric_prices(self):
        db=json.loads((Path(__file__).parents[1]/'data/funeral-hall-prices.json').read_text())
        rec=next(x for x in db['items'] if x['facilityName']=='진부장례식장')
        self.assertEqual(rec['prices'],[]);self.assertTrue(rec['sourceReviewRequired'])
        self.assertEqual(rec['sourceUrl'],'https://www.pcfmc.or.kr/facilities09')
