import importlib.util
import pathlib
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "submit_indexnow.py"
SPEC = importlib.util.spec_from_file_location("submit_indexnow", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class IndexNowTests(unittest.TestCase):
    def test_path_mapping(self):
        self.assertEqual("https://www.dahamsangjo.co.kr/", MODULE.path_to_url("index.html"))
        self.assertEqual(
            "https://www.dahamsangjo.co.kr/area-incheon-jemulpo-funeral.html",
            MODULE.path_to_url("area-incheon-jemulpo-funeral.html"),
        )
        self.assertIsNone(MODULE.path_to_url("../outside.html"))
        self.assertIsNone(MODULE.path_to_url("sitemap.xml"))

    def test_changed_alias_and_current_pages_are_deduplicated(self):
        seed = "\n".join(
            [
                "https://www.dahamsangjo.co.kr/area-incheon-junggu-funeral.html",
                "https://www.dahamsangjo.co.kr/area-incheon-jemulpo-funeral.html",
                "https://www.dahamsangjo.co.kr/area-incheon-jemulpo-funeral.html",
            ]
        )
        with mock.patch("pathlib.Path.read_text", return_value=seed):
            urls = MODULE.collect_urls(
                [
                    "M\tarea-incheon-junggu-funeral.html",
                    "A\t.github/indexnow-seed.txt",
                ]
            )
        self.assertEqual(
            [
                "https://www.dahamsangjo.co.kr/area-incheon-jemulpo-funeral.html",
                "https://www.dahamsangjo.co.kr/area-incheon-junggu-funeral.html",
            ],
            urls,
        )

    def test_external_seed_url_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.validate_url("https://example.com/page.html")

    def test_payload_uses_public_root_key(self):
        with mock.patch("pathlib.Path.read_text", return_value=MODULE.KEY):
            payload = MODULE.build_payload(["https://www.dahamsangjo.co.kr/"])
        self.assertEqual("www.dahamsangjo.co.kr", payload["host"])
        self.assertEqual(
            f"https://www.dahamsangjo.co.kr/{MODULE.KEY}.txt",
            payload["keyLocation"],
        )


if __name__ == "__main__":
    unittest.main()
