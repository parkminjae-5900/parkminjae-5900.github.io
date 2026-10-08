import copy
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "generate_actual_cases.py"
SPEC = importlib.util.spec_from_file_location("generate_actual_cases", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def published_case():
    return {
        "id": "sample-case",
        "event_month": "2026-10",
        "region": "서울",
        "funeral_hall": "교원예움 서서울장례식장",
        "funeral_type": "가족장",
        "publication": {
            "publish": True,
            "privacy_reviewed": True,
            "costs_verified": True,
            "explicit_photo_permission": False,
        },
        "facility_identity": {
            "facilityName": "교원예움 서서울장례식장",
            "address": "서울특별시 영등포구 선유로 101",
            "officialBranchName": "서서울",
            "sourceUrl": "https://example.go.kr/facility?fnrCd=1000",
            "facilityCode": "1000",
        },
    }


class FacilityIdentityTests(unittest.TestCase):
    def test_exact_identity_passes(self):
        case = published_case()
        MODULE.validate(case)
        self.assertIn("1000", MODULE.facility_identity_key(case))

    def test_cross_branch_code_is_rejected(self):
        case = published_case()
        case["facility_identity"]["facilityCode"] = "1001"
        with self.assertRaises(SystemExit):
            MODULE.validate(case)

    def test_facility_name_mismatch_is_rejected(self):
        case = published_case()
        case["facility_identity"]["facilityName"] = "교원예움 화성장례식장"
        with self.assertRaises(SystemExit):
            MODULE.validate(case)

    def test_source_url_is_part_of_grouping_key(self):
        first = published_case()
        second = copy.deepcopy(first)
        second["facility_identity"]["sourceUrl"] = "https://other.example.go.kr/facility/1000"
        self.assertNotEqual(MODULE.facility_identity_key(first), MODULE.facility_identity_key(second))


if __name__ == "__main__":
    unittest.main()
