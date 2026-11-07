"""Generate an offline visual story, analytical figures and an executable notebook."""

import argparse
import json
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
import seaborn as sns

from analysis import DEPARTMENTS, records, run
from review_scenarios import make_review_pack
from sources import ROOT


def public_findings(public):
    rows = []
    for (metric, sector), series in public.groupby(["metric_code", "sector_code"]):
        series = series.sort_values("quarter")
        latest = series.iloc[-1]
        prior = series.iloc[-5]
        baseline = series[series["quarter"].eq("2019Q1")].iloc[0]
        rows.append({
            "metric_code": metric, "sector_code": sector, "quarter": latest["quarter"],
            "latest": float(latest["value"]), "baseline": float(baseline["value"]),
            "index": round(float(latest["value"] / baseline["value"] * 100), 3),
            "yoy_pct": round(float((latest["value"] / prior["value"] - 1) * 100), 3),
        })
    return pd.DataFrame(rows)


def plots(public, result):
    folder = ROOT / "outputs" / "plots"
    folder.mkdir(parents=True, exist_ok=True)
    sns.set_style("whitegrid")
    palette = ["#0f6b70", "#183247", "#487da0", "#80949c", "#183247"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})

    def save(name):
        plt.tight_layout()
        plt.savefig(folder / f"{name}.png", bbox_inches="tight", dpi=100)
        plt.savefig(folder / f"{name}.svg", bbox_inches="tight")
        plt.close()

    fig, ax = plt.subplots(figsize=(12, 5))
    for sector, color in [("K", palette[0]), ("-", palette[1])]:
        series = public[public["metric_code"].eq("EHQ03C01") & public["sector_code"].eq(sector)]
        index = series["value"] / series["value"].iloc[0] * 100
        ax.plot(series["quarter"], index, label=series["sector"].iloc[0], color=color, linewidth=2.5)
    ax.set(title="Irish employment context · 2019Q1 = 100", xlabel="Quarter", ylabel="Index (2019Q1 = 100)")
    ax.set_xticks(range(0, 30, 4))
    ax.legend(frameon=False)
    save("public_employment")

    changes = public[public["sector_code"].eq("K")].pivot(index="quarter", columns="metric", values="value").pct_change().dropna() * 100
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(changes.corr(), vmin=-1, vmax=1, center=0, annot=True, fmt=".2f",
                cmap=sns.diverging_palette(220, 165, as_cmap=True), ax=ax)
    ax.set(title="Finance/insurance quarter-to-quarter changes · descriptive Pearson r", xlabel="Metric", ylabel="Metric")
    save("public_change_correlations")
    changes.to_csv(ROOT / "outputs" / "tables" / "public_quarterly_changes_K.csv")

    selected = changes.iloc[:, :3]
    pair = sns.pairplot(selected, diag_kind="hist", plot_kws={"color": palette[0], "alpha": 0.65})
    pair.fig.suptitle("Finance/insurance changes (%) · exploratory, serially dependent", y=1.02)
    pair.savefig(folder / "public_change_pairs.png", bbox_inches="tight", dpi=100)
    plt.close(pair.fig)

    recon = result["reconciliation"]
    known = recon[recon["delta_eur"].notna()]
    fig, ax = plt.subplots(figsize=(11, 4))
    sns.histplot(data=known, x="delta_eur", bins=30, color=palette[0], ax=ax)
    ax.set(title="Fictional payroll differences · common comparable base", xlabel="Actual minus approved gross (EUR)", ylabel="Employee records")
    save("payroll_distribution")

    heat = result["absence_summary"].pivot(index="department", columns="month", values="rate_pct").reindex(DEPARTMENTS)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(heat, annot=True, fmt=".2f", cmap=sns.light_palette(palette[0], as_cmap=True), cbar_kws={"label": "Lost / scheduled hours (%)"}, ax=ax)
    ax.set(title="Fictional absence rates · FTE-weighted weekday exposure", xlabel="Month", ylabel="Department")
    save("absence_heatmap")

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.boxplot(data=result["time_summary"], x="department", y="average_hours", color="#f7f4ef", ax=ax)
    sns.stripplot(data=result["time_summary"], x="department", y="average_hours", color=palette[0], alpha=0.5, jitter=0.2, ax=ax)
    ax.axhline(48, color=palette[1], linestyle="--", label="48h screening threshold")
    ax.set(title="Fictional weekly hours · incomplete coverage reviewed separately", xlabel="Department", ylabel="Observed mean hours/week (17-week screen)")
    ax.tick_params(axis="x", rotation=15)
    ax.legend(frameon=False)
    save("working_time")

    exception_counts = result["exceptions"].groupby("area").size().sort_values()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(exception_counts.index, exception_counts.values, color=palette[0])
    ax.set(title="Synthetic exception register · flags by control area", xlabel="Exception flags (multiple per employee possible)", ylabel="Control area")
    save("exception_areas")


def notebook(public, provenance, result):
    nbf = nbformat.v4
    cells = [
        nbf.new_markdown_cell(
            "# Workforce Analytics & People Operations\n"
            "## An interactive portfolio demonstration\n\n"
            "Independent, AI-assisted project by Margarita Bermejo Cano. No affiliation with Waystone.\n\n"
            "**Data sources:** official CSO workforce aggregates and a synthetic multi-system HR dataset. "
            "Operational results describe the demonstration dataset."
        ),
        nbf.new_markdown_cell(
            "## EDA decision log\n\n"
            f"- **Source:** CSO EHQ03, official API; snapshot SHA-256 `{provenance['sha256']}`.\n"
            f"- **Scale:** {provenance['raw_cells']:,} published cube cells; {len(public):,} selected cells; full data, no sampling.\n"
            "- **Selection:** all employees, five unadjusted metrics, all published sectors, 2019Q1 onward. Overlapping sector aggregates are analysed separately.\n"
            "- **Level:** in-depth operational analysis: quality, reconciliation, exceptions, distributions, relationships, controls and limitations.\n"
            "- **Synthetic source:** seed 731; 360 fictional employees; as-of 2026-10-31; seven independent-format feeds. No real sensitive records.\n"
            "- **Analytical approach:** deterministic validation and reconciliation controls address the operational reporting requirements. Predictive employee scoring and causal inference are outside scope.\n"
            "- **Uncertainty:** public revisions and missing inferential variances; fictional payroll assumptions; statutory working-time periods; holiday calendars; real HR/legal judgement."
        ),
        nbf.new_code_cell(
            "from pathlib import Path\nimport sys, json\nimport pandas as pd\nimport numpy as np\n"
            "import matplotlib.pyplot as plt\nimport seaborn as sns\nfrom IPython.display import display, Image\n"
            "ROOT = Path.cwd()\nsys.path.insert(0, str(ROOT / 'scripts'))\n"
            "from analysis import run\nfrom build import public_findings, plots\n"
            "public, provenance, sources, result = run()\n"
            "sns.set_style('whitegrid')\npd.set_option('display.max_columns', 20)\n"
            "OUTPUT = ROOT / 'outputs'\n"
            "display(pd.DataFrame([{'source': name, 'rows': len(frame), 'columns': len(frame.columns),"
            "'memory_MB': round(frame.memory_usage(deep=True).sum()/1024**2,2)} for name,frame in sources.items()]))"
        ),
        nbf.new_markdown_cell("## 1 / Data structure and completeness\nReview the units, reporting grains and missing values in each source. Missing critical employment or payroll values remain unknown and are referred for resolution."),
        nbf.new_code_cell(
            "display(public.head(5)); display(public.tail(5)); display(public.dtypes.to_frame('dtype'))\n"
            "display(public.describe(include='all'))\n"
            "display(pd.DataFrame({'missing': public.isna().sum(), 'missing_pct': public.isna().mean()*100}))\n"
            "display(sources['hr_raw'].head(5))\n"
            "display(pd.DataFrame({name: frame.replace('', np.nan).isna().sum() for name, frame in sources.items()}).fillna('not a field'))\n"
            "print('Selected public key duplicates:', public.duplicated(['metric_code','sector_code','quarter']).sum())\n"
            "print('Exact raw HR payload duplicates:', sources['hr_raw'].drop(columns='source_row').duplicated().sum())"
        ),
        nbf.new_markdown_cell(
            "## 2 / Public workforce context\n"
            "CSO means describe enterprise-survey aggregates. Individual salary benchmarking requires a suitable employee-level comparison. Employment, earnings and paid hours use different concepts. "
            "Nominal, unadjusted changes may reflect seasonality, bonuses or workforce composition. Year-on-year comparisons provide context; inflation adjustment is outside scope."
        ),
        nbf.new_code_cell(
            "findings = public_findings(public)\n"
            "findings.to_csv(OUTPUT / 'tables' / 'public_findings.csv', index=False)\n"
            "display(findings[findings['sector_code'].isin(['K','-'])])\n"
            "plots(public, result)\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'public_employment.png')))"
        ),
        nbf.new_markdown_cell(
            "## 3 / Relationships and outlier sensitivity\n"
            "Within finance/insurance, inspect changes rather than correlations between trending levels. "
            "These are only 29 quarterly differences, serially dependent and based on aggregate survey estimates. "
            "Pearson correlations and IQR outliers are used as descriptive diagnostics. Serial dependence, sample size and aggregate survey estimation limit statistical inference; formal significance and causal tests are outside scope."
        ),
        nbf.new_code_cell(
            "wide = public[public['sector_code'].eq('K')].pivot(index='quarter', columns='metric', values='value')\n"
            "changes = wide.pct_change().dropna()*100\n"
            "display(changes.describe())\n"
            "display(changes.agg(['skew','kurt']))\n"
            "q1, q3 = changes.quantile(.25), changes.quantile(.75)\n"
            "flag = changes.lt(q1-1.5*(q3-q1)) | changes.gt(q3+1.5*(q3-q1))\n"
            "display(flag.sum().to_frame('IQR diagnostic quarters'))\n"
            "display(changes.corr())\n"
            "display(changes.loc[~changes.index.str.startswith('2020')].corr())\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'public_change_correlations.png')))\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'public_change_pairs.png')))"
        ),
        nbf.new_markdown_cell(
            "## 4 / Data validation and reporting population\n"
            "Normalise keys and field types, collapse only equivalent payloads, quarantine conflicts and reject critical-field failures. "
            "The synthetic roster contains 360 employee keys. Validation and employment-date rules define the active reporting population. "
            "Exact repeats and conflicting records have different treatment."
        ),
        nbf.new_code_cell(
            "display(pd.Series(result['qa']).to_frame('value'))\n"
            "display(result['exceptions'][result['exceptions']['area'].eq('HR master')])\n"
            "display(result['active_hr'].groupby('department').agg(headcount=('employee_id','size'),fte=('fte','sum')))"
        ),
        nbf.new_markdown_cell(
            "## 5 / Payroll reconciliation and investigation\n"
            "Approved full-time annual salary / 12 x FTE + approved recurring allowance + approved variable pay. "
            "This baseline covers full months; separate examples below illustrate base-pay proration. Tax, PRSI, pension and net-pay checks remain outside scope. Unmatched or unknown amounts are excluded from the common comparable sum. "
            "Report signed and absolute discrepancies to show both the net effect and the total variance magnitude. Root-cause examples are deliberately introduced in the synthetic data."
        ),
        nbf.new_code_cell(
            "recon = result['reconciliation']\n"
            "display(recon['result'].value_counts().to_frame('employees'))\n"
            "display(recon[recon['result'].ne('Reconciled')][['employee_id','expected_gross_eur','gross_eur','delta_eur','result']])\n"
            "display(sources['approvals'][sources['approvals']['employee_id'].isin(['EMP0018','EMP0044','EMP0055'])])\n"
            "common = recon[recon['delta_eur'].notna()]\n"
            "assert round(common['gross_eur'].sum()-common['expected_gross_eur'].sum(),2) == result['qa']['signed_payroll_delta_eur']\n"
            "assert recon.loc[recon['employee_id'].isin(['EMP0044','EMP0055']),'result'].eq('Reconciled').all()\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'payroll_distribution.png')))"
        ),
        nbf.new_markdown_cell(
            "## 6 / Absence rates and scheduled exposure\n"
            "Deduplicate episodes, validate dates and keys, union scheduled lost dates and reconcile worked-time collisions. "
            "The denominator uses weekdays within employment dates multiplied by FTE x 7.5 hours/day. "
            "Separate examples below apply explicit rosters and an assumed office closure. The baseline analysis uses synthetic scheduling metadata and excludes health information."
        ),
        nbf.new_code_cell(
            "display(result['absence_summary'])\n"
            "display(result['exceptions'][result['exceptions']['area'].eq('Absence')])\n"
            "assert result['qa']['absence_naive_valid_days'] - result['qa']['absence_overlap_days_removed'] == result['qa']['absence_unique_days']\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'absence_heatmap.png')))"
        ),
        nbf.new_markdown_cell(
            "## 7 / Working-time review and completeness\n"
            "The WRC general rule is a 48-hour average over four calendar months, with exceptions. "
            "This lab uses 17 complete weeks (2026-07-06 to 2026-10-30) as an operational screen only. "
            "Coverage gaps remain unknown; annual/sick-leave adjustments, weekly rest, reference-period exceptions and compensatory rest need HR/legal review. "
            "Peak weeks and reference-period averages are reviewed separately. A statutory assessment would require the applicable period, adjustments and qualified legal interpretation."
        ),
        nbf.new_code_cell(
            "display(result['time_summary'].groupby('result').agg(employees=('employee_id','size'),mean_observed=('average_hours','mean')))\n"
            "display(result['time_summary'][result['time_summary']['employee_id'].isin(['EMP0100','EMP0103','EMP0150','EMP0170'])])\n"
            "display(result['exceptions'][result['exceptions']['area'].eq('Working time')])\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'working_time.png')))"
        ),
        nbf.new_markdown_cell(
            "## 8 / Visa, PIP and ER administration\n"
            "Fictional metadata illustrates expiry horizons, owner/evidence gaps and overdue review dates. "
            "The 90-day review horizon is an operational service-level assumption. "
            "Sensitive personal fields and substantive employment decisions are excluded. "
            "Provider coordination and specialist HR judgement are represented by proposed procedures; practical experience requires separate evidence."
        ),
        nbf.new_code_cell(
            "display(result['visa'][['case_id','employee_id','expiry_date','days_remaining','status','owner','evidence','result']])\n"
            "display(result['cases'].groupby(['case_type','result']).size().to_frame('cases'))\n"
            "display(result['exceptions'].groupby(['area','severity']).size().unstack(fill_value=0))\n"
            "display(Image(filename=str(OUTPUT / 'plots' / 'exception_areas.png')))"
        ),
        nbf.new_markdown_cell(
            "## 9 / Controls, Excel evidence and requirement coverage\n"
            "Inspect the native Excel PivotTables and editable formulas. Raw-to-clean transformations and roster membership are regenerated by Python; clean-input formulas and pivots recalculate in Excel. "
            "The control designs require operational approval before implementation. Employer impact would need measurement in a live setting."
        ),
        nbf.new_code_cell(
            "requirements = pd.DataFrame(json.loads((ROOT/'assets'/'requirements.json').read_text()))\n"
            "display(requirements)\n"
            "display(pd.Series(json.loads((OUTPUT/'excel_validation.json').read_text())))\n"
            "assert json.loads((OUTPUT/'excel_validation.json').read_text())['formula_errors'] == []\n"
            "assert json.loads((OUTPUT/'excel_validation.json').read_text())['pivot_tables'] == 2\n"
            "summary = {'public_source': provenance, 'operational_findings': result['qa'], 'requirement_levels': requirements['level'].value_counts().to_dict()}\n"
            "(OUTPUT/'analysis_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')\n"
            "display(requirements['level'].value_counts().to_frame('requirements'))"
        ),
        nbf.new_markdown_cell(
            "## Findings and next actions\n\n"
            f"- **{result['qa']['active_headcount']} validated active employees** after applying master-data and employment-date rules; excluded records remain in the audit trail.\n"
            f"- **{result['qa']['payroll_amount_exceptions']} amount discrepancies**: net EUR {result['qa']['signed_payroll_delta_eur']:,.2f}, absolute EUR {result['qa']['absolute_payroll_delta_eur']:,.2f}, on the same {result['qa']['comparable_payroll_rows']}-record comparable base.\n"
            f"- **{result['qa']['absence_overlap_days_removed']} overlapping scheduled day(s)** removed from the numerator; worked-time collisions require source review.\n"
            f"- **{result['qa']['time_above_screen']} above-screen time records and {result['qa']['time_incomplete']} incomplete record** require HR/legal review of the relevant hours and coverage.\n"
            f"- **{result['qa']['visa_within_90_days']} fictional permissions in the 0–90-day horizon**, plus {result['qa']['visa_expired_records']} expired records requiring authorised verification.\n"
            "- Immediate control priorities: identity uniqueness; approved effective-dated compensation; lifecycle/payroll cutoff; absence overlap/time reconciliation; complete time data; owned visa/case follow-up.\n"
            "- Before real use: confirm data-owner permissions and AI scope, minimise sensitive fields, add legal/roster/holiday rules, test source-system mappings, obtain HR/payroll/legal review and segregate correction approval.\n"
            "- CV/interview evidence required: years of experience, live BambooHR capability, immigration administration, Tier 2 ER judgement and hands-on Power BI authoring."
        ),
    ]
    cells.extend([
        nbf.new_markdown_cell(
            "## Supplementary operational review\n\n"
            "These separate synthetic cases extend the original reporting model. "
            "The baseline workforce and exception register remain unchanged.\n\n"
            "- **Payroll closure:** apply APR-018 in a separate extract, re-run the controls and independently verify the corrected gross. Role assignments and sign-offs are simulated.\n"
            "- **Starter/leaver pay:** inclusive calendar-day base-pay proration under an explicitly assumed policy.\n"
            "- **Absence:** employee-specific rosters, a synthetic office closure on 26 October, employment dates and overlapping episode union. Roster hours already encode working patterns.\n"
            "- **Working time:** 1 July–31 October, complete calendar-day coverage including recorded rest days, and tagged annual/sick-leave exclusions. Other statutory exclusions, reference-period selection and legal applicability require qualified review.\n\n"
            "[Organisation of Working Time Act, section 15](https://revisedacts.lawreform.ie/eli/1997/act/20/section/15/revised/en/html)."
        ),
        nbf.new_code_cell(
            "from review_scenarios import make_review_pack\n"
            "review = make_review_pack(sources, result)\n"
            "closure = review['closure']\n"
            "display(pd.DataFrame(closure['events']))\n"
            "display(pd.DataFrame([{'version': name, **closure[key]} for name,key in [('Original','before_qa'),('Corrected scenario','after_qa')]])[['version','reconciled_employees','payroll_amount_exceptions','signed_payroll_delta_eur','absolute_payroll_delta_eur']])\n"
            "assert closure['corrected_delta_eur'] == 0\n"
            "display(pd.DataFrame(review['proration']))\n"
            "display(pd.DataFrame(review['roster_summary']))\n"
            "display(pd.DataFrame(review['calendar_summary']))\n"
            "summary['review_scenarios'] = {key: review[key] for key in ['closure','proration','roster_summary','calendar_summary','scope','time_source']}\n"
            "(OUTPUT/'analysis_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')"
        ),
    ])
    notebook = nbf.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": sys.version.split()[0]},
    })
    nbformat.write(notebook, ROOT / "analysis.ipynb")


def execute_notebook():
    from jupyter_client import KernelManager
    from nbclient import NotebookClient
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    book = nbformat.read(ROOT / "analysis.ipynb", as_version=4)
    client = NotebookClient(book, km=manager, timeout=180, resources={"metadata": {"path": str(ROOT)}})
    try:
        client.execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.write(book, ROOT / "analysis.ipynb")
    print("Executed notebook:", sum(cell.cell_type == "code" for cell in book.cells), "code cells")


def build_site(public, provenance, sources, result, review):
    from openpyxl import load_workbook
    requirements = json.loads((ROOT / "assets" / "requirements.json").read_text())
    excel = json.loads((ROOT / "outputs" / "excel_validation.json").read_text())
    flagged = set(result["exceptions"]["employee_id"])
    dots = [{
        "id": person["employee_id"], "department": person["department"],
        "flag": person["employee_id"] in flagged,
    } for person in records(sources["fixture_roster"])]
    row = list(result["hr_clean"]["employee_id"]).index("EMP0018") + 2
    book = load_workbook(ROOT / "outputs" / "People_Operations_Control_Workbook.xlsx", read_only=True, data_only=False)
    try:
        guide = {"reconciliation_row": row, "lookup": book["Lookup Lab"]["B2"].value,
                 "expected": book["Reconciliation"][f"I{row}"].value,
                 "delta": book["Reconciliation"][f"K{row}"].value}
    finally:
        book.close()
    payload = {
        "qa": result["qa"], "provenance": provenance, "excel": excel, "review": review, "excel_guide": guide,
        "public": records(public[["metric_code", "quarter", "sector_code", "value"]]),
        "public_findings": records(public_findings(public)),
        "metrics": records(public[["metric_code", "metric", "unit"]].drop_duplicates()),
        "sectors": records(public[["sector_code", "sector"]].drop_duplicates()),
        "exceptions": records(result["exceptions"]),
        "reconciliation": records(result["reconciliation"]),
        "absence": records(result["absence_summary"]),
        "time": records(result["time_summary"]),
        "visa": records(result["visa"]), "cases": records(result["cases"]),
        "requirements": requirements, "departments": DEPARTMENTS, "dots": dots,
        "approvals": records(sources["approvals"]),
        "source_counts": {name: len(frame) for name, frame in sources.items() if name != "fixture_roster"},
        "level_counts": dict(Counter(item["level"] for item in requirements)),
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    template = (ROOT / "assets" / "site-template.html").read_text(encoding="utf-8")
    if template.count("__DATA__") != 1:
        raise ValueError("Expected one inline-data placeholder.")
    (ROOT / "index.html").write_text(template.replace("__DATA__", encoded), encoding="utf-8")
    public_findings(public).to_csv(ROOT / "outputs" / "tables" / "public_findings.csv", index=False)
    (ROOT / "outputs" / "site_data.json").write_text(encoded, encoding="utf-8")
    print("Built offline portfolio:", ROOT / "index.html")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    public, provenance, sources, result = run()
    review = make_review_pack(sources, result)
    (ROOT / "outputs" / "review_scenarios.json").write_text(json.dumps(review, indent=2, allow_nan=False), encoding="utf-8")
    for key in ["corrected_payroll", "proration", "roster_days", "roster_summary", "calendar_days", "calendar_summary"]:
        pd.DataFrame(review[key]).to_csv(ROOT / "outputs" / "tables" / f"review_{key}.csv", index=False)
    if args.excel:
        from excel_workbook import build, calculate_and_pivot
        calculate_and_pivot(build(public, sources, result, review))
    plots(public, result)
    notebook(public, provenance, result)
    build_site(public, provenance, sources, result, review)
    if args.execute:
        execute_notebook()


if __name__ == "__main__":
    main()
