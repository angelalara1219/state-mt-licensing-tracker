import tempfile
import unittest
from pathlib import Path

from tracker import watch as w

FIX = Path(__file__).parent / "fixtures"
TODAY = "2026-11-04"


class NewsTests(unittest.TestCase):
    def test_keeps_relevant_csbs_items_with_dates(self):
        items = w.parse_csbs_news((FIX / "csbs_news.html").read_text(), TODAY)
        titles = [i.title for i in items]
        self.assertEqual(len(items), 2)
        self.assertIn("Treasury Should Preserve State-Federal Parity in Stablecoin Regulation", titles)
        self.assertNotIn("Community Bank Lending Trends in Q3", titles)
        renewal = items[0]
        self.assertEqual(renewal.date_published, "2026-10-21")
        self.assertTrue(renewal.link.startswith("https://www.csbs.org/newsroom/"))


class HelperTests(unittest.TestCase):
    def test_states_prefer_longest_name(self):
        self.assertEqual(w.states_in("West Virginia and Virginia both changed"), "West Virginia; Virginia")
        self.assertEqual(w.states_in("No state here"), "")

    def test_page_lines_drops_chrome_and_dupes(self):
        html = ("<html><body><nav>Menu Menu Menu Menu Menu Menu</nav><main>"
                "<p>Texas S.B. 895 enacted full MTMA effective September 1, 2023</p>"
                "<p>Texas S.B. 895 enacted full MTMA effective September 1, 2023</p>"
                "<p>short</p></main></body></html>")
        self.assertEqual(w.page_lines(html),
                         ["Texas S.B. 895 enacted full MTMA effective September 1, 2023"])


class DiffTests(unittest.TestCase):
    def test_first_run_is_baseline_then_logs_new_lines(self):
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d)
            base = ["Ohio H.B. 1 introduced full money transmission act",
                    "Internal Use Only - page footer text here"]
            first = w.diff_page("t", base, source="CSBS", category="MTMA legislation",
                                link="x", today=TODAY, snapshot_dir=snap)
            self.assertEqual(first, [])
            new = base + ["Michigan H.B. 5544 enacted full MTMA, effective July 1, 2027",
                          "Unrelated sentence about nothing in particular"]
            out = w.diff_page("t", new, source="CSBS", category="MTMA legislation",
                              link="x", today=TODAY, snapshot_dir=snap)
            self.assertEqual(len(out), 1)
            self.assertEqual(out[0].state, "Michigan")
            self.assertEqual(out[0].date_published, "2027-07-01")

    def test_agency_alerts_skip_mortgage_only_lines(self):
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d)
            w.diff_page("n", ["baseline line for the NMLS page"], source="NMLS",
                        category="Agency alert", link="x", today=TODAY, snapshot_dir=snap)
            out = w.diff_page("n", [
                "Florida OFR: new mortgage loan originator CE requirement",
                "Florida OFR: money transmitter licensees must update control persons",
            ], source="NMLS", category="Agency alert", link="x", today=TODAY, snapshot_dir=snap)
            self.assertEqual([u.title for u in out],
                             ["Florida OFR: money transmitter licensees must update control persons"])


class StorageTests(unittest.TestCase):
    def test_merge_dedupes_and_roundtrips(self):
        a = w.Update(TODAY, "2026-10-21", "CSBS", "News", "", "Title", "link")
        b = w.Update(TODAY, "", "NMLS", "Agency alert", "Texas", "Other", "link2")
        rows, added = w.merge([a], [a, b, b])
        self.assertEqual(added, [b])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "u.csv"
            w.save_updates(rows, p)
            self.assertEqual(len(w.load_updates(p)), 2)

    def test_readme_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "README.md"
            p.write_text("a\n<!-- LATEST:START -->\nx\n<!-- LATEST:END -->\n"
                         "<!-- MTMA:START -->\n<!-- MTMA:END -->\nz\n")
            w.update_readme(w.load_updates(), p)
            text = p.read_text()
            self.assertIn("| Full | 23 |", text)
            self.assertIn("Virginia", text)
            self.assertTrue(text.endswith("z\n"))


if __name__ == "__main__":
    unittest.main()
