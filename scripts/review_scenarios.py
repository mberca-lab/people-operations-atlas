"""Supplementary synthetic cases; the published baseline remains unchanged."""

import hashlib
from math import isfinite

import pandas as pd

from analysis import analyse, employee_key, records

TIME_SOURCE = "https://revisedacts.lawreform.ie/eli/1997/act/20/section/15/revised/en/html"


def prorated_pay(annual_salary, fte, hire_date, end_date, month):
    start = pd.Timestamp(month).normalize()
    if start.day != 1 or not isfinite(annual_salary) or annual_salary < 0 or not isfinite(fte) or not 0 < fte <= 1:
        raise ValueError("Use a month-start date, nonnegative salary and FTE in (0, 1].")
    hire = pd.Timestamp(hire_date)
    end = pd.Timestamp(end_date) if end_date else None
    if pd.isna(hire) or (end is not None and (pd.isna(end) or end < hire)):
        raise ValueError("Valid employment dates are required.")
    finish = start + pd.offsets.MonthEnd(0)
    days = max(0, ((min(finish, end) if end is not None else finish) - max(start, hire)).days + 1)
    return {"active_days": days, "month_days": finish.day,
            "monthly_base_eur": round(annual_salary * fte / 12, 2),
            "prorated_base_eur": round(annual_salary * fte / 12 * days / finish.day, 2)}


def absence_on_roster(roster, episodes, holidays, start, end):
    if len({row["employee_id"] for row in roster}) != len(roster):
        raise ValueError("Roster employee keys must be unique.")
    keys = {row["employee_id"] for row in roster}
    lost = {key: set() for key in keys}
    for episode in episodes:
        first, last = pd.Timestamp(episode["start_date"]), pd.Timestamp(episode["end_date"])
        if episode["employee_id"] not in keys or pd.isna(first) or pd.isna(last) or last < first:
            raise ValueError("Absence needs a resolved roster key and valid date interval.")
        lost[episode["employee_id"]].update(pd.date_range(first, last))
    closed = {pd.Timestamp(day) for day in holidays}
    days, summary = [], []
    for person in roster:
        if not 0 <= person["daily_hours"] <= 24 or not set(person["weekdays"]).issubset(range(7)):
            raise ValueError("Roster hours and weekday assignments must be valid.")
        employee_days = []
        for day in pd.date_range(start, end):
            active = day >= pd.Timestamp(person["hire_date"]) and (
                not person["end_date"] or day <= pd.Timestamp(person["end_date"]))
            planned = person["daily_hours"] if active and day.weekday() in person["weekdays"] else 0
            scheduled = 0 if day in closed else planned
            row = {"employee_id": person["employee_id"], "date": day.strftime("%Y-%m-%d"),
                   "planned_hours": planned, "closed_day": int(day in closed),
                   "absence_day": int(day in lost[person["employee_id"]]),
                   "scheduled_hours": scheduled,
                   "lost_hours": scheduled if day in lost[person["employee_id"]] else 0}
            employee_days.append(row)
        days.extend(employee_days)
        planned = sum(row["planned_hours"] for row in employee_days)
        scheduled = sum(row["scheduled_hours"] for row in employee_days)
        lost_hours = sum(row["lost_hours"] for row in employee_days)
        summary.append({"employee_id": person["employee_id"], "roster": person["roster"],
                        "planned_hours": planned, "scheduled_hours": scheduled,
                        "lost_hours": lost_hours,
                        "rate_pct": round(lost_hours / scheduled * 100, 3) if scheduled else None})
    return days, summary


def calendar_time_review(frame, start, employees):
    first = pd.Timestamp(start)
    if first.day != 1:
        raise ValueError("This illustration starts on the first day of a calendar month.")
    last = first + pd.DateOffset(months=4) - pd.Timedelta(days=1)
    required = pd.date_range(first, last)
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data[data["date"].between(first, last)]
    if data.duplicated(["employee_id", "date"]).any():
        raise ValueError("Duplicate employee-day records require source resolution.")
    result = []
    for employee in employees:
        rows = data[data["employee_id"].eq(employee)].copy()
        hours = pd.to_numeric(rows["worked_hours"], errors="coerce")
        leave = rows["leave_kind"].isin(["Annual", "Sick"])
        valid = hours.map(isfinite).all() and hours.ge(0).all() and not (leave & hours.gt(0)).any()
        supported_leave = rows["leave_kind"].isin(["None", "Annual", "Sick"]).all()
        complete = len(rows) == len(required) and valid and supported_leave
        eligible = len(required) - int(leave.sum())
        average = float(hours.sum() / (eligible / 7)) if complete and eligible > 0 else None
        result.append({"employee_id": employee, "start_date": first.strftime("%Y-%m-%d"),
                       "end_date": last.strftime("%Y-%m-%d"), "required_days": len(required),
                       "reported_days": len(rows), "excluded_leave_days": int(leave.sum()),
                       "eligible_days": eligible, "worked_hours": float(hours.sum()),
                       "average_hours": average,
                       "result": "Incomplete / review" if average is None else
                       "Above 48h / review" if average > 48 else "Below screen"})
    return result


def make_review_pack(sources, baseline):
    before = baseline["reconciliation"].set_index("employee_id").loc["EMP0018"]
    corrected = {name: frame.copy(deep=True) for name, frame in sources.items()}
    mask = corrected["payroll_raw"]["employee_id"].map(employee_key).eq("EMP0018")
    if mask.sum() != 1:
        raise ValueError("The closure example requires one unambiguous payment.")
    for column, expectation in [("base_eur", "expected_base_eur"),
                                ("allowance_eur", "expected_allowance_eur"),
                                ("variable_eur", "expected_variable_eur"),
                                ("gross_eur", "expected_gross_eur")]:
        corrected["payroll_raw"].loc[mask, column] = before[expectation]
    after = analyse(corrected)
    resolved = after["reconciliation"].set_index("employee_id").loc["EMP0018"]
    approvals = sources["approvals"].query("employee_id == 'EMP0018' and kind == 'Salary' and status == 'Approved'")
    approvals = approvals[pd.to_datetime(approvals["effective_date"]).le(pd.Timestamp(baseline["qa"]["as_of"]))]
    if len(approvals) != 1:
        raise ValueError("Independent review requires one effective approved salary.")
    approval = approvals.iloc[0]
    independent = round(approval["amount_eur"] * before["fte"] / 12, 2) + before["expected_allowance_eur"] + before["expected_variable_eur"]
    if resolved["result"] != "Reconciled" or round(resolved["gross_eur"] - independent, 2) != 0:
        raise ValueError("Independent closure checks failed.")
    hash_payroll = lambda frame: hashlib.sha256(frame.to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()
    closure = {
        "case_id": "SIM-CLOSE-001", "employee_id": "EMP0018",
        "approval_id": approval["approval_id"], "effective_date": str(approval["effective_date"])[:10],
        "approved_salary_eur": float(approval["amount_eur"]), "fte": float(before["fte"]),
        "allowance_eur": float(before["expected_allowance_eur"]),
        "variable_eur": float(before["expected_variable_eur"]),
        "expected_gross_eur": float(before["expected_gross_eur"]),
        "original_gross_eur": float(before["gross_eur"]), "corrected_gross_eur": float(resolved["gross_eur"]),
        "original_delta_eur": float(before["delta_eur"]), "corrected_delta_eur": float(resolved["delta_eur"]),
        "before_qa": baseline["qa"], "after_qa": after["qa"],
        "original_payroll_sha256": hash_payroll(sources["payroll_raw"]),
        "corrected_payroll_sha256": hash_payroll(corrected["payroll_raw"]),
        "events": [
            {"stage": "1 / Evidence", "owner": "Payroll reviewer", "reference": "PAY-0018 + APR-018",
             "action": "Compare the recorded payment with the approved salary effective 1 October."},
            {"stage": "2 / Finding", "owner": "Compensation owner", "reference": "Synthetic source comparison",
             "action": "The payroll export retains the previous base salary. The approved increase is absent from that export."},
            {"stage": "3 / Correction", "owner": "Authorised payroll preparer", "reference": "SIM-CORR-001",
             "action": "Apply the approved base salary in a separate corrected extract; retain both versions."},
            {"stage": "4 / Verification", "owner": "Independent review role", "reference": "SIM-CHECK-001",
             "action": "Re-run the full controls and independently calculate salary / 12 x FTE plus approved components."},
            {"stage": "5 / Closure", "owner": "Accountable control owner", "reference": "SIM-SIGNOFF-001",
             "action": "Record a zero residual variance and simulated sign-off. Add an effective-date approval-to-payroll check."},
        ],
    }
    pay = []
    for employee, scenario, annual, fte, hire, end in [
        ("JOIN-01", "Mid-month starter", 72000, 1, "2026-10-12", None),
        ("LEAVE-01", "Mid-month leaver", 57600, 1, "2025-01-01", "2026-10-20"),
        ("PART-01", "Part-time full month", 48000, 0.6, "2025-01-01", None),
    ]:
        pay.append({"employee_id": employee, "scenario": scenario, "annual_salary_eur": annual,
                    "fte": fte, "hire_date": hire, "end_date": end, "month": "2026-10-01",
                    **prorated_pay(annual, fte, hire, end, "2026-10-01")})
    roster = [
        {"employee_id": "ROSTER-01", "roster": "Mon-Fri / 7.5 hours", "weekdays": [0, 1, 2, 3, 4],
         "daily_hours": 7.5, "hire_date": "2026-10-01", "end_date": None},
        {"employee_id": "ROSTER-02", "roster": "Mon-Wed / 7.5 hours", "weekdays": [0, 1, 2],
         "daily_hours": 7.5, "hire_date": "2026-10-05", "end_date": "2026-10-28"},
    ]
    episodes = [
        {"employee_id": "ROSTER-01", "start_date": "2026-10-23", "end_date": "2026-10-27"},
        {"employee_id": "ROSTER-01", "start_date": "2026-10-27", "end_date": "2026-10-28"},
        {"employee_id": "ROSTER-02", "start_date": "2026-10-25", "end_date": "2026-10-28"},
    ]
    roster_days, roster_summary = absence_on_roster(roster, episodes, ["2026-10-26"], "2026-10-01", "2026-10-31")
    time_days = []
    for employee, daily in [("TIME-01", 10), ("TIME-02", 7.5), ("TIME-03", 7.5)]:
        for day in pd.date_range("2026-07-01", "2026-10-31"):
            if employee == "TIME-03" and day == pd.Timestamp("2026-10-31"):
                continue
            leave = employee == "TIME-02" and pd.Timestamp("2026-08-10") <= day <= pd.Timestamp("2026-08-14")
            time_days.append({"employee_id": employee, "date": day.strftime("%Y-%m-%d"),
                              "worked_hours": 0 if leave or day.weekday() >= 5 else daily,
                              "leave_kind": "Annual" if leave else "None"})
    return {"closure": closure, "corrected_payroll": records(corrected["payroll_raw"]),
            "proration": pay, "roster_inputs": roster, "absence_episodes": episodes,
            "closed_dates": ["2026-10-26"], "roster_days": roster_days, "roster_summary": roster_summary,
            "calendar_days": time_days,
            "calendar_summary": calendar_time_review(pd.DataFrame(time_days), "2026-07-01", ["TIME-01", "TIME-02", "TIME-03"]),
            "time_source": TIME_SOURCE,
            "scope": "Separate synthetic scenarios. Calendar-day base-pay proration and office closure are demonstration policies. The four-month time illustration excludes tagged annual/sick leave days; other statutory exclusions and applicability require HR/legal review."}
