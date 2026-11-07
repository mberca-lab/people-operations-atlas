"""Pin an official public aggregate snapshot; never load internal employee data."""

import hashlib
import itertools
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/EHQ03/JSON-stat/2.0/en"
METHOD = "https://www.cso.ie/en/methods/earnings/earningshoursandemploymentcostssurvey/"
NOTES = "https://www.cso.ie/en/methods/surveybackgroundnotes/earningsandlabourcostsquarterly/"
LICENSE = "https://data.gov.ie/dataset/ehq03-average-earnings-hours-worked-employment-and-labour-costs"
WRC = "https://www.workplacerelations.ie/en/what_you_should_know/hours-and-wages/working_hours/"


def decode_cube(data):
    dimensions = data["id"]
    categories = []
    for name in dimensions:
        index = data["dimension"][name]["category"]["index"]
        categories.append(
            index if isinstance(index, list) else sorted(index, key=index.get)
        )
    values = data["value"]
    rows = []
    for offset, codes in enumerate(itertools.product(*categories)):
        value = values.get(str(offset)) if isinstance(values, dict) else values[offset]
        row = {name: code for name, code in zip(dimensions, codes)}
        row["value"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def load_public():
    snapshot = ROOT / "data" / "public" / "ehq03.json"
    provenance = ROOT / "data" / "public" / "provenance.json"
    raw = snapshot.read_bytes()
    metadata = json.loads(provenance.read_text())
    if hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise ValueError("Public snapshot hash differs from the recorded source.")
    data = json.loads(raw)
    frame = decode_cube(data)
    required = ["STATISTIC", "TLIST(Q1)", "C02665V03225", "C02397V02888", "value"]
    if list(frame) != required:
        raise ValueError("CSO dimension layout changed; review before rebuilding.")
    selected = frame[
        frame["C02397V02888"].eq("-")
        & frame["STATISTIC"].isin(
            ["EHQ03C01", "EHQ03C02", "EHQ03C03", "EHQ03C05", "EHQ03C08"]
        )
    ].copy()
    for name in required[:-1]:
        selected[name + "_label"] = selected[name].map(
            data["dimension"][name]["category"]["label"]
        )
    selected = selected.rename(columns={
        "STATISTIC": "metric_code", "STATISTIC_label": "metric",
        "TLIST(Q1)": "quarter_code", "TLIST(Q1)_label": "quarter",
        "C02665V03225": "sector_code", "C02665V03225_label": "sector",
    })
    selected["value"] = pd.to_numeric(selected["value"], errors="coerce")
    units = data["dimension"]["STATISTIC"]["category"].get("unit", {})
    selected["unit"] = selected["metric_code"].map(
        {code: unit.get("label", "") for code, unit in units.items()}
    )
    selected = selected[selected["quarter"].ge("2019Q1")]
    selected = selected[
        ["metric_code", "metric", "quarter", "sector_code", "sector", "value", "unit"]
    ]
    if selected.duplicated(["metric_code", "quarter", "sector_code"]).any():
        raise ValueError("Public series keys are not unique.")
    return selected.sort_values(["metric_code", "sector_code", "quarter"]), metadata


def acquire():
    folder = ROOT / "data" / "public"
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "ehq03.json").exists():
        frame, metadata = load_public()
    else:
        request = urllib.request.Request(URL, headers={"User-Agent": "PeopleOperationsAtlas/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
        data = json.loads(raw)
        if data.get("extension", {}).get("official") is not True:
            raise ValueError("Expected an official CSO dataset.")
        metadata = {
            "publisher": "Central Statistics Office, Ireland",
            "dataset": "EHQ03",
            "label": data["label"],
            "url": URL,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "publisher_updated": data.get("updated"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "license": "Creative Commons Attribution 4.0",
            "license_url": LICENSE,
            "methodology_url": METHOD,
            "background_url": NOTES,
            "working_time_guidance_url": WRC,
            "raw_dimensions": data["id"],
            "raw_size": data["size"],
            "raw_cells": len(decode_cube(data)),
            "selection": "All employees; unadjusted Employment, Weekly Earnings, Hourly Earnings, Weekly Paid Hours and Hourly Total Labour Costs; 2019Q1 onward. All published sectors retained, never summed across overlapping sector groupings.",
            "boundaries": [
                "Public sector aggregates, not Waystone or employee-level data.",
                "Survey coverage: enterprises with 3+ employees; all with 50+ and a sample with 3-49. Small enterprises below 3 employees are excluded.",
                "Means are not individual salary benchmarks. Employment and earnings have different denominator definitions.",
                "Hours are paid hours, not individual actual working hours or working-time compliance evidence.",
                "Unadjusted quarter-on-quarter changes may reflect seasonality; year-on-year comparisons are descriptive, nominal and subject to revisions.",
                "Missing published cells remain missing; no interpolation or imputation.",
                "NACE K is a broad finance/insurance context, not a company-specific peer match.",
                "Use the current survey methodology for current coverage; the general background page contains older legislation and register details.",
            ],
        }
        (folder / "ehq03.json").write_bytes(raw)
        (folder / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        frame, metadata = load_public()
    frame.to_csv(folder / "workforce_context.csv", index=False)
    print(frame.dtypes.to_string())
    print(frame.head(5).to_string(index=False))
    print(f"Selected cells: {len(frame):,}; missing: {frame['value'].isna().sum():,}; latest: {frame['quarter'].max()}")
    print("SHA256:", metadata["sha256"])
    print("Metric units:", frame.groupby("metric")["unit"].first().to_dict())


if __name__ == "__main__":
    acquire()
