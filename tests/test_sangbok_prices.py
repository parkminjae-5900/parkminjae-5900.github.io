import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from test_scan_official_funeral_prices import scan,HAS_BS4
HTML=Path('tests/fixtures/sangbok-prices.html').read_text()
HALL={'fcltNm':'창원시립상복공원장례식장','addr':'경상남도 창원시 성산구 공단로474번길 160 (상복동)','homepageUrl':'https://wwwcwsisulorkr/_sangbok/indexphp'}

@unittest.skipUnless(HAS_BS4,'BeautifulSoup required')
class SangbokTest(unittest.TestCase):
 def scan(self,html=HTML,final=None,h=None):
  with patch.object(scan,'session',return_value=object()), patch.object(scan,'get_html',return_value=(html,final or scan.SANGBOK_URL)) as get:
   result=scan.scan_hall(h or HALL)
   return result,get
 def test_broken_raw_url_routes_only_to_verified_page(self):
  result,get=self.scan();self.assertEqual(result['status'],'priced');self.assertEqual(result['homepage'],HALL['homepageUrl'])
  self.assertEqual(get.call_args.args[1],scan.SANGBOK_URL);self.assertEqual(get.call_count,1)
 def test_exact_rates_and_units(self):
  result,_=self.scan();p=result['prices']
  self.assertEqual([x['amount'] for x in p],[1800,2500,40000,70000,80000,140000,300000,400000])
  self.assertEqual([x['unit'] for x in p],['1㎡당(1일)']*2+['1구당(1일)']*2+['1회']*2+['',''])
  self.assertTrue(all(x['requiresManualQuantity'] for x in p[:2]));self.assertIn('총액',result['sourceNote'])
 def test_wrong_name_or_address_does_not_fetch(self):
  for field,value in [('fcltNm','다른장례식장'),('addr','경상남도 창원시 성산구 공단로474번길 161')]:
   h={**HALL,field:value};r,g=self.scan(h=h);self.assertEqual(r['reviewReason'],'facility_identity_unverifiable');g.assert_not_called()
 def test_other_path_redirect_is_rejected(self):
  r,_=self.scan(final='https://www.cwsisul.or.kr/_sangbok/_sub02/sub02_02.html');self.assertEqual(r['reviewReason'],'facility_source_path_mismatch')
 def test_wrong_host_redirect_is_rejected(self):
  r,_=self.scan(final=scan.SANGBOK_URL.replace('www.cwsisul.or.kr','other.example'));self.assertEqual(r['reviewReason'],'facility_source_path_mismatch')
 def test_page_name_and_phone_are_checked(self):
  for old,new,reason in [('창원시립상복공원','다른공원','facility_page_name_mismatch'),('055-712-0930','055-111-1111','facility_page_phone_mismatch')]:
   r,_=self.scan(html=HTML.replace(old,new));self.assertEqual(r['reviewReason'],reason)
 def test_changed_conditions_stop_publication(self):
  for old,new in [('12시간 미만','6시간 미만'),('1개월 전부터','3개월 전부터'),('수습,봉합은 별도','수습,봉합 포함')]:
   r,_=self.scan(html=HTML.replace(old,new));self.assertEqual(r['status'],'no_price_found');self.assertEqual(r['reviewReason'],'facility_price_conditions_changed')
 def test_missing_or_ambiguous_price_is_rejected(self):
  for value in ['상담 필요','1,800원~2,500원']:
   r,_=self.scan(html=HTML.replace('1,800원',value));self.assertEqual(r['status'],'no_price_found')
 def test_network_failure_has_corrected_target(self):
  r,_=self.scan(html=None);self.assertEqual(r['status'],'unreachable');self.assertEqual(r['sourceUrl'],scan.SANGBOK_URL)
 def test_promotion_guard_rejects_generic_or_missing_area_safety(self):
  result,_=self.scan();rec={**result,'facilityName':HALL['fcltNm'],'address':HALL['addr']}
  self.assertEqual(scan.identity_guard(rec,None,HALL['homepageUrl']),(True,'guard_passed'))
  bad=copy.deepcopy(rec);bad['prices'][0].pop('sourceParser');self.assertFalse(scan.identity_guard(bad,None,HALL['homepageUrl'])[0])
  bad=copy.deepcopy(rec);bad['prices'][0].pop('requiresManualQuantity');self.assertEqual(scan.identity_guard(bad,None,HALL['homepageUrl']),(False,'area_unit_review_required'))
 def test_raw_url_is_not_globally_rewritten(self):
  self.assertEqual(scan.normalize_url(HALL['homepageUrl']),HALL['homepageUrl'])
 def test_correct_homepage_supported(self):
  r,g=self.scan(h={**HALL,'homepageUrl':'https://www.cwsisul.or.kr/_sangbok/index.php'});self.assertEqual(r['status'],'priced')

if __name__=='__main__':unittest.main()
