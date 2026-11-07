"""Reproducible public context and a fully fictional, seeded HR operations lab."""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from sources import ROOT, load_public

AS_OF = pd.Timestamp("2026-10-31")
SEED = 731
DEPARTMENTS = ["Operations", "Client Services", "Risk & Compliance", "Technology", "Corporate"]
OWNERS = {
    "HR master": "People Systems", "Payroll": "Payroll Control",
    "Absence": "People Operations", "Working time": "People Operations",
    "Visa": "Immigration Coordinator", "PIP / ER": "People Operations",
}


def employee_key(value):
    return re.sub(r"\s+", "", str(value)).upper().strip()


def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def make_sources():
    rng = np.random.default_rng(SEED)
    employees = []
    for index in range(1, 361):
        department = DEPARTMENTS[(index - 1) % 5]
        salary = float(rng.integers(380, 990) * 100)
        fte = float(rng.choice([0.6, 0.8, 1.0], p=[0.07, 0.13, 0.8]))
        employees.append({
            "employee_id": f"EMP{index:04d}", "department": department,
            "annual_salary_eur": salary, "fte": fte,
            "start_date": f"{2020 + index % 5}-01-01",
            "end_date": "2026-09-30" if index > 350 else "",
            "contract": "Permanent" if index % 7 else "Fixed term",
        })
    roster = pd.DataFrame(employees)
    hr = roster.copy().astype(object)
    for index in range(0, 360, 13):
        hr.at[index, "employee_id"] = f" {hr.at[index, 'employee_id'].lower()} "
    for index in range(0, 360, 17):
        hr.at[index, "department"] = "ops " if index % 5 == 0 else str(hr.at[index, "department"]) + " "
    hr.at[6, "annual_salary_eur"] = ""
    hr.at[19, "department"] = ""
    hr.at[29, "start_date"] = "31/02/2026"
    hr.at[40, "fte"] = "1.8"
    hr.at[27, "start_date"] = "2026-11-15"
    hr.at[14, "fte"] = str(hr.at[14, "fte"]).replace(".", ",")
    duplicates = hr.iloc[[11, 45, 87]].copy()
    conflict = hr.iloc[[59]].copy()
    conflict["annual_salary_eur"] = float(conflict.iloc[0]["annual_salary_eur"]) + 5000
    hr = pd.concat([hr, duplicates, conflict], ignore_index=True)
    hr.insert(0, "source_row", [f"HR-{i:04d}" for i in range(1, len(hr) + 1)])

    events = pd.DataFrame([
        {"approval_id": "APR-018", "employee_id": "EMP0018", "kind": "Salary",
         "effective_date": "2026-10-01", "amount_eur": roster.iloc[17]["annual_salary_eur"] * 1.08, "status": "Approved"},
        {"approval_id": "APR-044", "employee_id": "EMP0044", "kind": "Salary",
         "effective_date": "2026-10-01", "amount_eur": roster.iloc[43]["annual_salary_eur"] * 1.08, "status": "Approved"},
        {"approval_id": "APR-055", "employee_id": "EMP0055", "kind": "Variable",
         "effective_date": "2026-10-01", "amount_eur": 420.0, "status": "Approved"},
    ] + [
        {"approval_id": f"ALW-{i:03d}", "employee_id": f"EMP{i:04d}", "kind": "Allowance",
         "effective_date": "2026-10-01", "amount_eur": 120.0, "status": "Approved"}
        for i in range(1, 21)
    ])
    payroll = []
    for row in employees[:350]:
        index = int(row["employee_id"][3:])
        salary = row["annual_salary_eur"]
        if index == 44:
            salary *= 1.08
        base = round(salary * row["fte"] / 12, 2)
        allowance = 120.0 if index <= 20 else 0.0
        variable = 420.0 if index == 55 else 0.0
        if index == 5:
            base += 2000.0
        if index == 11:
            allowance += 250.0
        payroll.append({
            "employee_id": "E033" if index == 33 else row["employee_id"],
            "period": "2026-10", "payment_ref": f"PAY-{index:04d}",
            "base_eur": base, "allowance_eur": allowance, "variable_eur": variable,
            "gross_eur": round(base + allowance + variable, 2),
        })
    pay = pd.DataFrame(payroll).astype(object)
    pay = pay[pay["employee_id"].ne("EMP0099")]
    pay.loc[pay["employee_id"].eq("EMP0024"), "gross_eur"] = "not supplied"
    extra = pd.DataFrame([{
        "employee_id": "EMP0355", "period": "2026-10", "payment_ref": "PAY-0355",
        "base_eur": 3500.0, "allowance_eur": 0.0, "variable_eur": 0.0, "gross_eur": 3500.0,
    }])
    pay = pd.concat([pay, extra, pay[pay["employee_id"].isin(["EMP0080", "EMP0081"])]], ignore_index=True)
    conflict = pay[pay["employee_id"].eq("EMP0101")].copy()
    conflict["gross_eur"] = float(conflict.iloc[0]["gross_eur"]) + 200
    pay = pd.concat([pay, conflict], ignore_index=True)
    pay.insert(0, "source_row", [f"PR-{i:04d}" for i in range(1, len(pay) + 1)])

    absence_rows = []
    for index in range(80):
        emp = employees[int(rng.integers(0, 350))]["employee_id"]
        start = pd.Timestamp("2026-07-01") + pd.Timedelta(days=int(rng.integers(0, 119)))
        end = min(start + pd.Timedelta(days=int(rng.integers(0, 10))), AS_OF)
        absence_rows.append({
            "episode_id": f"ABS-{index + 1:03d}", "employee_id": emp,
            "start_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d"),
            "type": "Sickness", "owner": "People Operations",
        })
    absence = pd.DataFrame(absence_rows)
    overlap = absence.iloc[[0]].copy()
    overlap["episode_id"] = "ABS-081"
    overlap["end_date"] = (
        pd.Timestamp(overlap.iloc[0]["end_date"]) + pd.Timedelta(days=3)
    ).strftime("%Y-%m-%d")
    bad = pd.DataFrame([
        {"episode_id": "ABS-082", "employee_id": "EMP0050", "start_date": "2026-10-20",
         "end_date": "2026-10-01", "type": "Sickness", "owner": ""},
        {"episode_id": "ABS-083", "employee_id": "EMP9999", "start_date": "2026-10-01",
         "end_date": "2026-10-03", "type": "Sickness", "owner": "People Operations"},
    ])
    absence = pd.concat([absence, absence.iloc[[4, 8, 12, 16]], overlap, bad], ignore_index=True)

    time_rows = []
    dates = pd.bdate_range("2026-07-06", "2026-10-30")
    true_absence = {}
    for row in absence_rows:
        true_absence.setdefault(row["employee_id"], set()).update(
            pd.bdate_range(row["start_date"], row["end_date"])
        )
    for row in employees[:350]:
        index = int(row["employee_id"][3:])
        for day in dates:
            week = day.to_period("W-SUN").start_time
            if index == 103 and week == pd.Timestamp("2026-08-10"):
                continue
            hours = round(7.5 * row["fte"], 2)
            if 100 <= index <= 107:
                hours = 11.0
            if index == 150 and week == pd.Timestamp("2026-10-19"):
                hours = 12.0
            if day in true_absence.get(row["employee_id"], set()):
                hours = 0.0
            start = day + pd.Timedelta(hours=9)
            breaks = 30 if hours > 6 else 15 if hours > 4.5 else 0
            if index == 175 and day == pd.Timestamp("2026-10-15"):
                hours, breaks = 7.5, 15
            if index == 170 and day == pd.Timestamp("2026-10-20"):
                hours, breaks = 13.5, 30
            if index == 170 and day == pd.Timestamp("2026-10-21"):
                start = day + pd.Timedelta(hours=7)
            finish = start + pd.Timedelta(hours=hours, minutes=breaks)
            time_rows.append({
                "employee_id": row["employee_id"], "date": day.strftime("%Y-%m-%d"),
                "week": week.strftime("%Y-%m-%d"), "worked_hours": hours,
                "break_minutes": breaks,
                "shift_start": start.isoformat() if hours else "",
                "shift_end": finish.isoformat() if hours else "",
            })
    time = pd.DataFrame(time_rows)

    visas = pd.DataFrame([
        {"case_id": f"VISA-{index + 1:03d}", "employee_id": f"EMP{index + 200:04d}",
         "permission": "Fictional permission record",
         "expiry_date": (AS_OF + pd.Timedelta(days=days)).strftime("%Y-%m-%d"),
         "status": "Submitted" if index % 4 == 0 else "Not started",
         "owner": "" if index == 8 else "Immigration Coordinator",
         "evidence": "Pending" if index % 3 == 0 else "Recorded",
         "provider": "Demo external provider"}
        for index, days in enumerate([-15, -2, 0, 7, 15, 25, 35, 45, 60, 70, 80, 90, 100, 110,
                                      120, 130, 140, 150, 180, 200, 220, 240, 270, 300, 330, 365])
    ])
    cases = pd.DataFrame([
        {"case_id": f"CASE-{index + 1:03d}", "employee_id": f"EMP{index + 120:04d}",
         "case_type": "PIP review" if index < 18 else "ER triage",
         "opened_date": "2026-10-01",
         "next_review": (AS_OF + pd.Timedelta(days=index - 8)).strftime("%Y-%m-%d"),
         "status": "Open", "owner": "" if index in [3, 22] else "People Operations",
         "documentation": "Missing" if index in [3, 7, 20] else "Complete"}
        for index in range(30)
    ])
    return {
        "hr_raw": hr, "payroll_raw": pay, "approvals": events,
        "absence_raw": absence, "time_raw": time, "visa_raw": visas, "cases_raw": cases,
        "fixture_roster": roster,
    }


def resolve_duplicates(frame, key, fields):
    keep, conflicts, duplicate_count = [], [], 0
    for value, group in frame.groupby(key, sort=True):
        payloads = group[fields].fillna("<missing>").astype(str).drop_duplicates()
        if len(payloads) > 1:
            conflicts.append((value, group))
        else:
            keep.append(group.iloc[0])
            duplicate_count += len(group) - 1
    clean = pd.DataFrame(keep).reset_index(drop=True)
    return clean, conflicts, duplicate_count


def analyse(sources):
    exceptions = []

    def issue(area, employee, code, detail, evidence, action, severity="Review", amount=None):
        exceptions.append({
            "exception_id": f"EX-{len(exceptions) + 1:03d}", "area": area,
            "employee_id": employee, "code": code, "severity": severity,
            "detail": detail, "evidence": evidence, "action": action,
            "owner": OWNERS[area], "status": "Open / demonstration",
            "amount_eur": amount,
        })

    hr = sources["hr_raw"].copy()
    hr["employee_id"] = hr["employee_id"].map(employee_key)
    hr["department"] = hr["department"].str.strip().replace({"ops": "Operations"})
    for column in ["annual_salary_eur", "fte"]:
        hr[column] = pd.to_numeric(hr[column].astype(str).str.replace(",", "."), errors="coerce")
    supplied_end = hr["end_date"].fillna("").astype(str).str.strip().ne("")
    for column in ["start_date", "end_date"]:
        hr[column] = pd.to_datetime(hr[column], format="%Y-%m-%d", errors="coerce")
    hr["invalid_end"] = supplied_end & hr["end_date"].isna()
    payload = ["department", "annual_salary_eur", "fte", "start_date", "end_date", "contract", "invalid_end"]
    master, hr_conflicts, hr_dupes = resolve_duplicates(hr, "employee_id", payload)
    for employee, group in hr_conflicts:
        issue("HR master", employee, "Conflicting master", "Two different salary records share one employee key.",
              ", ".join(group["source_row"]), "Quarantine both; ask People Systems to confirm the authoritative effective-dated record.")
    valid = (
        master["department"].isin(DEPARTMENTS)
        & master["annual_salary_eur"].gt(0) & master["fte"].between(0.01, 1)
        & master["start_date"].notna()
        & ~master["invalid_end"]
        & (master["end_date"].isna() | master["end_date"].ge(master["start_date"]))
    )
    for _, row in master[~valid].iterrows():
        failed = [name for name, bad in [
            ("department", row["department"] not in DEPARTMENTS),
            ("salary", pd.isna(row["annual_salary_eur"]) or row["annual_salary_eur"] <= 0),
            ("FTE", not 0 < row["fte"] <= 1),
            ("hire date", pd.isna(row["start_date"])),
            ("end date", row["invalid_end"] or (pd.notna(row["end_date"]) and row["end_date"] < row["start_date"])),
        ] if bad]
        issue("HR master", row["employee_id"], "Critical field", f"Unusable {', '.join(failed)}.",
              row["source_row"], "Obtain a verified source correction for the critical employment fields.")
    clean = master[valid].drop(columns="invalid_end").copy()
    clean["active"] = clean["start_date"].le(AS_OF) & (clean["end_date"].isna() | clean["end_date"].ge(AS_OF))
    active = clean[clean["active"]].copy()

    pay = sources["payroll_raw"].copy()
    pay["employee_id"] = pay["employee_id"].map(employee_key)
    for column in ["base_eur", "allowance_eur", "variable_eur", "gross_eur"]:
        pay[column] = pd.to_numeric(pay[column], errors="coerce")
    payroll, pay_conflicts, pay_dupes = resolve_duplicates(
        pay, "employee_id",
        ["period", "payment_ref", "base_eur", "allowance_eur", "variable_eur", "gross_eur"],
    )
    for employee, group in pay_conflicts:
        issue("Payroll", employee, "Conflicting payment", "Conflicting gross amounts share a payment identity.",
              ", ".join(group["source_row"]), "Hold the payment group; validate the payment register and approval trail.", "High")
    invalid_key = ~payroll["employee_id"].str.fullmatch(r"EMP\d{4}")
    for _, row in payroll[invalid_key].iterrows():
        issue("Payroll", row["employee_id"], "Unmapped key", "Payroll key does not match the HR identifier contract.",
              f"{row['source_row']} / {row['payment_ref']}",
              "Confirm an exact cross-system employee-key mapping with the source owner.")
    payroll = payroll[~invalid_key].copy()
    for _, row in payroll[payroll["gross_eur"].isna()].iterrows():
        issue("Payroll", row["employee_id"], "Missing gross", "Gross pay cannot be parsed.",
              row["source_row"], "Request a corrected payroll export and retain the amount as unknown pending verification.", "High")

    approvals = sources["approvals"].copy()
    approvals["effective_date"] = pd.to_datetime(approvals["effective_date"])
    approvals = approvals[approvals["status"].eq("Approved") & approvals["effective_date"].le(AS_OF)]
    salary_events = approvals[approvals["kind"].eq("Salary")].set_index("employee_id")["amount_eur"]
    allowances = approvals[approvals["kind"].eq("Allowance")].groupby("employee_id")["amount_eur"].sum()
    variable = approvals[approvals["kind"].eq("Variable")].groupby("employee_id")["amount_eur"].sum()
    active["approved_salary_eur"] = active["employee_id"].map(salary_events).fillna(active["annual_salary_eur"])
    active["expected_base_eur"] = (active["approved_salary_eur"] * active["fte"] / 12).round(2)
    active["expected_allowance_eur"] = active["employee_id"].map(allowances).fillna(0)
    active["expected_variable_eur"] = active["employee_id"].map(variable).fillna(0)
    active["expected_gross_eur"] = active[
        ["expected_base_eur", "expected_allowance_eur", "expected_variable_eur"]
    ].sum(axis=1).round(2)
    recon = active.merge(
        payroll[["employee_id", "gross_eur", "base_eur", "allowance_eur", "variable_eur", "payment_ref"]],
        on="employee_id", how="left", validate="one_to_one", indicator=True,
    )
    recon["delta_eur"] = (recon["gross_eur"] - recon["expected_gross_eur"]).round(2)
    recon["result"] = np.select(
        [recon["_merge"].eq("left_only"), recon["gross_eur"].isna(), recon["delta_eur"].abs().gt(0.02)],
        ["Missing / quarantined payment", "Unknown gross", "Amount exception"], default="Reconciled",
    )
    for _, row in recon[recon["result"].eq("Missing / quarantined payment")].iterrows():
        issue("Payroll", row["employee_id"], "Unmatched employee",
              "An active, validated HR employee has no resolved payroll match.",
              row["source_row"], "Trace absence to a missing export, rejected key or quarantined payment; verify before payroll sign-off.")
    for _, row in recon[recon["result"].eq("Amount exception")].iterrows():
        code = "Stale salary" if row["employee_id"] == "EMP0018" else "Allowance mismatch" if row["employee_id"] == "EMP0011" else "Unapproved movement"
        evidence = f"{row['payment_ref']}; expected EUR {row['expected_gross_eur']:.2f}; received EUR {row['gross_eur']:.2f}"
        if row["employee_id"] == "EMP0018":
            evidence += "; APR-018 approved salary effective 2026-10-01"
        issue("Payroll", row["employee_id"], code,
              "Regular gross differs from the effective-dated approved components.", evidence,
              "Check salary, FTE and component approvals; agree and document the correction with Payroll.", "High",
              float(row["delta_eur"]))
    active_ids = set(active["employee_id"])
    clean_ids = set(clean["employee_id"])
    for _, row in payroll[~payroll["employee_id"].isin(active_ids)].iterrows():
        if row["employee_id"] in clean_ids:
            code = "Inactive recurring payment"
            detail = "Regular pay appears for a leaver or not-yet-started employee."
        else:
            code = "Unvalidated HR reference"
            detail = "Payroll refers to a quarantined or invalid HR master record."
        issue("Payroll", row["employee_id"], code, detail, row["payment_ref"],
              "Verify employment dates, payment authority and any approved settlement or proration with Payroll.", "High")

    abs_raw = sources["absence_raw"].copy()
    abs_clean = abs_raw.drop_duplicates("episode_id").copy()
    abs_dupes = len(abs_raw) - len(abs_clean)
    for column in ["start_date", "end_date"]:
        abs_clean[column] = pd.to_datetime(abs_clean[column], errors="coerce")
    abs_valid = abs_clean["start_date"].notna() & abs_clean["end_date"].ge(abs_clean["start_date"]) & abs_clean["employee_id"].isin(clean_ids)
    for _, row in abs_clean[~abs_valid].iterrows():
        issue("Absence", row["employee_id"], "Invalid episode",
              "Invalid date range or unresolved HR reference.", row["episode_id"],
              "Correct the episode or reconcile its employee key before publishing absence rates.")
    abs_clean = abs_clean[abs_valid].copy()
    day_sets = {}
    naive_days = 0
    overlap_days = 0
    for _, row in abs_clean.sort_values(["employee_id", "start_date"]).iterrows():
        employment = clean.set_index("employee_id").loc[row["employee_id"]]
        start = max(row["start_date"], pd.Timestamp("2026-07-01"), employment["start_date"])
        end = min(row["end_date"], AS_OF, employment["end_date"] if pd.notna(employment["end_date"]) else AS_OF)
        days = set(pd.bdate_range(start, end)) if end >= start else set()
        naive_days += len(days)
        existing = day_sets.setdefault(row["employee_id"], set())
        overlap = existing & days
        if overlap:
            overlap_days += len(overlap)
            issue("Absence", row["employee_id"], "Overlapping absence",
                  f"{len(overlap)} scheduled day(s) appear in more than one episode.", row["episode_id"],
                  "Review the overlapping episodes; count each scheduled lost day once.")
        existing.update(days)
    absence_months = []
    for month in ["2026-07", "2026-08", "2026-09", "2026-10"]:
        month_start = pd.Timestamp(month + "-01")
        month_end = min(month_start + pd.offsets.MonthEnd(0), AS_OF)
        for department in DEPARTMENTS:
            scheduled, lost = 0.0, 0.0
            for _, row in clean[clean["department"].eq(department)].iterrows():
                start = max(row["start_date"], month_start)
                end = min(row["end_date"] if pd.notna(row["end_date"]) else month_end, month_end)
                days = set(pd.bdate_range(start, end)) if end >= start else set()
                scheduled += len(days) * 7.5 * row["fte"]
                lost += len(days & day_sets.get(row["employee_id"], set())) * 7.5 * row["fte"]
            absence_months.append({
                "month": month, "department": department,
                "scheduled_hours": round(scheduled, 2), "lost_hours": round(lost, 2),
                "rate_pct": round(lost / scheduled * 100, 3) if scheduled else None,
            })
    absence_summary = pd.DataFrame(absence_months)

    time = sources["time_raw"].copy()
    conflicts = time[time["worked_hours"].gt(0)].copy()
    conflicts["date_parsed"] = pd.to_datetime(conflicts["date"])
    conflicts = conflicts[
        conflicts.apply(lambda row: row["date_parsed"] in day_sets.get(row["employee_id"], set()), axis=1)
    ]
    for employee, group in conflicts.groupby("employee_id"):
        issue("Absence", employee, "Absence / time conflict",
              "A scheduled sickness day also has recorded worked hours.",
              ", ".join(group["date"]), "Reconcile the absence episode and time record with the source owners; preserve the original evidence.")
    weekly = time.groupby(["employee_id", "week"], as_index=False).agg(
        worked_hours=("worked_hours", "sum"), days_reported=("date", "count")
    )
    time_summary = weekly[weekly["employee_id"].isin(active_ids)].groupby("employee_id", as_index=False).agg(
        weeks=("week", "count"), average_hours=("worked_hours", "mean"),
        peak_hours=("worked_hours", "max"), complete_weeks=("days_reported", lambda series: int(series.eq(5).sum())),
    )
    time_summary = active[["employee_id", "department"]].merge(time_summary, how="left", validate="one_to_one")
    for column in ["weeks", "complete_weeks"]:
        time_summary[column] = time_summary[column].fillna(0).astype(int)
    time_summary["result"] = np.select(
        [time_summary["complete_weeks"].ne(17), time_summary["average_hours"].gt(48)],
        ["Incomplete / review", "Above 48h / review"], default="Below screen",
    )
    for _, row in time_summary[time_summary["result"].ne("Below screen")].iterrows():
        issue("Working time", row["employee_id"], row["result"],
              f"{row['complete_weeks']} complete weeks; observed mean " +
              (f"{row['average_hours']:.2f} hours." if pd.notna(row["average_hours"]) else "unknown."),
              "Daily time records, 2026-07-06 to 2026-10-30",
              "Review actual hours, the statutory reference period and leave adjustments with HR/legal. The current operational window covers 17 weeks.")
    shifts = time[time["worked_hours"].gt(0)].copy()
    shifts["shift_start"] = pd.to_datetime(shifts["shift_start"])
    shifts["shift_end"] = pd.to_datetime(shifts["shift_end"])
    shifts = shifts.sort_values(["employee_id", "shift_start"])
    shifts["previous_end"] = shifts.groupby("employee_id")["shift_end"].shift()
    shifts["rest_hours"] = (shifts["shift_start"] - shifts["previous_end"]).dt.total_seconds() / 3600
    rest = shifts[shifts["rest_hours"].lt(11) & shifts["employee_id"].isin(active_ids)]
    for employee, group in rest.groupby("employee_id"):
        issue("Working time", employee, "Daily rest review",
              f"Minimum logged interval {group['rest_hours'].min():.1f}h, below the general 11h daily-rest rule.",
              ", ".join(group["date"]), "Validate shift timestamps, exemptions and compensatory rest; escalate to the HR/legal owner.")
    minimum_break = np.select([shifts["worked_hours"].gt(6), shifts["worked_hours"].gt(4.5)], [30, 15], default=0)
    breaks = shifts[shifts["break_minutes"].lt(minimum_break) & shifts["employee_id"].isin(active_ids)]
    for employee, group in breaks.groupby("employee_id"):
        issue("Working time", employee, "Break record review",
              "Logged break minutes are below the general total-duration screen.",
              ", ".join(group["date"]), "Verify both break timing and duration against the applicable entitlements.")

    visa = sources["visa_raw"].copy()
    visa["expiry_date"] = pd.to_datetime(visa["expiry_date"])
    visa["days_remaining"] = (visa["expiry_date"] - AS_OF).dt.days
    visa["action_by"] = visa["expiry_date"] - pd.Timedelta(days=90)
    visa["result"] = np.select(
        [visa["days_remaining"].lt(0), visa["days_remaining"].le(30), visa["days_remaining"].le(90)],
        ["Expired / verify", "0-30 days", "31-90 days"], default="Over 90 days",
    )
    for _, row in visa[visa["days_remaining"].le(90) | visa["owner"].eq("")].iterrows():
        issue("Visa", row["employee_id"], "Renewal follow-up", f"{row['days_remaining']} days to recorded expiry; {row['status']}.",
              row["case_id"], "Verify permission and renewal evidence with an authorised provider. Apply the 90-day operational service horizon for follow-up.")
    cases = sources["cases_raw"].copy()
    cases["next_review"] = pd.to_datetime(cases["next_review"])
    cases["days_overdue"] = (AS_OF - cases["next_review"]).dt.days.clip(lower=0)
    cases["result"] = np.where(
        cases["days_overdue"].gt(0) | cases["owner"].eq("") | cases["documentation"].eq("Missing"),
        "Governance follow-up", "Scheduled",
    )
    for _, row in cases[cases["result"].eq("Governance follow-up")].iterrows():
        issue("PIP / ER", row["employee_id"], "Case governance",
              f"{row['case_type']}: {row['days_overdue']} day(s) overdue; documentation {row['documentation']}; owner {'missing' if not row['owner'] else 'assigned'}.",
              row["case_id"], "Assign an owner and review date, complete documentation and refer substantive ER decisions to the qualified HR specialist.")

    comparable = recon[recon["gross_eur"].notna()]
    amount_exceptions = recon[recon["result"].eq("Amount exception")]
    exception_frame = pd.DataFrame(exceptions)
    qa = {
        "seed": SEED, "as_of": AS_OF.strftime("%Y-%m-%d"),
        "fixture_people": 360, "hr_raw_rows": len(hr), "hr_unique_keys": hr["employee_id"].nunique(),
        "hr_exact_duplicates_removed": hr_dupes, "hr_conflicting_keys": len(hr_conflicts),
        "hr_critical_records_excluded": int((~valid).sum()), "hr_valid_records": len(clean),
        "active_headcount": len(active), "active_fte": round(float(active["fte"].sum()), 2),
        "payroll_raw_rows": len(pay), "payroll_exact_duplicates_removed": pay_dupes,
        "payroll_conflicting_keys": len(pay_conflicts), "payroll_resolved_rows": len(payroll),
        "reconciled_employees": int(recon["result"].eq("Reconciled").sum()),
        "payroll_amount_exceptions": len(amount_exceptions),
        "comparable_payroll_rows": len(comparable),
        "expected_comparable_eur": round(float(comparable["expected_gross_eur"].sum()), 2),
        "actual_comparable_eur": round(float(comparable["gross_eur"].sum()), 2),
        "signed_payroll_delta_eur": round(float(comparable["delta_eur"].sum()), 2),
        "absolute_payroll_delta_eur": round(float(comparable["delta_eur"].abs().sum()), 2),
        "absence_raw_rows": len(abs_raw), "absence_exact_duplicates_removed": abs_dupes,
        "absence_valid_episodes": len(abs_clean), "absence_naive_valid_days": naive_days,
        "absence_unique_days": sum(len(days) for days in day_sets.values()),
        "absence_overlap_days_removed": overlap_days,
        "absence_rate_pct": round(float(absence_summary["lost_hours"].sum() / absence_summary["scheduled_hours"].sum() * 100), 3),
        "working_time_daily_rows": len(time),
        "time_above_screen": int(time_summary["result"].eq("Above 48h / review").sum()),
        "time_incomplete": int(time_summary["result"].eq("Incomplete / review").sum()),
        "visa_within_90_days": int(visa["days_remaining"].between(0, 90).sum()),
        "visa_expired_records": int(visa["days_remaining"].lt(0).sum()),
        "case_followups": int(cases["result"].eq("Governance follow-up").sum()),
        "exceptions": len(exception_frame),
    }
    return {
        "hr_clean": clean, "active_hr": active, "payroll_clean": payroll,
        "reconciliation": recon.drop(columns="_merge"), "absence_clean": abs_clean,
        "absence_days": pd.DataFrame(
            [{"employee_id": employee, "date": day} for employee, days in day_sets.items() for day in sorted(days)]
        ),
        "absence_summary": absence_summary, "time_weekly": weekly,
        "time_summary": time_summary, "visa": visa, "cases": cases,
        "exceptions": exception_frame, "qa": qa,
    }


def run():
    public, provenance = load_public()
    sources = make_sources()
    result = analyse(sources)
    for folder in ["data/synthetic", "outputs", "outputs/tables", "outputs/plots"]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    for name, frame in sources.items():
        frame.to_csv(ROOT / "data" / "synthetic" / f"{name}.csv", index=False)
    for name, frame in result.items():
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(ROOT / "outputs" / "tables" / f"{name}.csv", index=False)
    (ROOT / "outputs" / "qa.json").write_text(json.dumps(result["qa"], indent=2), encoding="utf-8")
    print(json.dumps(result["qa"], indent=2))
    return public, provenance, sources, result


if __name__ == "__main__":
    run()
