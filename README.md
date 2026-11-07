# People, in Balance

An independent, AI-assisted People Data & Operations portfolio project by Margarita Bermejo Cano. **Official public data and clearly labelled fictional demonstrations; not affiliated with Waystone.**

**[Explore the live atlas](https://mberca.github.io/people-operations-atlas/)** · [Download the complete portfolio package](https://github.com/mberca/people-operations-atlas/releases/latest/download/People_in_Balance_Portfolio.zip)

Open `index.html` in a browser. The self-contained atlas combines a morphing workforce constellation, an interactive seven-system connection map, official Irish sector context, a transparent reporting-population journey, a payroll discrepancy bridge, an investigation desk, absence heatmaps, working-time screens, visa/case timelines and a 29-requirement evidence map. Keep the accompanying folders if you want the download links to work. For a complete review package, extract `People_in_Balance_Portfolio.zip` and open its `index.html`; do not publish or email any real employee data.

## Evidence layers

**Public:** CSO Ireland EHQ03, *Average Earnings, Hours Worked, Employment and Labour Costs*, CC BY 4.0. The pinned official snapshot contains 130,536 cells; the analysis selects 3,150 all-employee cells across five unadjusted measures and 30 quarters, 2019Q1–2026Q2. Source hash, URLs, retrieval date, units and coverage are in `data\public\provenance.json`. Indexing and changes are transformations; public cells are never silently imputed. Overlapping published sector aggregates are never summed.

**Fictional:** 360 wholly fictional employee keys and seven differently structured HR/payroll/approval/absence/time/visa/case feeds, seed 731, as-of 2026-10-31. No real employee, customer, health, nationality, passport or case narrative data. Seeded mechanisms demonstrate controls; they are not discoveries about an employer.

**Not experience claims:** live BambooHR SME capability, actual Tier 2/ER judgement, end-to-end immigration administration, hands-on Power BI authoring and years of experience are not established here. The evidence map distinguishes demonstrated features, simulations, proposed design and unsupported experience.

## Deliverables

| File | What to inspect |
|---|---|
| `index.html` | Offline interactive visual atlas; desktop/mobile; light/dark; reduced motion; keyboard inspection; accessible tables; no trackers or runtime requests |
| `analysis.ipynb` | Executed in-depth notebook: source audit, missingness, descriptive trends/distributions, change correlations/sensitivity, reconciliation, exceptions and limitations |
| `outputs\People_Operations_Control_Workbook.xlsx` | Editable formulas, XLOOKUP, INDEX/MATCH, exact VLOOKUP, nested logic, validation, absence exposure, time/visa/case controls and **two genuine native Excel PivotTables** |
| `outputs\analysis_summary.json` | Source provenance, baseline operational metrics and requirement-level counts |
| `outputs\tables\` | Reproducible cleaned/analysed tables; all operational rows are fictional |
| `outputs\plots\` | Labelled PNG/SVG analysis figures |
| `outputs\*_validation.json` | Native formula/pivot validation, Python/Excel parity and scenario tests, browser checks |
| `outputs\screenshots\` | Verified desktop/mobile visual captures |

## Main fictional control results

364 raw HR rows → 360 keys → 355 valid masters → 344 active people / 324 FTE → 340 payroll-comparable records → 337 reconciled. Quarantined conflicts, invalid fields, future hires, leavers and unknown payments stay visible rather than being silently included or filled.

The same comparable base yields a **EUR 1,847.33 signed discrepancy** versus **EUR 2,652.67 absolute discrepancy**. Approved salary/variable-pay changes correctly reconcile; unsupported movement, allowance mismatch and stale salary are separated. Absence uses 296 unique scheduled lost dates after removing one overlap; the FTE-weighted lost-hour rate is 0.975%. Seven complete time records exceed the baseline screen and one incomplete record remains unknown. Visa/case flags are operational service-level demonstrations, not legal findings.

## Rebuild and validate on Windows

Dependencies are in `requirements.txt`. An existing local `.venv` uses the installed analysis packages plus notebook dependencies. A new environment can be prepared with:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run from this project directory:

```powershell
# Verify or acquire the official snapshot.
.\.venv\Scripts\python.exe scripts\sources.py

# Rebuild data, Excel, figures, notebook and offline HTML; execute the notebook.
.\.venv\Scripts\python.exe scripts\build.py --excel --execute

# Control fixtures, independently checked Excel results and native Excel scenarios.
.\.venv\Scripts\python.exe tests\test_atlas.py

# Actual local-file browser behaviour, themes, keyboard, filters and screenshots.
.\.venv\Scripts\python.exe tests\test_browser.py
```

Native workbook creation requires Microsoft Excel on Windows and pywin32. It opens a **new isolated Excel instance**, disables macros/links/alerts, calculates, creates pivots, saves only this workbook and quits only that instance. No existing user workbook is attached to or closed. Browser checks use installed Playwright Chromium or Microsoft Edge; missing browsers may need installing separately.

`build.py` without `--excel` reuses the already validated workbook/report. `--execute` runs the notebook with the interpreter invoking the build. `sources.py` reuses the pinned local snapshot and rejects a hash mismatch; updating to a new snapshot requires explicit provenance review.

## Workbook review and update boundary

Start with **Read Me → Dashboard → Reconciliation → Payroll Pivot → Exceptions**. **Lookup Lab** independently compares XLOOKUP/INDEX-MATCH/VLOOKUP, including an explicit missing key. **Approvals** drives expected gross; multiple current salary events trigger ambiguity rather than first-match guessing. **Absence Exposure/Summary**, **Time Review**, **Visa Tracker** and **Case Tracker** demonstrate formula-driven operational reporting. **System Mapping/SOP** document proposed platform contracts, escalation and sign-off.

Change clean-sheet inputs or Parameters to explore formulas, then **Data → Refresh All** for pivots. Raw-to-clean transformations, validated roster membership, daily-time aggregation and unioned absence dates are generated by Python; editing a raw worksheet alone does not refresh the clean model. The as-of date and reporting-window changes require rebuilding extracts. Browser scenario/triage changes are temporary, clearly simulated and do not modify the baseline files.

## Methodological and operational limits

CSO means are aggregate enterprise-survey estimates, not individual pay benchmarks or employer-specific comparisons. Employment, earnings and paid hours have different concepts/denominators; the estimates are unadjusted, nominal and revisable. Descriptive change correlations use a small, serially dependent quarterly series; no p-values, causal or individual-level claims are made.

Fictional payroll is full-month approved gross only: no tax, net pay, PRSI, pension or proration. Absence assumes weekday/FTE exposure, without public holidays or custom rosters. Lost days are clipped to employment dates and overlapping dates unioned; time collisions require source review, not inference about health or motive.

The working-time lab uses **17 complete weeks**, not the statutory **four calendar months**. [WRC guidance](https://www.workplacerelations.ie/en/what_you_should_know/hours-and-wages/working_hours/) informs screening only; statutory leave adjustments, weekly rest, exemptions, compensatory rest, night work and legal judgements are not fully implemented. Complete absence of time records is retained as unknown, not silently dropped. Logged break totals do not prove compliant break timing.

Visa horizons are analyst-set service levels, not immigration rules; submitted renewals do not establish permission. PIP/ER records are fictional administration metadata. Closure requires qualified, authorised human judgement and source evidence.

Before real deployment: confirm data-owner and AI-use authorisation, minimise/restrict sensitive fields, confirm EUDB/FedRAMP scope if relevant, validate source mappings and legal/roster/holiday rules, segregate correction approvals and obtain HR/payroll/legal sign-off. No production-readiness or employer-impact claim is made.
