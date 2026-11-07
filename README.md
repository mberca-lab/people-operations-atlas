# Workforce Analytics & People Operations

An independent, AI-assisted People Data & Operations portfolio project by Margarita Bermejo Cano. **Official public data and clearly labelled fictional demonstrations; not affiliated with Waystone.**

**[Explore the live portfolio](https://mberca.github.io/people-operations-atlas/)** · [Download the complete portfolio package](https://github.com/mberca/people-operations-atlas/releases/latest/download/Workforce_Analytics_Portfolio.zip)

The atlas presents Irish workforce trends, multi-source data validation, payroll reconciliation, absence reporting, working-time review and case governance. An interactive source-system map and a 29-requirement evidence map connect the analysis to the People Data & Operations role.

The main review follows four sections: **review brief → payroll investigation → People Operations → Excel and evidence**. An annotated **Evidence Folio** brings the original payment, approved calculation and review note together; selecting a review stage highlights the corresponding evidence. The correction uses a separate extract and simulated sign-off. Navy/teal styling distinguishes analytical content from amber/red control warnings.

The complete public-data charts, source-system map, reporting populations, exception register, absence/time/renewal trackers and operational scenarios remain in **Detailed analysis and methods**, collapsed initially. Existing topic links open the relevant detail automatically, including links shared directly to a section. All 29 requirements are available in the expandable evidence map; important synthetic-data and professional-experience boundaries remain visible in the main review.

The main payroll review includes the baseline discrepancy bridge with animated bar entry, a tracing path and a guided three-case review. Selecting a case pauses the automatic review; hovering or focusing the visual suspends it while evidence is read. Motion pauses off-screen and respects reduced-motion preferences. The workforce constellation remains visible on desktop and mobile. All displayed amounts stay fixed to the validated baseline; the folio correction remains a separate scenario.

For offline review, extract `Workforce_Analytics_Portfolio.zip` and open `index.html`. Keep the accompanying folders so that the workbook, notebook and summary downloads remain available.

## Evidence layers

**Public:** CSO Ireland EHQ03, *Average Earnings, Hours Worked, Employment and Labour Costs*, CC BY 4.0. The pinned official snapshot contains 130,536 cells; the analysis selects 3,150 all-employee cells across five unadjusted measures and 30 quarters, 2019Q1–2026Q2. Source hash, URLs, retrieval date, units and coverage are in `data\public\provenance.json`. Indexing and changes are transformations; public cells are never silently imputed. Overlapping published sector aggregates are never summed.

**Synthetic operations:** 360 fictional employee keys across seven HR/payroll/approval/absence/time/visa/case feeds, seed 731, as-of 2026-10-31. All operational records are synthetic; sensitive personal and employer data are excluded. Deliberately introduced data-quality issues support the control demonstrations.

**Professional experience:** the evidence map distinguishes implemented features, synthetic scenarios and proposed procedures. Years of experience, live BambooHR capability, Tier 2/ER judgement, immigration administration and Power BI authoring require separate CV and interview evidence.

## Deliverables

| File | What to inspect |
|---|---|
| `index.html` | Four-section interactive portfolio, annotated payroll Evidence Folio and expandable analytical detail; desktop/mobile; light/dark; reduced motion; keyboard inspection; accessible tables; no trackers or runtime requests |
| `analysis.ipynb` | Executed in-depth notebook: source audit, missingness, descriptive trends/distributions, change correlations/sensitivity, reconciliation, exceptions and limitations |
| `outputs\People_Operations_Control_Workbook.xlsx` | Editable formulas, XLOOKUP, INDEX/MATCH, exact VLOOKUP, nested logic, validation, absence exposure, time/visa/case controls and **two genuine native Excel PivotTables** |
| `outputs\analysis_summary.json` | Source provenance, baseline operational metrics and requirement-level counts |
| `outputs\review_scenarios.json` | Separate payroll closure evidence, extract hashes, calendar-day proration, roster-aware absence and four-calendar-month time examples |
| `outputs\tables\` | Reproducible cleaned/analysed tables; all operational rows are fictional |
| `outputs\plots\` | Labelled PNG/SVG analysis figures |
| `outputs\*_validation.json` | Native formula/pivot validation, Python/Excel parity and scenario tests, browser checks |
| `outputs\screenshots\` | Verified desktop/mobile visual captures |

## Main fictional control results

364 raw HR rows → 360 keys → 355 valid masters → 344 active people / 324 FTE → 340 payroll-comparable records → 337 reconciled. The exception register retains quarantined conflicts, invalid fields and unresolved payments. Employment-date rules determine starter and leaver inclusion.

The comparable base yields a **EUR 1,847.33 signed discrepancy** and **EUR 2,652.67 absolute discrepancy**. Approved salary and variable-pay changes reconcile; unsupported movement, allowance mismatch and stale salary require follow-up. Absence uses 296 unique scheduled lost dates after removing one overlap; the FTE-weighted lost-hour rate is 0.975%. Seven complete time records exceed the baseline screen and one incomplete record requires coverage review. Visa and case flags identify operational follow-up priorities.

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

Start with **Read Me → Excel Walkthrough → Dashboard → Reconciliation → Payroll Pivot → Exceptions**. **Lookup Lab** independently compares XLOOKUP/INDEX-MATCH/VLOOKUP, including an explicit missing key. **Approvals** drives expected gross; multiple current salary events trigger ambiguity rather than first-match guessing. **Absence Exposure/Summary**, **Time Review**, **Visa Tracker** and **Case Tracker** demonstrate formula-driven operational reporting. **System Mapping/SOP** document proposed platform contracts, escalation and sign-off.

Change clean-sheet inputs or Parameters to explore formulas, then **Data → Refresh All** for pivots. Raw-to-clean transformations, validated roster membership, daily-time aggregation and unioned absence dates are generated by Python; editing a raw worksheet alone does not refresh the clean model. The as-of date and reporting-window changes require rebuilding extracts. Browser scenario/triage changes are temporary, clearly simulated and do not modify the baseline files.

**Supplementary review sheets:** Closure Review links the original Dashboard to a separate corrected scenario; Closure Evidence records the five simulated review stages. Applying APR-018 resolves EMP0018's EUR -402.67 discrepancy, increases reconciled employees from 337 to 338 and leaves two amount discrepancies totalling EUR 2,250.00. Original and corrected payroll versions have canonical UTF-8/LF CSV hashes.

Proration Examples contains formula-driven calendar-day base-pay calculations for a starter, leaver and part-time employee. Roster Days/Summary clips schedules to employment dates, removes an assumed office closure and unions overlapping absence dates. Calendar Days/Review uses 1 July–31 October, explicit rest-day records and tagged annual/sick-leave exclusions; a missing weekend record remains unknown.

## Methodological and operational limits

CSO means describe aggregate enterprise-survey estimates. Individual pay benchmarking and employer-specific comparisons require suitable additional data. Employment, earnings and paid hours have different concepts and denominators; the estimates are unadjusted, nominal and revisable. Change correlations are descriptive, based on a small, serially dependent quarterly series. Statistical significance and causal inference are outside scope.

Baseline payroll covers full-month approved gross; separate examples illustrate calendar-day base-pay proration under an assumed policy. Tax, net pay, PRSI and pensions remain outside scope. Baseline absence assumes weekday/FTE exposure; supplementary examples use explicit rosters and a synthetic office closure. Actual holiday arrangements require policy validation. Lost days are clipped to employment dates and overlapping dates combined. Absence/time collisions require source reconciliation.

The baseline working-time review covers **17 complete weeks**. A separate **four-calendar-month** illustration excludes tagged annual/sick-leave days, referencing [section 15](https://revisedacts.lawreform.ie/eli/1997/act/20/section/15/revised/en/html) and [WRC guidance](https://www.workplacerelations.ie/en/what_you_should_know/hours-and-wages/working_hours/). Other statutory exclusions, leave-period interpretation, reference-period applicability, weekly rest, exemptions, compensatory rest and night work require further assessment. Missing time records remain unknown. Break timing requires review in addition to logged duration.

Visa horizons are analyst-set service levels. Continuing permission requires authorised verification, including review of the renewal evidence. PIP/ER records contain fictional administration metadata. Closure requires qualified HR judgement and source evidence.

Before operational implementation, confirm data-owner and AI-use authorisation, minimise restricted fields, confirm EUDB/FedRAMP scope where relevant, validate source mappings and legal/roster/holiday rules, segregate correction approvals and obtain HR/payroll/legal sign-off. Employer impact would require measurement after implementation.
