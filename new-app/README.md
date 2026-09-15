# MOA Valuation Package Automation

Greenfield app in `new-app/`. It does **not** use the existing POC backend or `pdf-process.py`.

Phase 1: upload PDFs **or** a Valuation Package folder path → assemble in TEST23 SOP order → extract a Plan Profile → preview keep/remove rules → add bookmarks → save `{PlanNumber}_{BeginningPlanYear}-Valuation.pdf`.

Page removal, bookmarks, SSN scan, and Outlook are not applied yet.

## Run

```bash
cd new-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

UI: http://127.0.0.1:8002  
API docs: http://127.0.0.1:8002/docs

Optional: set `MOA_OUTPUT_DIR` to a Windows path such as `K:\Mutual of America` in production.

## Layout

```
new-app/
  main.py                 FastAPI entry
  api/jobs.py             POST /api/jobs, download PDF
  services/orchestrator.py
  services/pdf_assembler.py
  services/pdf_extractor.py
  services/plan_profile_service.py
  services/rules_engine.py      JSON keep/remove only
  services/review_service.py    cover-field checks
  services/save_service.py
  services/pdf_modifier.py      Phase 4 stub
  services/bookmark_service.py  Phase 4 stub
  models/plan_profile.py
  config/field_patterns.py      extraction regexes
  config/sections.yaml
  config/rules.yaml             rules A–G
  templates/index.html
  output/                       saved packages
```

## Sample PDFs

Upload these from `tests/fixtures/` at http://127.0.0.1:8002

| File | What it tests |
|------|----------------|
| `01_pass_no_action.pdf` | All sections; tests pass; Rule G keep |
| `02_current_fail_qnec.pdf` | CURRENT fail, QNEC, top heavy, after 12 months |
| `03_prior_fail_offcalendar.pdf` | PRIOR fail; plan year 10/01/2017–09/30/2018 → `333333_2017-Valuation.pdf` |
| `assemble-current-fail/*.pdf` | Same as #2 split into 16 files — select all, keep 01–16 order |

Regenerate:

```bash
python tests/fixtures/build_samples.py
```

## Tests

```bash
cd new-app
python -m pytest -q
```

## Next (do not skip)

1. Tune `config/field_patterns.py` against real MOA packages when they arrive.
2. Phase 2: SSN scan and package-order validation.
3. Phase 4: apply rule decisions to the PDF and generate bookmarks.
