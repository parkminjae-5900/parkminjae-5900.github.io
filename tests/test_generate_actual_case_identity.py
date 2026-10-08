import copy
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "generate_actual_cases.py"
SPEC = importlib.util.spec_from_file_location("generate_actual_cases", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def seoseoul_case():
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
            "address": "서울 영등포구 선유로 101 (양평동1가)",
            "officialBranchName": "서서울",
            "sourceUrl": "https://www.kyowonyeum.co.kr/Site/Funeral?fnrCd=1000",
            "facilityCode": "1000",
        },
    }


def hwaseong_case():
    case = seoseoul_case()
    case["funeral_hall"] = "교원예움 화성장례식장"
    case["facility_identity"] = {
        "facilityName": "교원예움 화성장례식장",
        "address": "경기 화성시 만세구 마도면 쌍송북로 111 (두곡리)",
        "officialBranchName": "화성",
        "sourceUrl": "https://www.kyowonyeum.co.kr/Site/Funeral?fnrCd=1001",
        "facilityCode": "1001",
    }
    return case


class FacilityIdentityTests(unittest.TestCase):
    def test_exact_registry_identity_passes(self):
        case = seoseoul_case()
        MODULE.validate(case)
        self.assertEqual("kyowonyeum-seoseoul-1000", MODULE.facility_identity_key(case))

    def test_cross_branch_code_is_rejected(self):
        case = seoseoul_case()
        case["facility_identity"]["sourceUrl"] = "https://www.kyowonyeum.co.kr/Site/Funeral?fnrCd=1001"
        case["facility_identity"]["facilityCode"] = "1001"
        with self.assertRaises(SystemExit):
            MODULE.validate(case)

    def test_arbitrary_https_source_is_rejected(self):
        case = seoseoul_case()
        case["facility_identity"]["sourceUrl"] = "https://example.com/facility/1000"
        with self.assertRaises(SystemExit):
            MODULE.validate(case)

    def test_facility_name_mismatch_is_rejected(self):
        case = seoseoul_case()
        case["facility_identity"]["facilityName"] = "교원예움 화성장례식장"
        with self.assertRaises(SystemExit):
            MODULE.validate(case)

    def test_verified_branches_have_distinct_registry_ids(self):
        self.assertNotEqual(
            MODULE.facility_identity_key(seoseoul_case()),
            MODULE.facility_identity_key(hwaseong_case()),
        )


if __name__ == "__main__":
    unittest.main()
