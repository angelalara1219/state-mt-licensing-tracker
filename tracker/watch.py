"""Weekly watcher for state money transmitter licensing changes.

Sources (all public):

  * CSBS newsroom - press releases about NMLS, money transmission,
    stablecoins, and other state licensing news.
  * CSBS "State Pending & Enacted MTMA Legislation" - which states have
    adopted the Money Transmission Modernization Act.
  * NMLS State & Agency News - state agency alerts posted on the NMLS
    Resource Center. That page is built with JavaScript, so it is read
    with a headless browser (Playwright) when one is available.

For the two "page" sources the watcher keeps a plain-text snapshot in
data/snapshots/ and logs any new lines that look relevant. The first run
just records a baseline.
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
UPDATES_CSV = DATA / "updates.csv"
MTMA_CSV = DATA / "mtma_status.csv"
README = ROOT / "README.md"

CSBS_NEWS_URL = "https://www.csbs.org/newsroom"
CSBS_MTMA_URL = "https://www.csbs.org/state-pending-enacted-mtma-legislation"
NMLS_NEWS_URL = ("https://mortgage.nationwidelicensingsystem.org/knowledge/news/"
                 "SitePages/NMLS-State-%26-Agency-News.aspx")

HEADERS = {"User-Agent": "nmls-mt-tracker/1.0 (public-data research script)"}

# What counts as relevant to money transmitters / MSBs.
RELEVANT = re.compile(
    r"money transmi|money services|\bMSBs?\b|virtual currency|digital asset|"
    r"crypto|kiosk|stablecoin|\bMTMA\b|currency exchange|check cash|"
    r"payment instrument|stored value|annual renewal|renewal period",
    re.IGNORECASE,
)
# CSBS press releases about NMLS itself are worth keeping too.
CSBS_EXTRA = re.compile(r"\bNMLS\b|licens", re.IGNORECASE)

STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Puerto Rico", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
]
# Longest names first so "West Virginia" wins over "Virginia".
STATE_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, STATES), key=len, reverse=True)) + r")\b")

DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December) \d{1,2}, \d{4}\b")


@dataclass
class Update:
    date_found: str
    date_published: str
    source: str
    category: str
    state: str
    title: str
    link: str


COLUMNS = [f.name for f in fields(Update)]


# ------------------------------------------------------------------ helpers

def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_rendered(url: str) -> str:
    """Render a JavaScript page with Playwright. Raises if unavailable."""
    from playwright.sync_api import sync_playwright  # optional dependency

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(url, wait_until="networkidle", timeout=60_000)
        html = page.content()
        browser.close()
    return html


def iso(text: str) -> str:
    try:
        return datetime.strptime(text, "%B %d, %Y").date().isoformat()
    except (TypeError, ValueError):
        return ""


def states_in(text: str) -> str:
    found = []
    for name in STATE_RE.findall(text):
        if name not in found:
            found.append(name)
    return "; ".join(found)


def page_lines(html: str) -> list[str]:
    """Visible text of a page, one meaningful line per entry, in order."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer"]):
        tag.decompose()
    root = soup.find("main") or soup.body or soup
    seen, lines = set(), []
    for raw in root.get_text("\n").splitlines():
        line = " ".join(raw.split())
        if len(line) < 20 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines


# ------------------------------------------------------------------ sources

def parse_csbs_news(html: str, today: str) -> list[Update]:
    soup = BeautifulSoup(html, "html.parser")
    updates, seen = [], set()
    for heading in soup.find_all(["h2", "h3", "h4"]):
        link = heading.find("a", href=True)
        if not link or "/newsroom/" not in link["href"]:
            continue
        url = urljoin(CSBS_NEWS_URL, link["href"])
        title = " ".join(link.get_text().split())
        if url in seen or not title:
            continue
        seen.add(url)
        if not (RELEVANT.search(title) or CSBS_EXTRA.search(title)):
            continue
        # The date is the first "Month D, YYYY" after the heading.
        published = ""
        for sib in heading.find_all_next(string=DATE_RE, limit=1):
            published = iso(DATE_RE.search(sib).group(0))
        updates.append(Update(today, published, "CSBS", "News", states_in(title), title, url))
    return updates


def diff_page(name: str, lines: list[str], *, source: str, category: str,
              link: str, today: str, snapshot_dir: Path = SNAPSHOTS) -> list[Update]:
    """Compare against the saved snapshot; log new relevant lines."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"{name}.txt"
    first_run = not path.exists()
    old = set() if first_run else set(path.read_text(encoding="utf-8").splitlines())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if first_run:
        return []
    updates = []
    for line in lines:
        if line in old or not RELEVANT.search(line) and not STATE_RE.search(line):
            continue
        if category == "Agency alert" and not RELEVANT.search(line):
            continue  # NMLS also posts mortgage-only alerts; skip those
        found = DATE_RE.search(line)
        updates.append(Update(today, iso(found.group(0)) if found else "", source,
                              category, states_in(line), line[:300], link))
    return updates


# ------------------------------------------------------------------ storage

def load_updates(path: Path = UPDATES_CSV) -> list[Update]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [Update(**{c: r.get(c, "") for c in COLUMNS}) for r in csv.DictReader(f)]


def save_updates(rows: list[Update], path: Path = UPDATES_CSV) -> None:
    rows = sorted(rows, key=lambda u: (u.date_published or u.date_found, u.date_found), reverse=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def merge(existing: list[Update], new: list[Update]) -> tuple[list[Update], list[Update]]:
    keys = {(u.source, u.title, u.link) for u in existing}
    added = [u for u in new if (u.source, u.title, u.link) not in keys]
    # de-dupe within the new batch too
    uniq, seen = [], set()
    for u in added:
        k = (u.source, u.title, u.link)
        if k not in seen:
            seen.add(k)
            uniq.append(u)
    return existing + uniq, uniq


# ------------------------------------------------------------------ README

def _replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    if start not in text or end not in text:
        return text
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}\n{body}\n{end}{tail}"


def latest_table(rows: list[Update], n: int = 10) -> str:
    rows = sorted(rows, key=lambda u: (u.date_published or u.date_found), reverse=True)[:n]
    out = ["| Date | Source | State | Update |", "|---|---|---|---|"]
    for u in rows:
        title = u.title.replace("|", "/")
        title = f"[{title}]({u.link})" if u.link else title
        out.append(f"| {u.date_published or u.date_found} | {u.source} | {u.state or '—'} | {title} |")
    return "\n".join(out)


def mtma_summary(path: Path = MTMA_CSV) -> str:
    if not path.exists():
        return ""
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    groups: dict[str, list[str]] = {}
    for r in rows:
        groups.setdefault(r["status"], []).append(r["state"])
    out = ["| Status | Count | States |", "|---|---|---|"]
    for status in ("Full", "Partial", "Pending", "None listed"):
        states = groups.get(status, [])
        out.append(f"| {status} | {len(states)} | {', '.join(states)} |")
    return "\n".join(out)


def update_readme(rows: list[Update], path: Path = README) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = _replace_block(text, "LATEST", latest_table(rows))
    text = _replace_block(text, "MTMA", mtma_summary())
    path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------ main

def run() -> int:
    today = date.today().isoformat()
    found: list[Update] = []
    ok = 0

    try:
        found += parse_csbs_news(fetch(CSBS_NEWS_URL), today)
        ok += 1
    except Exception as exc:  # keep going if one source is down
        print(f"! CSBS newsroom: {exc}", file=sys.stderr)

    try:
        found += diff_page("csbs_mtma", page_lines(fetch(CSBS_MTMA_URL)),
                           source="CSBS", category="MTMA legislation",
                           link=CSBS_MTMA_URL, today=today)
        ok += 1
    except Exception as exc:
        print(f"! CSBS MTMA page: {exc}", file=sys.stderr)

    try:
        found += diff_page("nmls_agency_news", page_lines(fetch_rendered(NMLS_NEWS_URL)),
                           source="NMLS", category="Agency alert",
                           link=NMLS_NEWS_URL, today=today)
        ok += 1
    except Exception as exc:
        print(f"! NMLS agency news: {exc}", file=sys.stderr)

    if ok == 0:
        print("Every source failed; nothing was changed.", file=sys.stderr)
        return 1

    rows, added = merge(load_updates(), found)
    save_updates(rows)
    update_readme(rows)
    print(f"{ok}/3 sources checked. New updates: {len(added)}")
    for u in added:
        print(f"  + [{u.source}] {u.state or '-'}: {u.title[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
