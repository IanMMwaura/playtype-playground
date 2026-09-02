from __future__ import annotations

import re
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
WWW = PROJECT_ROOT / "playtype_playground" / "www"


class PublicAssetTests(unittest.TestCase):
    def test_expected_public_files_exist(self) -> None:
        expected = {
            "404.html",
            "body-layout.js",
            "charts.js",
            "favicon.svg",
            "llms.txt",
            "privacy.html",
            "robots.txt",
            "sitemap.xml",
            "social-preview.png",
            "social-preview.svg",
            "terms.html",
        }
        self.assertTrue(expected.issubset({path.name for path in WWW.iterdir()}))

    def test_social_preview_uses_standard_link_card_dimensions(self) -> None:
        source = (WWW / "social-preview.png").read_bytes()
        self.assertEqual(source[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", source[16:24]), (1200, 630))

    def test_chart_binding_has_no_embedded_source_map_references(self) -> None:
        source = (WWW / "charts.js").read_text(encoding="utf-8")
        self.assertNotIn("sourceMappingURL", source)
        self.assertNotIn("sourceURL", source)
        self.assertNotIn("webpack", source.lower())

    def test_celtics_green_is_the_only_product_accent(self) -> None:
        styles = (PROJECT_ROOT / "playtype_playground" / "styles.css").read_text(
            encoding="utf-8"
        ).lower()
        favicon = (WWW / "favicon.svg").read_text(encoding="utf-8").lower()
        preview = (WWW / "social-preview.svg").read_text(encoding="utf-8").lower()

        self.assertIn("--accent: #007a33", styles)
        self.assertIn("#007a33", favicon)
        self.assertIn("#007a33", preview)
        self.assertIn('<circle cx="32" cy="32" r="19"', favicon)
        self.assertIn('<circle cx="32" cy="32" r="19"', preview)
        self.assertNotIn('m16 54v10h22', favicon)
        self.assertNotIn(">pp</text>", favicon + preview)
        self.assertNotIn("#c65d2e", styles + favicon + preview)

    def test_policy_pages_have_basic_metadata(self) -> None:
        for filename in ("privacy.html", "terms.html"):
            source = (WWW / filename).read_text(encoding="utf-8")
            self.assertIn('<html lang="en">', source)
            self.assertEqual(len(re.findall(r"<h1(?:\s|>)", source)), 1)
            self.assertIn('name="description"', source)
            self.assertIn('rel="canonical"', source)
            self.assertIn('property="og:image"', source)
            self.assertIn('rel="icon"', source)

    def test_robots_allows_crawlers(self) -> None:
        source = (WWW / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *\nAllow: /", source)
        self.assertIn("User-agent: GPTBot\nAllow: /", source)
        self.assertNotIn("Disallow: /", source)

    def test_sitemap_is_valid_xml(self) -> None:
        root = ET.parse(WWW / "sitemap.xml").getroot()
        self.assertTrue(root.tag.endswith("urlset"))
        self.assertEqual(len(list(root)), 3)


if __name__ == "__main__":
    unittest.main()
