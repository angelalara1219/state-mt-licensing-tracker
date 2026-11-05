# State Money Transmitter Licensing Tracker

A self-updating log of state money transmitter licensing changes: NMLS agency alerts, CSBS news, and which states have adopted the Money Transmission Modernization Act (MTMA).

## Why I built this

If you've handled licensing or compliance for an MSB, you know the problem. Every state runs its own playbook. Changes show up as an agency alert on NMLS, a CSBS press release, a bill that quietly takes effect July 1, or a renewal reminder buried in an email. Keeping track across 50 states plus DC is a lot of tabs.

This repo checks the main public sources once a week and keeps one running log, so the question "what changed for money transmitters this month?" has a one-page answer.

— Angela Lara, CAMS

## Latest updates

<!-- LATEST:START -->
| Date | Source | State | Update |
|---|---|---|---|
| 2026-11-02 | NMLS | — | [MSB Call Report Form Version 5: response to public comments now available](https://mortgage.nationwidelicensingsystem.org/knowledge/news/SitePages/NMLS-State-%26-Agency-News.aspx) |
| 2026-10-21 | CSBS | — | [State Supervisors Advise Licensees to Plan Ahead for NMLS Annual Renewal](https://www.csbs.org/newsroom/state-supervisors-advise-licensees-plan-ahead-nmls-annual-renewal) |
| 2026-10-19 | CSBS | — | [Treasury Should Preserve State-Federal Parity in Stablecoin Regulation](https://www.csbs.org/newsroom/treasury-should-preserve-state-federal-parity-stablecoin-regulation) |
| 2026-07-01 | CSBS | Virginia | [Virginia H.B. 1942 (full MTMA) takes effect](https://www.csbs.org/state-pending-enacted-mtma-legislation) |
| 2026-02-01 | CSBS | Alaska | [Alaska S.B. 86 / H.B. 99 (full MTMA) pending; passed Senate and carried over to 2026 (CSBS, Feb 2026)](https://www.csbs.org/state-pending-enacted-mtma-legislation) |
| 2026-02-01 | CSBS | Michigan | [Michigan H.B. 5544 (full MTMA) introduced (CSBS, Feb 2026)](https://www.csbs.org/state-pending-enacted-mtma-legislation) |
| 2026-02-01 | CSBS | Oklahoma | [Oklahoma H.B. 3521 (full MTMA) introduced (CSBS, Feb 2026)](https://www.csbs.org/state-pending-enacted-mtma-legislation) |
| 2026-01-01 | CSBS | Illinois | [Illinois S.B. 3412 (full MTMA) takes effect](https://www.csbs.org/state-pending-enacted-mtma-legislation) |
<!-- LATEST:END -->

Full log: [`data/updates.csv`](data/updates.csv)

## MTMA adoption at a glance

Based on CSBS's [State Pending & Enacted MTMA Legislation](https://www.csbs.org/state-pending-enacted-mtma-legislation) tracker (February 2026 version). "None listed" means CSBS shows no MTMA activity for that state, not that the state has no money transmitter law.

<!-- MTMA:START -->
| Status | Count | States |
|---|---|---|
| Full | 23 | Arizona, Colorado, Illinois, Indiana, Iowa, Kansas, Maine, Maryland, Massachusetts, Minnesota, Mississippi, Missouri, Nebraska, Nevada, New Hampshire, North Dakota, South Carolina, South Dakota, Tennessee, Texas, Vermont, Virginia, Wisconsin |
| Partial | 8 | Arkansas, California, Connecticut, Georgia, Hawaii, Rhode Island, Utah, West Virginia |
| Pending | 3 | Alaska, Michigan, Oklahoma |
| None listed | 17 | Alabama, Delaware, Florida, Idaho, Kentucky, Louisiana, Montana, New Jersey, New Mexico, New York, North Carolina, Ohio, Oregon, Pennsylvania, Washington, Wyoming, District of Columbia |
<!-- MTMA:END -->

State-by-state detail with bill numbers and effective dates: [`data/mtma_status.csv`](data/mtma_status.csv)

## What it watches

| Source | What it catches | How |
|---|---|---|
| [CSBS newsroom](https://www.csbs.org/newsroom) | Press releases on NMLS, money transmission, stablecoins, licensing | Reads new headlines and keeps the relevant ones |
| [CSBS MTMA legislation page](https://www.csbs.org/state-pending-enacted-mtma-legislation) | New MTMA bills, enactments, effective dates | Compares the page to last week's copy and logs new lines |
| [NMLS State & Agency News](https://mortgage.nationwidelicensingsystem.org/knowledge/news/SitePages/NMLS-State-%26-Agency-News.aspx) | State agency alerts: new requirements, deadlines, transitions to NMLS | Loads the page in a headless browser, compares it to last week's copy, and keeps only money transmitter-related lines |

The first time a page is checked, the watcher just saves a baseline in `data/snapshots/`. Changes show up from the second run on.

## What's in the log

| Column | What it is |
|---|---|
| `date_found` | When this tracker picked it up |
| `date_published` | When the source published it, if known |
| `source` | CSBS or NMLS |
| `category` | News, MTMA legislation, or Agency alert |
| `state` | State(s) mentioned, if any |
| `title` | Headline, or the changed line from the page |
| `link` | Where to read more |

## Run it yourself

```bash
pip install -r requirements.txt
playwright install chromium        # only needed for the NMLS page
python -m tracker.watch
python -m unittest discover -s tests
```

A GitHub Action ([`.github/workflows/update.yml`](.github/workflows/update.yml)) runs this every Monday and commits only when something changed. You can also run it by hand from the **Actions** tab.

## Notes

- Public sources only. Nothing here comes from any employer or non-public source.
- This is a monitoring aid, not legal advice. Always confirm requirements with the state regulator or the NMLS Resource Center.
- Page-change tracking is intentionally simple. If a source redesigns its site, expect one noisy week, then it settles down.

## Related

- [FinCEN Advisory & Guidance Tracker](https://github.com/angelalara1219/fincen-advisory-guidance-tracker): the federal side of the same idea, covering FinCEN alerts, advisories, and SAR key terms.

## License

MIT
