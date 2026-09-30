# Solution Document — Automating the Valuation Package Process

**Product:** MOA Valuation Package Automation  
**Audience:** delivery, architecture review, and client handover  
**Requirements:** the requirements document (MOA Val Package Assembly and 401(k) Editing/Review)

The requirements document describes the **manual** process a reviewer follows in Adobe and Excel. This application automates that process on the reviewer’s computer. This document maps each manual step to what the application does, and states what the reviewer still does by hand.

---

## 1. The problem (manual process)

A reviewer assembles a Mutual of America Valuation Package for a plan year by hand:

1. Claim the plan on the Val Assembly Log so others know it is being worked.
2. Open the plan folder on `K:\Mutual of America\<Plan Number>\Testing\…\Valuation Package`.
3. Confirm every source file is a PDF. If it is not, convert it or send it back to the tester.
4. In Adobe, choose Combine Files, add every PDF, drag files into the required order, and remove pages that should not ship.
5. Combine into one PDF. Move individual pages with thumbnails if needed.
6. Save as `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf` in the Testing folder. The year is the **start** of the plan year (for example 10/01/2017–09/30/2018 is 2017).
7. Review the package against the requirements:
   - Cover must show the Mutual of America stamp, and company, address, plan name, and plan year end must match the plan.
   - Keep or remove Action Required paragraphs (compliance failure, PRIOR vs CURRENT ADP/ACP, after 12 months, variance, top heavy at 60% or more, “no immediate action”).
   - Keep or remove ADP/ACP failure notices and type the QNEC and refund amounts from the correction page. If only ADP or only ACP failed, drop the unused QNEC line.
   - Remove 415 failure information and the 415 sample letter if the plan did not fail 415.
   - Remove ADP/ACP and 402(g) sample letters when returns are not required (including 402(g) not processed by 15 April).
   - Keep Excess Summary only for non-ADP/ACP failures, or an ADP/ACP failure for a partially vested participant.
   - Keep or remove Year End Recap / Important Information bullets from the testing method, HCE, Safe Harbor, top heavy, and match rules.
   - Always include Compliance and Administrative Reports.
   - Add bookmarks with the required titles (HCE vs HCE/Key, ADP Test vs ACP Test vs ADP/ACP Tests).
8. Email the tester. The subject must start with MOA, then plan number, plan name, and plan year end.
9. Update the Val Assembly Log with the date sent and the time to assemble.

That work is slow, easy to order wrong, and easy to leave the wrong paragraph in the package.

---

## 2. The solution

The application runs on the reviewer’s PC. The reviewer uploads the Valuation Package PDFs (or pastes the folder path). The application combines them, applies the keep/remove rules, fills amounts, adds bookmarks, and writes the named PDF, an email draft, and a log row.

The reviewer then checks the result, sends the email, and finishes any step the application does not own (listed in §4).

```
Manual today                         Application
────────────────────────             ────────────────────────────────
Adobe Combine + drag order    →      Upload or folder path, auto-order
Delete unneeded pages         →      Keep/remove rules edit the PDF
Type QNEC and refund amounts  →      Amounts filled from the profile
Add bookmarks by hand         →      Bookmarks written from remaining sections
Save ######_YYYY-Valuation    →      Same filename, beginning plan year
Write the email               →      Outlook draft (.eml), reviewer sends it
Update the assembly log       →      Date, time, plan, and filename appended
```

---

## 3. Manual step → what the application does

| Manual step in the requirements | What the application does |
|---|---|
| Open the Valuation Package folder and add the PDFs | Upload files, or paste the folder path. The application reads PDFs and Excel from that path. |
| Put reports in the required order | Auto-order matches filenames to section keywords (for example Valuation Pkg, ResultSumm, HCEKey, ADP, 402, Census). The reviewer can still move rows Up/Down or Remove. |
| A multi-page cover / package that holds several front sections | A multi-page cover is split into separate rows named Cover Letter, Action required page 1–3, the excess notices, the failure letters, Year End Recap, and Compliance Report 1–3, so those pages can be reordered. |
| Remove files or pages that do not belong | Rules decide keep or remove for Action Required, notices, sample letters, Excess Summary, and recap bullets. Removed blocks are taken out of the PDF. |
| Cover: Mutual of America stamp; company, address, plan name, plan year end | Extracted into a Plan Profile and shown on the Checks tab, including the upper-right stamp. |
| Action Required paragraphs (failure, PRIOR, CURRENT, after 12 months, variance, top heavy, no action) | Kept or removed from the Plan Profile (testing method, returns, ADP/ACP, 402(g), 415, top heavy ≥ 60%, variance, contributions). |
| Compensation Limit Failure Summary has no special Action Required wording | The file can be included in order. The application does not add a special Action Required paragraph for it. |
| CURRENT ADP/ACP notice: type total QNEC, ADP QNEC, ACP QNEC | Placeholders are filled. If only ADP or only ACP has a QNEC, the other line is removed. |
| After 12 months CURRENT: QNEC plus deferral and match refunds | Filled when those amounts are present. A missing amount drops that line. |
| After 12 months PRIOR: refunds only, no QNEC sentence | Refund lines are filled. PRIOR does not keep the within-12 CURRENT notice. |
| 415 failure information and 415 letter | Removed when the plan did not fail 415. |
| ADP and ACP sample letters | Each letter stays only if that test failed and returns are required. |
| 402(g) sample letter | Removed if there are no 402(g) returns, or the report notes the failure was not processed by 15 April. |
| Excess Summary | Kept for 402(g) or 415, or for ADP/ACP when a participant is partially vested. |
| Year End Recap bullets | Kept or removed from HCE, PRIOR/CURRENT, Safe Harbor, top heavy, catch-up, and per-payroll match. |
| Compliance reports | Included when the file is in the package. The application does not drop them by rule. |
| Bookmarks | Created for sections that remain, with the required titles, including HCE for 403(b) and ADP Test / ACP Test / ADP/ACP Tests. |
| Save `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf` | Same name. Off-calendar plans use the beginning year from the cover. If the source path is a Valuation Package folder, a copy is also written to the Testing folder when that path can be written. |
| Email the tester | An Outlook draft is written. Subject starts with MOA, then plan number, plan name, and plan year end. |
| Update the Val Assembly Log | A row is appended with Date, Time, plan number, plan name, plan year end, filename, and job id. Date and Time are when the package was assembled. |

---

## 4. What the reviewer still does

These steps stay manual because they are outside the PDF package or they depend on a source report the application does not rewrite.

| Manual step | Why it stays manual |
|---|---|
| Enter your name on the Testing Log to claim the plan | The application does not open that testing workbook. |
| Convert a non-PDF to PDF, or send it back to the tester | Non-PDF files are skipped with a warning. |
| Confirm no other company name appears besides Mutual of America | The stamp check is automated. Other names on the cover are still a visual check. |
| Change the cover letter date from 01 to 1 | The date is read if it is in the PDF. It is not rewritten. |
| Calculate the prior-year HCE percentage from the NHCE table | The application uses PRIOR vs CURRENT for wording. The percentage stays on the source test or Excel. |
| Fix 402(g) dates on an off-calendar plan to the calendar year | The source 402(g) PDF must already show those dates. The saved filename still uses the cover plan year. |
| Send the email and record “date sent” | The application prepares the draft. The reviewer sends it. Log time is assembly time, not send time. |
| Reorder every inner page of 410(b) or Average Benefit Percentage the way Adobe thumbnails would | Whole reports are ordered. Inner detail pages are not split unless they are part of the cover split above. |

---

## 5. How the application is built

The reviewer uses a browser on the same PC. There is no separate server and no database.

```
Browser (upload, order, preview, keep/remove)
        │
        ▼
Application API  (http://127.0.0.1:8002)
        │
        ▼
Pipeline: order → merge PDFs → read plan facts → apply rules
          → edit PDF → bookmarks → save PDF, email draft, log
        │
        ▼
Files on disk (and optional K: Testing folder)
```

**Plan Profile** is the single set of facts every rule uses: plan number, names, dates, 401(k) vs 403(b), CURRENT vs PRIOR, pass/fail, QNEC and refund amounts, top heavy, and whether returns are required. Rules do not re-read the PDF to decide keep or remove.

Rules and section order live in configuration (`rules`, paragraph headings, section order and filename keywords), so requirement wording can be adjusted without rewriting the pipeline.

**Outputs**

- `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf`
- Outlook `.eml` draft beside that PDF
- `ValAssemblyLog.xlsx` under the output folder (`MOA_OUTPUT_DIR`, or the application output folder)

**On a client PC:** Python is already installed. Run the application, open http://127.0.0.1:8002. The first run installs PDF and Excel libraries from the internet once. To copy the application without a zip, use the text installer `install_moa.py`, then `run.bat`.

---

## 6. Processing sequence

1. Reviewer selects PDFs and Excel, or a Valuation Package folder.
2. The application lists files in requirement order and splits a multi-page cover into named pages.
3. Reviewer confirms order (or moves rows) and clicks Process.
4. PDFs are merged. Excel and a compliance testing summary, if present, fill the Plan Profile. Summary overlays are not merged into the package as extra reports.
5. Keep/remove is applied, amounts are filled, empty pages are dropped, bookmarks are added, and SSNs are flagged if found.
6. The named PDF, email draft, and log row are written. The reviewer previews, downloads, and sends the draft.

---

## 7. What to say in the review

The requirements document is the manual Adobe and Excel procedure. The application automates combine, order, keep/remove, amount fill, bookmarks, the valuation filename, the email draft, and the assembly log.

The reviewer still claims the plan on the Testing Log, sends the email, and owns source-report items the PDFs already contain (prior-year HCE percent and off-calendar 402(g) dates).
