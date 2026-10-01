# Application Progress Report

**Product:** MOA Valuation Package Automation  
**Date:** 1 October 2026  
**For:** Manager review  
**Compared with:** the requirements document (manual assembly and 401(k) review)

The requirements document is the manual process (Adobe combine, keep/remove, amounts, bookmarks, save, email, assembly log). This report shows how much of that process the application now does.

---

## Overall

| | |
|---|---|
| **Application progress** | **83%** |
| Requirement items scored | 24 |
| Done | 18 |
| Partial | 4 |
| Not done | 2 |

**How the percentage is calculated**

Each requirement item is scored Done = 100, Partial = 50, Not done = 0.  
(18 × 100) + (4 × 50) + (2 × 0) = 2,000.  
2,000 ÷ 24 = **83%**.

This is up from **75%** on 30 September. The two items that moved to Done are the cover date (`01` to `1`) and the prior-year HCE % / off-calendar 402(g) date rewrite.

Items the application was not asked to replace (claiming the plan on the Testing Log, converting non-PDFs, and sending the live email) stay in the 24 so the percentage is the full reviewer job, not only the PDF editing.

---

## By area

| Area | Progress | Meaning |
|---|---|---|
| Collect files and combine | 100% | Upload or folder path, merge, keyword order, named save |
| Keep / remove and amounts | 100% | Action Required, notices, letters, Excess Summary, recap, QNEC and refunds |
| Bookmarks and cover checks | 88% | Bookmarks, cover fields, and optional cover-day retype are done; “only Mutual of America” is still partly visual |
| Dates and HCE % on the pages | 100% | Optional. The reviewer checks “Retype dates and HCE %”. Preview can highlight those spots. The download stays clean. |
| Email and assembly log | 50% | Draft and log row are written; send and “date sent” are still manual |
| Steps outside the PDF | 17% | Inner test-page shuffle is partial. Testing Log and non-PDF conversion are not done. |

---

## Item scores

| # | Requirement | Status | Score |
|---|---|---|---|
| 1 | Open the Valuation Package (upload or folder path) | Done | 100 |
| 2 | Combine the PDFs into one package | Done | 100 |
| 3 | Put reports in the required order | Done | 100 |
| 4 | Split a multi-page cover into named pages for reorder | Done | 100 |
| 5 | Save `{Plan number}_{Beginning plan year}-Valuation.pdf` | Done | 100 |
| 6 | Off-calendar year uses the plan start year | Done | 100 |
| 7 | Keep or remove Action Required paragraphs | Done | 100 |
| 8 | CURRENT / PRIOR and after-12-month notices | Done | 100 |
| 9 | Fill QNEC and refund amounts; drop an unused ADP or ACP line | Done | 100 |
| 10 | ADP and ACP sample letters | Done | 100 |
| 11 | 402(g) letter, including the 15 April rule | Done | 100 |
| 12 | 415 failure information and 415 letter | Done | 100 |
| 13 | Excess Summary (including partially vested ADP/ACP) | Done | 100 |
| 14 | Year End Recap bullets | Done | 100 |
| 15 | Bookmarks, including 403(b) HCE and ADP Test / ACP Test | Done | 100 |
| 16 | Cover company, address, plan name, and plan year end | Done | 100 |
| 17 | Mutual of America is the only entity on the cover | Partial | 50 |
| 18 | Reorder every inner 410(b) / benefit-test page | Partial | 50 |
| 19 | Cover letter date shown as 1, not 01 | Done | 100 |
| 20 | Email the tester | Partial | 50 |
| 21 | Update the Val Assembly Log | Partial | 50 |
| 22 | Claim the plan on the Testing Log | Not done | 0 |
| 23 | Convert non-PDF files to PDF | Not done | 0 |
| 24 | Prior-year HCE % and off-calendar 402(g) dates | Done | 100 |

Partial items:

- **Only Mutual of America:** the stamp check is automated. Other company names are still a visual check.
- **Inner test pages:** whole reports are ordered. Detail pages inside 410(b) or Average Benefit Percentage are not split the way Adobe thumbnails would.
- **Email:** an Outlook draft is created with the required subject. The reviewer still sends it.
- **Assembly log:** Date, Time, plan, year, and file name are written when Process is clicked. Time is assembly time, not “date sent”.

Done, and turned on by the reviewer:

- **Cover date, prior-year HCE %, and off-calendar 402(g) dates.** These stay as printed unless the reviewer checks **Retype dates and HCE %** before Process. The box is off by default so a normal run does not move text on the page.
- A cover day changes only when the cover shows a zero-padded day (`January 01` becomes `January 1`).
- The HCE percentage is calculated only when the testing method is PRIOR and an NHCE % is on the package (under 2% → ×2; 2% to 7.99% → +2; 8% or more → ×1.25).
- 402(g) dates change only on an off-calendar plan, and only when those plan-year dates are printed on a 402(g) page. A calendar plan (year ending 31 December) is left as printed.
- **Highlight changes** on the preview is also optional and checked by default. Yellow marks show the rewritten words. Uncheck it for a plain preview. Download PDF never includes the marks.

Not done, and not planned as PDF automation:

- Entering the reviewer’s name on the Testing Log.
- Converting Word or Excel into PDF (those files are skipped with a warning).

---

## What is ready to show

- Upload PDFs or a Valuation Package folder path.
- Auto-order and a reorder list.
- Process: keep/remove, filled amounts, bookmarks.
- Optional retype of the cover day, the prior-year HCE %, and off-calendar 402(g) dates.
- Preview with optional highlights on the rewritten words, and a download of the named valuation PDF without those highlights.
- Outlook draft and an assembly-log row.

---

## What to say if asked “is it finished?”

The application covers the manual PDF assembly and review rules at about **95%** of those editing steps (18 of 20 PDF items are done; two are partial).  
Across the **whole** reviewer job in the requirements, progress is **83%** (was 75% before the date and HCE % option).

The remaining work is reviewer action outside the PDF: sending the email, the Testing Log, and converting non-PDF files. A package with no matching date or percentage will look unchanged even with the retype box checked; the notes on the result say what was left as printed.
