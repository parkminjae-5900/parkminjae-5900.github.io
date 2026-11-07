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
if importlib.util.find_spec("bs4") is None:
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
             patch.object(scan,"session"), patch.object(scan,"BeautifulSoup"), \
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
             patch.object(scan,"session"), patch.object(scan,"BeautifulSoup"), \
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
             patch.object(scan,"session"), patch.object(scan,"BeautifulSoup"), \
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

if __name__=="__main__":
    unittest.main()
