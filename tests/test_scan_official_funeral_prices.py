import importlib.util
import unittest
from pathlib import Path

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

if __name__=="__main__":
    unittest.main()
