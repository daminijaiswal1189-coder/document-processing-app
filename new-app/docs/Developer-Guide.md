# MOA Valuation Package — Developer Guide

Share this file with anyone joining the project. It describes the **current app in `new-app/`**, not the older POC.

## How to read this vs TEST23

| Document | Role |
|---|---|
| `TEST23.docx` | Business / SOP — what a reviewer does by hand |
| This Developer Guide | Technical implementation — what the app does today, and what it does **not** do |
| `docs/SRD.md` | Early requirements sketch; may lag the code |

They are **not identical**. TEST23 is the source of business rules. This guide maps those rules onto folders, YAML, and Python, and states coverage honestly:

- **Covered** — implemented and tested
- **Partial** — implemented with a known shortcut or missing nuance
- **Not implemented** — in TEST23 (or implied by it) but the app does not do it

When SOP and code disagree, **the code wins for what ships**; change the code (and tests) if the SOP is the intended behavior.

---

## Remaining 6 SOP decisions (hand this to a new developer)

These were the last TEST23 items that were easy to misread. Status as of this guide:

| # | Topic | Decision | Status |
|---|---|---|---|
| 1 | ADP-only bookmark | If the package has an ADP test report and not an ACP report, bookmark title is **ADP Test**. 403(b) stays **ACP Test**. Combined `adp-acp` filenames stay **ADP/ACP Tests**. | **Covered** (`bookmark_service.adp_acp_bookmark_title`) |
| 2 | ADP vs ACP sample letters | Separate rules **J_ADP** and **J_ACP**. Each letter is kept only if that test failed **and** returns are required. A combined letter that puts both extras on one page is not split line-by-line. | **Covered** for separate letters |
| 3 | Prior-test HCE percentage | The app **does not calculate** prior-year HCE ADP/ACP percentages. PRIOR method is a flag (`testing_method=PRIOR`) used for wording, notices, and recap Y2. Source reports / Excel supply any percentages. | **Not implemented** (intentional) |
| 4 | Off-calendar 402(g) dates | The **source 402(g) PDF is responsible** for calendar-year dates (e.g. PYE 06/30/2025 → 01/01/2024–12/31/2024). The app does not rewrite or validate those dates. Filename still uses cover plan year. | **Not implemented** (intentional) |
| 5 | Val Assembly Log date/time | **Date** and **Time** columns **are populated** when the user clicks Process. They are **assembly** timestamps (`%m/%d/%Y`, `%H:%M` local), not “date sent to the tester”. The app never records send time (Outlook is a `.eml` draft only). | **Covered** as assembly time |
| 6 | “Mutual of America only” | **Automated:** cover stamp / MOA wording in the upper right (`logo_check.py`, Checks tab). **Manual:** confirming no other TPA/vendor is named on the cover. The app does not fail the job for other entity names. | **Partial** by design |

---

## 1. What the app does

Reviewers assemble a Mutual of America **Valuation Package** from source PDFs (and optional Val Assembly Excel + Compliance Testing Summary). The app:

1. Accepts uploads **or** a folder path (Windows: `K:\Mutual of America\<plan>\Testing\...\Valuation Package`).
2. Merges PDFs in TEST23 combine order.
3. Extracts a **Plan Profile** (plan number, testing method, pass/fail flags, QNEC amounts, …).
4. Overlays Excel / summary numbers onto that profile.
5. Decides **keep / remove** for Action Required paragraphs, notices, sample letters, Excess Summary, and Year End Recap bullets.
6. Edits the PDF (drop blocks, fill QNEC/refund placeholders, restack leftover text, drop empty pages).
7. Adds bookmarks, scans for SSNs, saves `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf`.
8. Writes an Outlook `.eml` draft and appends a Val Assembly Log row.

There is **no database**. Jobs are in memory. The assembled PDF is on disk under `output/<job_id>/`.

---

## 2. Coverage vs TEST23 (read this first)

### 2.1 Covered

| TEST23 area | What the app does | Where |
|---|---|---|
| PDF assembly | Merge uploaded / folder PDFs into one file | `pdf_assembler.py` |
| Combine order | Sort by filename aliases in the full SOP list below | `sections.yaml`, `file_order.py` |
| Cover letter fields | Company, address, plan name, PYE, plan number | `pdf_extractor.py`, `test_cover_letter_fields.py` |
| Cover stamp | Upper-right MOA graphic / wording check | `logo_check.py` |
| Plan Profile | One object for all later rules | `models/plan_profile.py` |
| CURRENT vs PRIOR | `testing_method` from cover (preferred) or body | `field_patterns.py` |
| ADP / ACP fail | Flags + Action Required B/C + notice I + letters **J_ADP** / **J_ACP** | `rules.yaml` |
| After 12 months | AR D/E + notices D/E; CURRENT fills QNEC+refunds; PRIOR fills refunds only | `pdf_modifier.fill_qnec_placeholders` |
| 402(g) fail | Rule A paragraph + letter K; drop if no returns or after 4/15 note | `fail_402g`, `fail_402g_after_deadline` |
| 415 fail | Rule A + packet/letter L | `fail_415` |
| Top heavy | Keep F if `top_heavy` (percent ≥ 60) | `plan_profile_service.py` |
| Variance | Keep H if `variance_report` | Rule H |
| Contributions AR | Keep M if `contributions_required` | Rule M |
| QNEC amounts | Fill `$X,XXX,XXX.XX`; drop unused ADP or ACP QNEC line | `fill_qnec_placeholders` |
| Refund amounts | Fill deferral / match; drop the line if that amount is missing | same |
| Excess Summary | Keep for 402(g)/415, or ADP/ACP **and** partially vested | `keep_excess_summary` |
| Year End Recap | Keep/remove bullets Y1–Y8; always keep Y9 boiler | `paragraphs.yaml` recap_bullets |
| Keep/remove JSON | YAML conditions vs Plan Profile | `rules_engine.py` |
| PDF modification | Redact unused blocks, restack leftover text, drop empty pages | `pdf_modifier.py` |
| Bookmarks | Remaining detected sections; **ADP Test** / **ACP Test** / **ADP/ACP Tests**; 403(b) HCE vs HCE/Key | `bookmark_service.py` |
| SSN scan | `XXX-XX-XXXX` with extra checks | `ssn_scan.py` |
| Output name | `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf` | `save_service.py` |
| Copy to Testing folder | If source path ends with `Valuation Package` | `testing_folder_from_source` |
| Outlook draft | `.eml` subject `MOA \| Plan \| Name \| PYE …` | `outlook_service.py` |
| Val Assembly Log | Appends Date, Time, plan, PYE, filename, job id. Date/Time = assembly, not date sent | `assembly_log.py` |
| Compensation Limit file | Included in combine order | `sections.yaml` |
| No Comp Limit AR wording | App does **not** add or keep a special Action Required paragraph for compensation limit | intentional |
| Automated tests | pytest modules under `tests/` | see §15 |

### 2.2 Partial (SOP is richer than the code)

| TEST23 detail | What the app actually does | Gap |
|---|---|---|
| “Mutual of America is the only entity” | Stamp + wording check is automated | Other TPA names on the cover are **manual** |
| 403(b) HCE vs HCE/Key | Bookmark title is **HCE** for 403(b), **HCE/Key** otherwise | File still ordered as `HCE/Key`. No separate 403(b)-only recap wording |
| Cover letterhead date `1` not `01` | Date is extracted if present | Not validated or rewritten to a single-digit day |
| Recap Y9 “not administered by Mutual of America” | Always kept (no remove rule) | No TEST23 condition to drop it |
| Block restack after redaction | Leftover spans keep size/color; fonts mapped to tiro/helv/cour | Not true Word-style reflow. QNEC/recap pages flatten to a text box |

### 2.3 Not implemented / out of scope

| Item | Notes |
|---|---|
| Prior-year HCE ADP/ACP **percentage calculation** | Not computed. PRIOR is only a testing-method flag. Use source test reports / Excel. |
| 402(g) off-calendar date rewrite or validation | Source PDF must already show calendar-year 402(g) dates. |
| OCR / scanned photos | Source PDFs must have selectable text. |
| Creating missing source files | App only keep/removes what is in the upload. |
| Sending Outlook email / “date sent” | Writes a `.eml` draft only. Log time is assembly, not send. |
| Production Val Assembly Log extra columns | Current columns: Date, Time, Plan Number, Plan Name, PYE, Filename, Job ID. Confirm against the live K: template if a client needs more. |
| Old POC apps | Do not use `backend/`, `frontend/`, `electron/`, or root `pdf-process.py`. |

---

## 3. What not to touch

Product work lives only in **`new-app/`**.

Do **not** add features to `backend/`, `frontend/`, `electron/`, or root `pdf-process.py`. Those are the previous POC.

---

## 4. Stack and run

| Layer | Technology |
|---|---|
| UI | One file: `templates/index.html` (HTML + CSS + JS). No React, no build. |
| API | FastAPI (`main.py`, `api/jobs.py`) |
| PDF | PyMuPDF (`fitz`) |
| Excel | openpyxl / pandas |
| Rules | YAML (`config/rules.yaml`) evaluated in Python |
| Tests | pytest |

Default URL: **http://127.0.0.1:8002** (the app, not `/docs`, not `file://`).

**First time (Mac)**

```bash
cd new-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Every later run**

```bash
cd new-app
source .venv/bin/activate
python main.py
```

**Tests:** `python -m pytest -q` from `new-app/` with the venv on.

| Variable | Default | Purpose |
|---|---|---|
| `MOA_OUTPUT_DIR` | `new-app/output` | Assembled PDFs and `ValAssemblyLog.xlsx`. Production: `K:\Mutual of America`. |
| `MOA_HOST` | `127.0.0.1` | Bind address |
| `MOA_PORT` | `8002` | Port |

Restart `python main.py` after backend changes. Hard-refresh the browser after UI-only changes.

---

## 5. TEST23 SOP details the code implements

### 5.1 Full PDF combine order

Optional files are skipped when missing. Remaining files stay in this sequence (`config/sections.yaml`).

1. Cover Letter
2. Test Summary (aliases include Compliance Summary)
3. Compensation Limit Failure Summary
4. Combined Testing Report
5. Action Required
6. Failed Test Notice / Letter / Excess Summary / Excess Return Notice
7. Variance Report
8. Year End Recap (aliases include Important Information)
9. Compliance & Administrative Reports
10. Contribution Analysis
11. HCE/Key
12. Future HCE
13. ADP/ACP (aliases include ADP Test, ACP Test)
14. 402(g)
15. 410(b)
16. 401(a)(4)
17. Average Benefit Percentage Test
18. BRF (Benefits, Rights and Features)
19. 414(s)
20. 415
21. Top Heavy
22. Census

Auto-order uses **filename** aliases. If a real file is named oddly, add an alias or turn Auto-order off and use Up/Down in the UI.

### 5.2 401(k) vs 403(b)

| Topic | 401(k) | 403(b) | Code |
|---|---|---|---|
| Plan type | Extracted as `401k` when the cover/Excel says 401(k) | Extracted as `403b` when it says 403(b) | `plan_type` on Plan Profile |
| HCE bookmark | **HCE/Key** | **HCE** | `bookmark_service.py` |
| Test bookmark | **ADP Test**, **ACP Test**, or **ADP/ACP Tests** from filenames (`adp-test`, `acp-test`, `adp-acp`) or a standalone page heading. Cover lines like `ADP Test: Fail` do **not** count. | **ACP Test** | same |
| Recap | Same Y1–Y8 flags | Same rules; no extra 403(b)-only bullet engine | `rules.yaml` Y* |

`plan_type` is used for bookmarks. Keep/remove of ADP vs ACP **paragraphs** still uses `adp_failed` / `acp_failed`, not plan type.

### 5.3 Off-calendar 402(g)

TEST23: for an off-calendar plan, the **402(g) report** uses the **calendar year beginning**, not the plan-year dates.

Example: PYE `06/30/2025` → 402(g) period `01/01/2024`–`12/31/2024`.

**Covered**

- Output filename uses **beginning plan year from the cover** (`plan_year_start`), not dates printed on the 402(g) test.
- Calendar PYE `12/31/YYYY` with no start date → start is set to `01/01/YYYY`.

**Not implemented (source PDF owns this)**

- The app does **not** rewrite dates on the 402(g) pages.
- The app does **not** fail or warn if 402(g) dates still show the plan year instead of the calendar year.

If a client package has wrong 402(g) dates, that is a **source PDF / reviewer** issue.

### 5.4 Compensation Limit Failure Summary

TEST23: there is **no special wording** on the Action Required page for Compensation Limit Failure Summary.

**Covered as a no-op:** the file is ordered if present; there is **no** rule id and **no** Action Required heading for it. Do not add one unless SOP changes.

### 5.5 QNEC fill rules

Placeholders `$X,XXX,XXX.XX` on Excess Return / after-12 notices:

| Line | When it is written | When it is removed |
|---|---|---|
| Total “ADP/ACP test is $…” | `total_qnec` is set (sum of present ADP + ACP QNECs) | Left as placeholder if total is missing |
| `The ADP QNEC is …` | `adp_qnec` is not null | Line deleted if only ACP failed / no ADP QNEC |
| `The ACP QNEC is …` | `acp_qnec` is not null | Line deleted if only ADP failed / no ACP QNEC |
| Deferral refund | `deferral_refund` set | Line deleted if missing |
| Match refund | `match_refund` set | Line deleted if missing |

**If only ADP fails, do not show an ACP QNEC. If only ACP fails, do not show an ADP QNEC.** That is implemented: `fill_qnec_placeholders` deletes the unused line.

`total_qnec` = sum of whichever of `adp_qnec` / `acp_qnec` exist (`plan_profile_service.py`).

### 5.6 After 12 months — notices vs refunds

| Case | Keep | Fill on the notice |
|---|---|---|
| CURRENT + after 12 months + ADP/ACP fail | Rule **D** (AR + notice “Current method testing”) | QNEC total + ADP/ACP QNEC lines that exist + deferral/match refunds |
| PRIOR + after 12 months + ADP/ACP fail | Rule **E** (AR + notice “Prior method testing”) | Refunds only (no ADP/ACP QNEC lines on the PRIOR template) |
| CURRENT + ADP/ACP fail + **not** after 12 months | Rule **I** (notice “For current-method testing”) | QNECs (standard current-method notice) |
| PRIOR + returns + ADP/ACP, not after 12 | No notice I; PRIOR uses Action Required **B** | QNEC fill still runs if placeholders exist |

Rule I is removed when `after_12_months` is true so the within-12 CURRENT notice does not stay in the packet.

`extra` text on the page is required when `paragraphs.yaml` sets `extra` (so D/E notices do not collide with I).

### 5.7 Sample letters (explicit conditions)

| Id | Letter | Keep | Remove |
|---|---|---|---|
| J_ADP | SAMPLE/DRAFT with extra `Average Deferral Percentage (ADP)` | `returns_required` **and** `adp_failed` | ADP passed, no returns, or ADP letter not in the packet |
| J_ACP | SAMPLE/DRAFT with extra `Actual Contribution Percentage (ACP)` | `returns_required` **and** `acp_failed` | ACP passed, no returns, or ACP letter not in the packet |
| K | 402(g) SAMPLE/DRAFT | `fail_402g` **and** `returns_required` **and** `fail_402g_after_deadline` is not true | No 402(g) returns, 402(g) passed, **or** 402(g) was **not** processed before April 15 (note on the 402(g) report → `fail_402g_after_deadline`) |
| L | 415 failure info + 415 letter | `fail_415` | Plan did not fail 415 |

K extra text `SAMPLE/DRAFT` avoids wiping the 402(g) **test report**. L is one decision for both the 415 packet heading and the 415 letter.

If only ADP fails, the ACP sample letter is removed (and the reverse). Both extras must not live on the same page, or a remove of one id can redact the shared heading block.

### 5.8 Excess Summary

TEST23: Excess Summary is normally for failures that are **not ADP/ACP**, **unless** the ADP/ACP failure involves a **partially vested** participant.

Implemented in `finalize_profile`:

```text
keep_excess_summary =
    fail_402g
    OR fail_415
    OR (partially_vested AND (adp_failed OR acp_failed))
```

Rule **ES** keeps the `Excess Summary Report` heading when that flag is true.

### 5.9 Year End Recap bullets

Flags must come from **labeled cover lines and/or Excel**, never from the recap bullet template (the template would always match).

| Id | Keep the bullet when | Typical phrase (`paragraphs.yaml` `match`) |
|---|---|---|
| Y1 | No current HCE and no future HCE | did not have any Highly Compensated Employees |
| Y2 | PRIOR **and** (current or future HCE) | prior year data |
| Y3 | CURRENT **and** not Safe Harbor **and** (current or future HCE) | the actual amount the employee can defer |
| Y4 | Safe Harbor | Safe Harbor Plan |
| Y5 | HCE current **and** HCE future is false | the plan had Highly Compensated Employees for the plan year ending |
| Y6 | Catch-up is **not** disallowed (`catchup_disallowed` not true) | designed to allow participants who were age 50 |
| Y7 | Top heavy | Based on the top heavy testing results |
| Y8 | Per-payroll match | employer match contribution is calculated on a participant's compensation |
| Y9 | Always keep — no remove rule | not administered by Mutual of America |

Y1 vs Y2/Y3: if there are no HCEs, Y1 stays and PRIOR/CURRENT testing bullets are removed.

### 5.10 Bookmarks (TEST23 §O)

Bookmarks are created only for **detected remaining** sections (`profile.detected_sections`), using titles in `sections.yaml` plus 401(k)/403(b) overrides.

| Detected section | Bookmark title |
|---|---|
| Cover Letter | Cover Letter |
| Test Summary / Compliance Summary | Test Summary |
| Contribution Analysis | Contribution Analysis |
| HCE/Key | **HCE/Key** (401(k)) or **HCE** (403(b)) |
| Future HCE | Future HCE |
| ADP/ACP | **ADP Test** if only an ADP report is present; **ACP Test** if only ACP; **ADP/ACP Tests** if both or unclear; 403(b) always **ACP Test** |
| 402(g) | 402(g) Test |
| 410(b) | 410(b) Test |
| 401(a)(4) | 401(a)(4) Test |
| Average Benefit Percentage Test | Average Benefit Percentage Test |
| BRF | Benefits, Rights and Features Test |
| 414(s) | 414(s) Test |
| 415 | 415 Limit Test |
| Top Heavy | Top Heavy |
| Census | Census |

Removed Action Required / notice **pages** are not bookmarked as those sections if they are no longer detected. Empty pages after redaction are dropped.

Filenames such as `10_adp-test.pdf`, `12_acp-test.pdf`, and `10_adp-acp.pdf` drive the 401(k) title. A page whose entire heading line is `ADP Test` or `ACP Test` also counts. A cover line `ADP Test: Fail` does not.

### 5.11 Action Required keep/remove (A–H, M)

| Id | Heading (search text) | Keep when |
|---|---|---|
| A | IMMEDIATE ACTION REQUIRED - COMPLIANCE TEST FAILURE | Returns required **and** (402(g) or 415) **and** not 402(g) after 4/15. ADP/ACP-only failure does **not** keep A. |
| B | … ACP TEST FAILURE (PRIOR wording, refunds, no QNEC sentence) | PRIOR + returns + ADP/ACP fail + not reclassified |
| C | … ADP/ACP TEST FAILURE (CURRENT wording, includes QNEC) | CURRENT + returns + ADP/ACP fail |
| D | … CURRENT METHOD … AFTER 12-MONTHS | CURRENT + after 12 months + ADP/ACP fail |
| E | … PRIOR METHOD … AFTER 12-MONTHS | PRIOR + after 12 months + ADP/ACP fail |
| F | … TOP HEAVY **or** ATTENTION REQUIRED - TOP HEAVY DETERMINATION | `top_heavy` |
| G | NO IMMEDIATE ACTION IS REQUIRED AT THIS TIME | `has_action_required` is false |
| H | … VARIANCE | `variance_report` |
| M | … CONTRIBUTIONS | `contributions_required` |

`returns_already_processed` or `adp_reclassified` forces `returns_required = False`.

Variance AR body must **not** contain the words `Variance Report` or the flag can become true from the paragraph itself.

Duplicate ids **D** and **E** also apply to the after-12 **notices**. One keep/remove drives both the AR heading and the notice.

---

## 6. Folder structure

```
new-app/
  main.py                      FastAPI app; GET / serves the UI
  requirements.txt
  templates/index.html         Entire UI
  api/jobs.py                  POST/GET jobs, preview, download, email, log
  models/
    plan_profile.py            PlanProfile — every rule reads this
    job.py                     JobResult returned to the UI
    review.py                  RuleDecision, ReviewResult, ValidationItem
  config/
    settings.py                Paths, port, file limits
    rules.yaml                 Keep/remove conditions (rule ids)
    paragraphs.yaml            Headings / phrases searched in the PDF
    sections.yaml              Combine order + filename aliases + bookmark titles
    field_patterns.py          Regexes that fill Plan Profile from PDF text
    package_map.yaml           Human map of a real package (comments; not executed)
  services/
    orchestrator.py            Full pipeline (start here)
    folder_loader.py           Read a Valuation Package folder
    file_order.py              SOP sort from sections.yaml
    pdf_assembler.py           Merge PDFs
    pdf_extractor.py           Extract Plan Profile from merged PDF
    source_docs.py             Helpers for Excel / summary files
    source_profile.py          Overlay Excel + Compliance Summary onto profile
    plan_profile_service.py    Derived flags (dates, returns, QNEC total, Excess Summary)
    review_service.py          Checks tab
    logo_check.py              Cover stamp / “Mutual of America”
    rules_engine.py            YAML → keep / remove / skipped JSON
    pdf_modifier.py            Apply decisions to the PDF
    action_required.py         Action Required heading helpers
    bookmark_service.py        SOP bookmarks
    ssn_scan.py                XXX-XX-XXXX
    save_service.py            Filename + output folder
    outlook_service.py         .eml draft
    assembly_log.py            ValAssemblyLog.xlsx
  tests/                       pytest modules + fixtures/
  output/<job_id>/             Saved PDF + .eml
  sample-files/                Local trial PDFs
  docs/
    Developer-Guide.md         This file
    SRD.md                     Original requirements sketch (may lag)
```

---

## 7. Request flow

```
Browser  templates/index.html
    POST /api/jobs     files and/or source_path + auto_order
        api/jobs.py
            folder_loader.load_pdfs_from_folder()   if path pasted
            orchestrator.process_uploads()
        JSON JobResult → facts, pills, Keep/remove, Checks, Profile, Notes
    GET  /api/jobs/{id}/preview   PDF in iframe
    GET  /api/jobs/{id}/pdf       download
    GET  /api/jobs/{id}/email     Outlook .eml
    GET  /api/jobs/{id}/log       assembly log
```

Jobs are stored in `JOBS` (a dict in `api/jobs.py`). **Restarting the server clears JSON.** Preview/download still work if `output/<job_id>/*.pdf` exists.

The browser cannot read `K:\`. Only the Python process can. The user pastes a path; the server opens that folder.

---

## 8. Pipeline (`services/orchestrator.py`)

Read this file first.

| Step | Module | What it does |
|---|---|---|
| 1 | `_split_uploads` | PDFs vs `.xlsx` / `.xls` |
| 2 | `_split_summaries` | PDFs whose text contains “compliance testing summary of results” are overlays, not merged |
| 3 | `file_order.order_uploads` | TEST23 order from `sections.yaml` (unless Auto-order is off) |
| 4 | `pdf_assembler.merge_pdfs` | One `fitz` document |
| 5 | `pdf_extractor.extract_plan_profile` | Cover / body fields via `field_patterns.py` |
| 6 | `source_profile` | Overlay Excel + summary pass/fail / QNEC |
| 7 | `plan_profile_service.finalize_profile` | Derived fields |
| 8 | `review_service.validate` | Checks tab + logo |
| 9 | `rules_engine.evaluate` | Keep/remove JSON from `rules.yaml` |
| 10 | `pdf_modifier.apply_decisions` | Remove Action Required / notice / letter / Excess Summary blocks |
| 11 | `pdf_modifier.apply_recap_bullets` | Year End Recap Y1–Y8 |
| 12 | `pdf_modifier.fill_qnec_placeholders` | `$` QNEC and refund amounts |
| 13 | `bookmark_service.add_bookmarks` | Remaining sections |
| 14 | `ssn_scan.scan_ssns` | Pages with SSN pattern |
| 15 | `save_service.save_package` | `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf` |
| 16 | `outlook_service.write_draft` | Subject `MOA \| Plan \| Name \| PYE …` |
| 17 | `assembly_log.append_row` | `ValAssemblyLog.xlsx` |

**Rule:** keep/remove uses **Plan Profile only**. Do not re-parse the PDF inside `rules_engine.py`. If a decision is wrong, fix extraction or `finalize_profile`, then the YAML.

---

## 9. Plan Profile

`models/plan_profile.py` is the contract between extraction, rules, and the UI.

| Group | Fields |
|---|---|
| Identity | `plan_number`, `plan_name`, `company_name`, `company_address`, `plan_type` |
| Year | `plan_year_start`, `plan_year_end`, `beginning_plan_year` (filename) |
| Testing | `testing_method` (`CURRENT` \| `PRIOR`), `top_heavy`, `adp_failed`, `acp_failed`, `fail_402g`, `fail_415`, `after_12_months` |
| Returns | `returns_required`, `returns_already_processed`, `adp_reclassified`, `fail_402g_after_deadline` |
| Money | `adp_qnec`, `acp_qnec`, `total_qnec`, `deferral_refund`, `match_refund` |
| Recap | `hce_current`, `hce_future`, `safe_harbor`, `catchup_disallowed`, `per_payroll_match` |
| Other | `variance_report`, `contributions_required`, `partially_vested`, `keep_excess_summary`, `has_action_required` |

`apply_decisions` skips a heading unless `extra` (if set) is on that page.

A heading is not removed unless it is found in the PDF. “Remove” in the UI can still appear if the block was never in the source.

---

## 10. UI (`templates/index.html`)

One file. After Process:

- Upload can hide (`Show upload` / `Hide upload`).
- **Preview closed:** left = filename, actions, fact grid, source files; right = Keep/remove, Checks, Profile, Notes (that pane scrolls).
- **Preview open:** PDF on the left; summary stacked on the right (that column scrolls).

JS posts `FormData` to `/api/jobs`. Preview loads `/api/jobs/{id}/preview` in an iframe.

---

## 11. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | UI |
| GET | `/health` | Liveness |
| POST | `/api/jobs` | Process (`files`, `source_path`, `auto_order`) |
| GET | `/api/jobs/{id}` | JSON (memory only) |
| GET | `/api/jobs/{id}/preview` | Inline PDF |
| GET | `/api/jobs/{id}/pdf` | Attachment PDF |
| GET | `/api/jobs/{id}/email` | `.eml` |
| GET | `/api/jobs/{id}/log` | Assembly log Excel |

Limits: max **80** files, **50 MB** each. Non-PDF/Excel rejected. Names starting with `~$` ignored.

---

## 12. Output naming

`{PlanNumber}_{BeginningPlanYear}-Valuation.pdf`

Beginning plan year is the **start** year only:

- 01/01/2017–12/31/2017 → `2017`
- 10/01/2017–09/30/2018 → `2017`

If the source path ends with `Valuation Package`, also copy the PDF to the parent Testing folder.

---

## 13. Tests

```bash
python -m pytest -q
```

| File | Covers |
|---|---|
| `test_extract_and_assemble.py` | Merge + extract |
| `test_folder_and_order.py` | Folder load + SOP order |
| `test_cover_letter_fields.py` | Cover extraction |
| `test_logo_check.py` | Cover stamp |
| `test_profile_and_rules.py` | Profile + rules A–G |
| `test_action_required_compliance.py` | Rule A and related AR |
| `test_excel_summary_paragraphs.py` | Excel / summary overlay |
| `test_adp_acp_failure_notice.py` | Notice I / ADP-only QNEC line |
| `test_after_12_failure_notice.py` | Notices D / E; CURRENT QNEC+refunds; PRIOR refunds only |
| `test_sample_letters.py` | Letters J_ADP / J_ACP / K / L including K after 4/15 |
| `test_bookmarks.py` | ADP Test vs ACP Test vs ADP/ACP Tests titles |
| `test_remaining_sop.py` | H, M, ES, recap Y1–Y8, SSN, Outlook, log |
| `test_pdf_reflow.py` | Restack after redaction |
| `test_sample_fixtures.py` | Built-in fixture PDFs |

Rebuild tiny fixtures: `python tests/fixtures/build_samples.py`

When you change a rule, **add or update a test first**.

---

## 14. How to change things

### Wrong keep / remove

1. Profile + Checks on the result.
2. Wrong field → `field_patterns.py`, `source_profile.py`, or `plan_profile_service.py`.
3. Right field, wrong decision → `config/rules.yaml`.
4. Right decision, PDF still has the block → `paragraphs.yaml` heading / `extra`, then `pdf_modifier.py`.

### New keep / remove rule

1. Field on `PlanProfile` if needed.
2. Extract or overlay it.
3. Derive in `finalize_profile` if calculated.
4. Add `rules.yaml` + heading in `paragraphs.yaml`.
5. Wire `pdf_modifier.py` if the PDF must change.
6. Pytest, restart server, hard-refresh UI.

### Files in the wrong order

Add a filename alias in `sections.yaml`, or turn Auto-order off.

### UI only

`templates/index.html`. No rebuild.

---

## 15. Client-machine debugging

1. Use **http://127.0.0.1:8002** with `python main.py` running.
2. “Cannot reach the API” → server down, or HTML opened from disk.
3. Preview 404 after restart → Process again. Check `output/<job_id>/`.
4. Folder path does nothing → path must exist **on that PC** for the Python user; mapped `K:` must be available.
5. Output not on K: → set `MOA_OUTPUT_DIR` before starting Python.
6. Scanned image PDF → no extractable text; keep/remove cannot run.
7. Do not commit large assembled sample PDFs (GitHub HTTP 400 on ~44 MB packs).

---

## 16. Implementation notes (easy to get wrong)

- Recap bullets in fixtures use ASCII `- ` because `•` can become `?` in Helvetica.
- QNEC fill and recap rewrite flatten those pages to a text box; other leftover pages are restacked as spans.
- Header images stay; restacked text starts below them.
- SSN pattern is `XXX-XX-XXXX` with extra checks so EINs / plan numbers are less likely to match.
- Testing method prefers a labeled `Testing Method: CURRENT|PRIOR` line on the cover.
- PRIOR method does **not** compute HCE percentages; it only selects PRIOR wording / recap Y2.
- Val Assembly Log **Date** / **Time** = when Process ran, not when email was sent.

---

## 17. Suggested reading order

1. This file — especially **§2 Coverage** and **§5 SOP details**.
2. `TEST23.docx` for reviewer language.
3. `services/orchestrator.py`.
4. `models/plan_profile.py`.
5. `config/rules.yaml` + `config/paragraphs.yaml` + `config/sections.yaml`.
6. `api/jobs.py` + `templates/index.html` (JS at the bottom).
7. `services/pdf_modifier.py` when PDF output is wrong.
8. The pytest closest to the bug.

When in doubt: **fix Plan Profile first, rules second, PDF modifier last.**
