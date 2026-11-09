import importlib.util
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

if importlib.util.find_spec("requests") is None:
    requests=types.ModuleType("requests")
    requests.Session=lambda: None
    sys.modules["requests"]=requests
HAS_BS4=importlib.util.find_spec("bs4") is not None
if not HAS_BS4:
    bs4=types.ModuleType("bs4")
    bs4.BeautifulSoup=object
    sys.modules["bs4"]=bs4

SCRIPT=Path(__file__).parents[1]/"scripts"/"scan_official_funeral_prices.py"
spec=importlib.util.spec_from_file_location("price_scan",SCRIPT)
scan=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

def price(category="빈소",amount=10000):
    return {"category":category,"label":category,"amount":amount,"unit":"1시간"}

def record(name="교원예움 서서울장례식장",address="서울 영등포구",source_url="",prices=None):
    return {
        "facilityName":name,
        "address":address,
        "sourceUrl":source_url,
        "sourceGrade":"A",
        "prices":prices or [price()],
    }

def key(x):
    return scan.norm(x.get("facilityName",""))+"|"+scan.norm(x.get("address",""))

class PromotionGuardTests(unittest.TestCase):
    def test_branch_code_mismatch_is_rejected(self):
        old=record(source_url="https://example.test/Site/Funeral?fnrCd=1000")
        new=record(source_url="https://example.test/Site/Funeral?fnrCd=1001")
        self.assertEqual(scan.identity_guard(new,old,"https://example.test"),(False,"branch_code_mismatch"))

    def test_branch_code_missing_is_rejected(self):
        old=record(source_url="https://example.test/Site/Funeral?fnrCd=1000")
        new=record(source_url="https://example.test/prices")
        self.assertEqual(scan.identity_guard(new,old,"https://example.test"),(False,"branch_code_missing"))

    def test_same_branch_incomplete_prices_are_rejected(self):
        old=record(
            name="교원예움 화성장례식장",
            source_url="https://example.test/Site/Funeral?fnrCd=1001",
            prices=[price("빈소"),price("안치실")],
        )
        new=record(
            name="교원예움 화성장례식장",
            source_url="https://example.test/Site/Funeral?fnrCd=1001",
            prices=[price("빈소")],
        )
        self.assertEqual(scan.identity_guard(new,old,"https://example.test"),(False,"category_coverage_regression"))

    def test_guard_success_is_not_called_verified(self):
        old=record(source_url="https://example.test/prices")
        new=record(source_url="https://example.test/prices")
        self.assertEqual(scan.identity_guard(new,old,"https://example.test"),(True,"guard_passed"))

    def test_saved_promotion_is_re_evaluated_after_guard_change(self):
        old=record(source_url="https://example.test/Site/Funeral?fnrCd=1000")
        saved={
            "status":"priced",
            "homepage":"https://example.test",
            "facilityName":old["facilityName"],
            "address":old["address"],
            "sourceUrl":"https://example.test/Site/Funeral?fnrCd=1001",
            "prices":[price()],
            "promotion":{"eligible":True,"reason":"verified","guardVersion":1},
        }
        results={"saved":saved}
        scan.reevaluate_saved_promotions(results,{key(old):old},key,[])
        self.assertEqual(saved["promotion"]["eligible"],False)
        self.assertEqual(saved["promotion"]["reason"],"branch_code_mismatch")
        self.assertEqual(saved["promotion"]["guardVersion"],scan.PROMOTION_GUARD_VERSION)
        self.assertEqual(saved["promotion"]["basis"],"stored_scan_recheck")

    def test_summary_separates_discovery_promotion_and_overlap(self):
        a=record(name="A",address="주소A")
        b=record(name="B",address="주소B")
        c=record(name="C",address="주소C")
        results={
            "a":{**a,"status":"priced","promotion":{"eligible":True,"reason":"guard_passed"}},
            "b":{**b,"status":"priced","promotion":{"eligible":False,"reason":"branch_code_mismatch"}},
            "c":{**c,"status":"priced"},
            "x":{"facilityName":"X","address":"주소X","status":"no_price_found"},
        }
        counts,reasons,overlap=scan.summarize_promotions(results,[a,b],key)
        self.assertEqual(counts,{"eligible":1,"rejected":1,"unchecked":1})
        self.assertEqual(reasons,{"guard_passed":1,"branch_code_mismatch":1,"not_evaluated":1})
        self.assertEqual(overlap,2)

class BranchRoutingTests(unittest.TestCase):
    HOME="https://www.kyowonyeum.co.kr"
    BRANCH=HOME+"/Site/Funeral?fnrCd=1002"
    OTHER=HOME+"/Site/Funeral?fnrCd=1001"

    def setUp(self):
        self.h={"fcltNm":"교원예움 평택장례식장","addr":"경기도 평택시 신평로 205","homepageUrl":self.HOME}
        self.old=record(name=self.h["fcltNm"],address=self.h["addr"],source_url=self.BRANCH)

    def test_exact_curated_branch_is_start_page(self):
        self.assertEqual(scan.branch_scan_start(self.h,self.old,self.HOME),self.BRANCH)

    def test_untrusted_or_different_identity_is_not_reused(self):
        for changes in ({"sourceGrade":"B"},{"address":"다른 주소"},{"facilityName":"다른 지점"},
                        {"sourceUrl":"https://other.test/Site/Funeral?fnrCd=1002"}):
            with self.subTest(changes=changes):
                self.assertEqual(scan.branch_scan_start(self.h,{**self.old,**changes},self.HOME),self.HOME)

    def test_explicit_home_branch_is_preserved(self):
        self.assertEqual(scan.branch_scan_start(self.h,self.old,self.OTHER),self.OTHER)
        self.assertEqual(scan.identity_guard(record(name=self.h["fcltNm"],address=self.h["addr"],source_url=self.OTHER),self.old,self.HOME),
                         (False,"branch_code_mismatch"))

    def run_scan(self,responses,links=None):
        with patch.object(scan,"get_html",side_effect=responses) as get_html, \
             patch.object(scan,"session"), patch.object(scan,"BeautifulSoup"), patch.object(scan,"pyeongtaek_prices",return_value=None), \
             patch.object(scan,"candidate_links",return_value=links or []), \
             patch.object(scan,"table_prices",return_value=[price()]), \
             patch.object(scan,"text_prices",return_value=[]), patch.object(scan.time,"sleep"):
            result=scan.scan_hall(self.h,self.old)
        return result,get_html

    def test_other_branches_and_uncoded_pages_are_never_fetched(self):
        result,get_html=self.run_scan([("html",self.BRANCH)],
                                     [self.OTHER,self.HOME+"/prices",self.BRANCH])
        self.assertEqual(result["sourceUrl"],self.BRANCH)
        self.assertEqual(result["homepage"],self.HOME)
        self.assertEqual(get_html.call_count,1)
        self.assertEqual(get_html.call_args.args[1],self.BRANCH)

    def test_redirect_to_wrong_branch_or_host_is_rejected(self):
        for target in (self.OTHER,self.HOME,"https://other.test/?fnrCd=1002"):
            with self.subTest(target=target):
                result,_=self.run_scan([("html",target)])
                self.assertEqual(result["status"],"no_price_found")
                self.assertNotIn("prices",result)

    def test_secondary_redirect_cannot_masquerade_as_requested_branch(self):
        link=self.BRANCH+"&view=prices"
        with patch.object(scan,"get_html",side_effect=[("html",self.BRANCH),("wrong branch",self.OTHER)]), \
             patch.object(scan,"session"), patch.object(scan,"BeautifulSoup"), patch.object(scan,"pyeongtaek_prices",return_value=None), \
             patch.object(scan,"candidate_links",return_value=[link]), \
             patch.object(scan,"table_prices",return_value=[]), \
             patch.object(scan,"text_prices",return_value=[]), patch.object(scan.time,"sleep"):
            result=scan.scan_hall(self.h,self.old)
        self.assertEqual(result["status"],"no_price_found")

    def test_https_retry_preserves_branch_path(self):
        result,get_html=self.run_scan([(None,None),("html",self.BRANCH.replace("https:","http:"))])
        self.assertEqual(get_html.call_args.args[1],self.BRANCH.replace("https:","http:"))
        self.assertEqual(result["sourceUrl"],self.BRANCH.replace("https:","http:"))

    def test_non_branch_site_still_selects_richer_page_and_records_final_url(self):
        h={"homepageUrl":"https://example.test"}
        with patch.object(scan,"get_html",side_effect=[("home","https://example.test"),("prices","https://example.test/current-prices")]), \
             patch.object(scan,"session"), patch.object(scan,"BeautifulSoup"), patch.object(scan,"pyeongtaek_prices",return_value=None), \
             patch.object(scan,"candidate_links",return_value=["https://example.test/prices"]), \
             patch.object(scan,"table_prices",side_effect=[[],[price()]]), \
             patch.object(scan,"text_prices",return_value=[]), patch.object(scan.time,"sleep"):
            result=scan.scan_hall(h)
        self.assertEqual(result["sourceUrl"],"https://example.test/current-prices")

    def test_missing_homepage_is_unchanged(self):
        self.assertEqual(scan.scan_hall({}),{"status":"no_homepage"})

    def test_unknown_branch_retains_existing_guard(self):
        new=record(source_url=self.BRANCH)
        self.assertEqual(scan.identity_guard(new,None,self.HOME),(False,"branch_code_unverifiable"))

    def test_incomplete_correct_branch_does_not_replace_curated_prices(self):
        self.old["prices"]=[price(),price("안치실"),price("염습/입관")]
        result,_=self.run_scan([("html",self.BRANCH)])
        candidate={**result,"facilityName":self.h["fcltNm"],"address":self.h["addr"]}
        self.assertEqual(scan.identity_guard(candidate,self.old,self.HOME),(False,"category_coverage_regression"))
        self.assertEqual(len(self.old["prices"]),3)

@unittest.skipUnless(HAS_BS4,"beautifulsoup4 required for source HTML adapter")
class PyeongtaekParserTests(unittest.TestCase):
    URL="https://www.kyowonyeum.co.kr/Site/Funeral?fnrCd=1002"

    def setUp(self):
        self.html=(Path(__file__).parent/"fixtures"/"kyowon_pyeongtaek_prices.html").read_text(encoding="utf-8")

    def parse(self,html=None,url=None):
        return scan.pyeongtaek_prices(scan.BeautifulSoup(html or self.html,"html.parser"),url or self.URL)

    def test_all_official_rows_and_shared_price_are_explicit(self):
        rows=self.parse()
        self.assertEqual([(r["label"],r["amount"],r["unit"]) for r in rows],[
            ("202호 빈소",50000,"1시간"),("203호 빈소",41000,"1시간"),
            ("101호·102호 빈소",36000,"1시간"),("201호·204호 빈소",28000,"1시간"),
            ("301호·302호 빈소",23000,"1시간"),("303호 빈소",23000,"1시간"),
            ("입관실/염습실",400000,"1회"),("안치실",120000,"1일")])
        self.assertEqual(scan.category_coverage(rows),{"빈소","안치실","염습/입관"})

    def test_other_branches_and_domains_keep_generic_parser(self):
        for url in (self.URL.replace("1002","1001"),self.URL.replace("kyowonyeum.co.kr","other.test")):
            self.assertIsNone(self.parse(url=url))

    def test_wrong_identity_missing_price_unit_or_structure_fails_closed(self):
        changes=[("<h1 class=\"C\">평택장례식장</h1>","<h1>화성장례식장</h1>"),
                 ("평택시 신평로 205","평택시 신평로 999"),
                 ("50,000원","상담문의"),("41,000원","41,000원 또는 45,000원"),
                 ("기준 1시간","기준 미정"),("rowspan=\"2\"","rowspan=\"99\""),
                 ("· 부대시설","· 다른 시설")]
        for before,after in changes:
            with self.subTest(before=before):
                self.assertIn(before,self.html)
                self.assertEqual(self.parse(self.html.replace(before,after)),[])

    def test_shared_price_is_not_guessed_if_rowspan_removed(self):
        # Remove only the shared price span: 303호 then has no price cell.
        html=self.html.replace('<td rowspan="2">23,000원','<td>23,000원')
        self.assertNotEqual(html,self.html)
        self.assertEqual(self.parse(html),[])

    def test_scan_uses_adapter_without_prose_duplicates(self):
        h={"fcltNm":"교원예움 평택장례식장","addr":"경기도 평택시 신평로 205","homepageUrl":self.URL}
        with patch.object(scan,"session"),patch.object(scan,"get_html",return_value=(self.html,self.URL)), \
             patch.object(scan,"candidate_links",return_value=[]),patch.object(scan.time,"sleep"):
            result=scan.scan_hall(h)
        self.assertEqual(len(result["prices"]),8)
        self.assertEqual(result["sourceUrl"],self.URL)
        old=record(name=h["fcltNm"],address=h["addr"],source_url=self.URL,prices=self.parse())
        self.assertEqual(scan.identity_guard({**result,"address":h["addr"]},old,self.URL),(True,"guard_passed"))

    def test_invalid_adapter_page_does_not_fall_back_to_prose(self):
        html=self.html.replace("기준 1시간","기준 미정")
        with patch.object(scan,"session"),patch.object(scan,"get_html",return_value=(html,self.URL)), \
             patch.object(scan,"candidate_links",return_value=[]),patch.object(scan.time,"sleep"), \
             patch.object(scan,"text_prices") as prose:
            result=scan.scan_hall({"homepageUrl":self.URL})
        self.assertEqual(result["status"],"no_price_found")
        prose.assert_not_called()


@unittest.skipUnless(HAS_BS4,"beautifulsoup4 required")
class GijangPricesTests(unittest.TestCase):
    url="http://www.gjhp.kr/location01_05.php"

    def setUp(self):
        self.html=(Path(__file__).parent/"fixtures/gijang_prices.html").read_text(encoding="utf-8")

    def parse(self,html=None,url=None):
        return scan.gijang_prices(scan.BeautifulSoup(html or self.html,"html.parser"),url or self.url)

    def test_daily_amount_not_hourly_note(self):
        prices=self.parse()
        self.assertEqual(len(prices),9)
        self.assertEqual([p for p in prices if p["category"]=="안치실"],
            [{"category":"안치실","label":"안치료","amount":100000,"unit":"1일"}])
        self.assertEqual([p["amount"] for p in prices if p["category"]=="빈소"],[400000,400000,400000,500000,500000])
        self.assertEqual([p["unit"] for p in prices if p["category"]=="염습/입관"],["1회"])

    def test_changed_prices_are_read_not_hardcoded(self):
        prices=self.parse(self.html.replace("100,000원 / 1일","120,000원 / 1일"))
        self.assertEqual([p["amount"] for p in prices if p["category"]=="안치실"],[120000])

    def test_fail_closed_on_changed_or_missing_evidence(self):
        for old,new in [("<title>기장병원</title>","<title>다른 병원</title>"),
                        ("colspan=\"2\"","colspan=\"3\""),
                        ("100,000원 / 1일","100,000원 / 시간"),
                        ("100,000원 / 1일","문의"),
                        ("<th class=\"left-division\">요금</th>","<th>비고</th>")]:
            with self.subTest(old=old):self.assertEqual(self.parse(self.html.replace(old,new)),[])
        self.assertEqual(self.parse(self.html+self.html),[])
        self.assertEqual(self.parse(url="http://www.gjhp.kr/other.php"),[])
        self.assertIsNone(self.parse(url="http://other.example/location01_05.php"))

    def test_scan_does_not_fall_back_on_malformed_table(self):
        html=self.html.replace("100,000원 / 1일","문의")
        with patch.object(scan,"session"), patch.object(scan,"get_html",return_value=(html,self.url)), patch.object(scan,"candidate_links",return_value=[]), patch.object(scan,"text_prices",side_effect=AssertionError("unsafe fallback")), patch.object(scan.time,"sleep"):
            self.assertEqual(scan.scan_hall({"homepageUrl":self.url})["status"],"no_price_found")

    def test_scan_and_promotion_preserve_existing_categories(self):
        with patch.object(scan,"session"), patch.object(scan,"get_html",return_value=(self.html,self.url)), patch.object(scan,"candidate_links",return_value=[]), patch.object(scan.time,"sleep"):
            result=scan.scan_hall({"homepageUrl":self.url})
        self.assertEqual(result["status"],"priced")
        old={"sourceGrade":"A","address":"기장","prices":[price("빈소"),price("안치실")]}
        result["address"]="기장"
        self.assertTrue(scan.identity_guard(result,old,self.url)[0])

if __name__=="__main__":
    unittest.main()


@unittest.skipUnless(HAS_BS4,"BeautifulSoup required")
class YoungwolTests(unittest.TestCase):
    def fixture(self,n):
        return (Path(__file__).parent/'fixtures'/f'youngwol-{n}.html').read_text()

    def run_scan(self,second=None):
        def fetch(session,url):
            if 'page=2' in url:
                return (second,url) if second is not None else (self.fixture(2),url)
            return self.fixture(1),url
        with patch.object(scan,'get_html',side_effect=fetch), patch.object(scan,'session'):
            return scan.scan_hall({'homepageUrl':'https://www.youngwol.org'})

    def test_complete_inventory_and_exact_units(self):
        result=self.run_scan()
        self.assertEqual(result['status'],'priced')
        self.assertEqual(len(result['prices']),17)
        self.assertEqual(result['prices'][0],{'category':'안치실','label':'안치료 특실1(40평)','amount':3000,'unit':'1시간당'})
        self.assertEqual(result['prices'][-2:],[
            {'category':'염습/입관','label':'염습료','amount':200000,'unit':'1구당'},
            {'category':'염습/입관','label':'염습실사용료','amount':250000,'unit':'1구당'}])

    def test_missing_page_fails_closed(self):
        self.assertEqual(self.run_scan('')['status'],'no_price_found')

    def test_duplicate_page_fails_closed(self):
        self.assertEqual(self.run_scan(self.fixture(1))['status'],'no_price_found')

    def test_changed_header_fails_closed(self):
        self.assertEqual(self.run_scan(self.fixture(2).replace('규격','번호'))['status'],'no_price_found')

    def test_changed_total_fails_closed(self):
        self.assertEqual(self.run_scan(self.fixture(2).replace('Total 17건','Total 18건'))['status'],'no_price_found')

    def test_foreign_source_rejected(self):
        soup=scan.BeautifulSoup(self.fixture(1),'html.parser')
        self.assertIsNone(scan.youngwol_page(soup,'https://example.com/bbs/board.php?bo_table=funeral_01'))



class PriceUnitReviewTests(unittest.TestCase):
    def test_review_hold_blocks_live_and_saved_promotion(self):
        old=record(prices=[price("안치실")])
        old["priceReviewRequired"]=True
        for amount,unit in [(230000,"시간당"),(240000,"시간당"),(7000,"1일"),(9600,"1시간")]:
            candidate=record(prices=[dict(price("안치실",amount),unit=unit)])
            self.assertEqual(scan.identity_guard(candidate,old,""),
                             (False,"price_unit_review_required"))

    def test_review_hold_does_not_change_other_records(self):
        old=record(prices=[price()])
        self.assertEqual(scan.identity_guard(record(prices=[price()]),old,""),
                         (True,"guard_passed"))

    def test_reviewed_data_never_displays_suspect_amounts(self):
        import json
        data=json.loads((SCRIPT.parents[1]/"data/funeral-hall-prices.json").read_text())
        targets={"울산대학교병원장례식장":4,"경상국립대학교병원장례식장":0}
        found=[]
        for rec in data["items"]:
            if rec["facilityName"] not in targets:continue
            found.append(rec["facilityName"])
            self.assertTrue(rec["priceReviewRequired"])
            storage=[p for p in rec["prices"] if p["category"]=="안치실"]
            self.assertEqual(len(storage),1)
            self.assertIsNone(storage[0]["amount"])
            self.assertEqual(storage[0]["unit"],"")
            self.assertEqual(len(rec["prices"])-1,targets[rec["facilityName"]])
        self.assertEqual(set(found),set(targets))


@unittest.skipUnless(HAS_BS4,"BeautifulSoup required")
class EwhaSeoulTests(unittest.TestCase):
    URL="https://seoul.eumc.ac.kr/funeral/guide/facility.do"
    def setUp(self):
        self.html=(SCRIPT.parents[1]/"tests/fixtures/ewha-seoul-facility.html").read_text()
        self.soup=scan.BeautifulSoup(self.html,"html.parser")
    def test_six_types_preserve_equal_price_special_rooms(self):
        rows=scan.ewha_seoul_prices(self.soup,self.URL)
        self.assertEqual(len(rows),6)
        self.assertEqual([r["amount"] for r in rows],[1080000,1296000,2400000,2592000,2592000,4080000])
        self.assertTrue(all(r["unit"]=="1일" for r in rows))
        self.assertIn("특실5 · 305.7㎡",rows[3]["label"])
        self.assertIn("특실3 · 306.2㎡",rows[4]["label"])
    def test_other_branch_does_not_use_adapter(self):
        self.assertIsNone(scan.ewha_seoul_prices(self.soup,self.URL.replace("seoul.","mokdong.")))
    def test_exact_duplicate_card_is_removed(self):
        doubled=scan.BeautifulSoup(self.html+self.html,"html.parser")
        self.assertEqual(len(scan.ewha_seoul_prices(doubled,self.URL)),6)
    def test_changed_price_read_from_source(self):
        soup=scan.BeautifulSoup(self.html.replace("1,080,000","1,100,000"),"html.parser")
        self.assertEqual(scan.ewha_seoul_prices(soup,self.URL)[0]["amount"],1100000)
    def test_missing_unit_does_not_fall_back_to_nested_prose(self):
        broken=self.html.replace("빈소 임대료(1일)","빈소 임대료")
        with patch.object(scan,"session",return_value=None),patch.object(scan,"get_html",return_value=(broken,self.URL)),patch.object(scan,"candidate_links",return_value=[]),patch.object(scan.time,"sleep"):
            result=scan.scan_hall({"homepageUrl":self.URL})
        self.assertEqual(result["status"],"no_price_found")
    def test_scanner_and_published_data_agree(self):
        import json
        with patch.object(scan,"session",return_value=None),patch.object(scan,"get_html",return_value=(self.html,self.URL)),patch.object(scan,"candidate_links",return_value=[]),patch.object(scan.time,"sleep"):
            result=scan.scan_hall({"homepageUrl":self.URL})
        self.assertEqual(result["status"],"priced")
        data=json.loads((SCRIPT.parents[1]/"data/funeral-hall-prices.json").read_text())
        published=next(x for x in data["items"] if x["facilityName"]=="이대서울병원장례식장")
        self.assertEqual(len(published["prices"]),6)
        # Published amounts may legitimately change after a later official scan.
        identity=lambda rows: [(r["category"],r["label"],r["unit"]) for r in rows]
        self.assertEqual(identity(result["prices"]),identity(published["prices"]))
        self.assertEqual(scan.identity_guard(published,published,self.URL),(True,"guard_passed"))
