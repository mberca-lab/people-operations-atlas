"""Build editable control formulas, then calculate and create genuine pivots in Excel."""

import json
from datetime import datetime
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.workbook.properties import CalcProperties

from analysis import AS_OF, DEPARTMENTS
from sources import ROOT

TARGET = ROOT / "outputs" / "People_Operations_Control_Workbook.xlsx"
ROSE = "B11F4B"


def value(item):
    if item is None or (not isinstance(item, str) and pd.isna(item)):
        return None
    if isinstance(item, pd.Timestamp):
        return item.to_pydatetime()
    if isinstance(item, np.generic):
        return item.item()
    return item


def write_sheet(workbook, name, headers, rows):
    sheet = workbook.create_sheet(name)
    sheet.append(headers)
    for row in rows:
        sheet.append([value(item) for item in row])
    sheet.freeze_panes = "B2"
    sheet.sheet_view.showGridLines = False
    sheet.row_dimensions[1].height = 36
    for cell in sheet[1]:
        cell.font = Font(name="Aptos", bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill("solid", fgColor=ROSE)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Aptos", size=10, color="242424")
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if isinstance(cell.value, datetime):
                cell.number_format = "yyyy-mm-dd"
    for index, header in enumerate(headers, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = min(46, max(16, len(header) + 2))
    if len(rows):
        table = Table(displayName=name.replace(" ", "").replace("/", "") + "Data", ref=sheet.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)
    sheet.print_options.horizontalCentered = True
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = "1:1"
    return sheet


def add_frame(workbook, name, frame):
    return write_sheet(workbook, name, list(frame), frame.values.tolist())


def range_ref(sheet, column, count):
    return f"'{sheet}'!${column}$2:${column}${count + 1}"


def build(public, sources, result):
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True)
    readme = write_sheet(workbook, "Read Me", ["Section", "Instructions / evidence boundary"], [
        ["People, in Balance", "An independent portfolio project tailored to People Data & Operations duties. No affiliation with Waystone."],
        ["Public data", "CSO EHQ03 official sector aggregates, CC BY 4.0; source URL and hash are in the Public Sources sheet."],
        ["Synthetic operations", "Every employee, payment, absence, visa and case record is fictional. Seed 731; as-of 2026-10-31."],
        ["How to review", "Start in Dashboard, inspect Reconciliation and Payroll Pivot, then investigate Exceptions with source references."],
        ["Editable calculations", "Change clean inputs or Parameters to explore formulas. Raw-to-clean identity resolution and roster membership require a Python rebuild; they are not automatically refreshed from raw sheets."],
        ["PivotTables", "Payroll Pivot and Case Pivot are genuine native Excel PivotTables. After changing inputs, use Data > Refresh All."],
        ["Salary assumptions", "EUR annual full-time salary / 12 x FTE, full calendar month, no mid-month starters in the approved active base. No tax, PRSI, pension, deductions or net-pay validation."],
        ["Approvals", "This fixture has at most one current approved salary event per employee and recurring allowance events with no expiry. Multiple salary events trigger review. Real implementation needs effective start/end intervals and payroll cutoff rules."],
        ["Identity controls", "Exact repeated payloads collapse once. Conflicting groups and invalid keys are quarantined; no first-row guessing or fuzzy identity matching."],
        ["Missing gross", "Missing/non-numeric pay remains unknown, never zero. Reconciliation uses a common comparable base."],
        ["Absence", "Rates use FTE-weighted scheduled hours, weekday calendars, employment dates and unioned lost dates. Public holidays and differing roster patterns are not implemented."],
        ["Working time", "17 complete weeks is a screening window, NOT the statutory four calendar months. Leave adjustments, exemptions, weekly rest and legal decisions are outside this demo."],
        ["Visa", "30/90-day alert windows are demonstration service levels, not immigration law. Fictional expiry is not a determination of permission to work."],
        ["Case data", "PIP/ER metadata only; no case narratives, health diagnoses, passport data or automated employment decisions."],
        ["Evidence boundary", "A workbook cannot establish five years of experience, real BambooHR expertise, live immigration administration or hands-on Power BI skills."],
        ["Source references", "CSO: https://data.gov.ie/dataset/ehq03-average-earnings-hours-worked-employment-and-labour-costs"],
        ["WRC guidance", "https://www.workplacerelations.ie/en/what_you_should_know/hours-and-wages/working_hours/"],
    ])
    readme.column_dimensions["B"].width = 110
    parameters = write_sheet(workbook, "Parameters", ["Parameter", "Value", "Meaning"], [
        ["Edition", "Synthetic lab", "Inputs below are analyst-set or fixture values, not company policy."],
        ["As of", AS_OF.to_pydatetime(), "Reporting cutoff; changing month requires rebuilding source extracts."],
        ["Pay tolerance EUR", 0.02, "Analyst-set rounding tolerance, not materiality approval."],
        ["Visa horizon days", 90, "Demonstration operational lead time, not a legal threshold."],
        ["Weekly hours screen", 48, "General WRC maximum average rule; this demo only screens a 17-week window."],
        ["Required complete weeks", 17, "Operational screen, not a substitute for four calendar months."],
        ["Window start", datetime(2026, 7, 6), "Daily time fixture start."],
        ["Window end", datetime(2026, 10, 30), "Daily time fixture end."],
        ["Full-time daily hours", 7.5, "Fictional Monday-Friday roster; no public-holiday adjustment."],
    ])
    parameters["B3"].number_format = "yyyy-mm-dd"
    for row in range(3, 11):
        parameters.cell(row, 2).font = Font(name="Aptos", size=10, color="0078D4")
        parameters.cell(row, 2).fill = PatternFill("solid", fgColor="FFF4CC")
    validation = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1=0)
    parameters.add_data_validation(validation)
    validation.add("B4:B7")

    add_frame(workbook, "HR Raw", sources["hr_raw"])
    master = result["hr_clean"][[
        "employee_id", "department", "annual_salary_eur", "fte", "start_date", "end_date", "contract", "source_row"
    ]].copy()
    master["Active Y N"] = [
        f'=IF(AND(E{r}<=Parameters!$B$3,OR(F{r}="",F{r}>=Parameters!$B$3)),"Y","N")'
        for r in range(2, len(master) + 2)
    ]
    add_frame(workbook, "HR Master", master)
    add_frame(workbook, "Payroll Raw", sources["payroll_raw"])
    payroll = result["payroll_clean"][[
        "employee_id", "period", "gross_eur", "base_eur", "allowance_eur", "variable_eur", "payment_ref", "source_row"
    ]].copy()
    payroll["gross_eur"] = payroll["gross_eur"].where(payroll["gross_eur"].notna(), "Unknown")
    add_frame(workbook, "Payroll Clean", payroll)
    events = sources["approvals"].copy()
    events["effective_date"] = pd.to_datetime(events["effective_date"])
    add_frame(workbook, "Approvals", events)

    n, p, a = len(master), len(payroll), len(events)
    hr_id, hr_department, hr_salary, hr_fte, hr_active = [
        range_ref("HR Master", column, n) for column in ["A", "B", "C", "D", "I"]
    ]
    pay_id, pay_gross = [range_ref("Payroll Clean", column, p) for column in ["A", "C"]]
    approval_emp, approval_kind, approval_date, approval_amount, approval_status = [
        range_ref("Approvals", column, a) for column in ["B", "C", "D", "E", "F"]
    ]
    recon_rows = []
    for row, employee in enumerate(master["employee_id"], start=2):
        criteria = f'{approval_emp},A{row},{approval_kind},"Salary",{approval_status},"Approved",{approval_date},"<="&Parameters!$B$3'
        count = f"COUNTIFS({criteria})"
        salary = f'SUMIFS({approval_amount},{criteria})'
        component = lambda kind: f'SUMIFS({approval_amount},{approval_emp},A{row},{approval_kind},"{kind}",{approval_status},"Approved",{approval_date},"<="&Parameters!$B$3)'
        recon_rows.append([
            employee,
            f'=IFERROR(XLOOKUP(A{row},{hr_id},{hr_department}),"Unmapped")',
            f'=XLOOKUP(A{row},{hr_id},{hr_active},"N")',
            f'=IF({count}>1,"Ambiguous",IF({count}=1,{salary},XLOOKUP(A{row},{hr_id},{hr_salary},"Missing")))',
            f'=XLOOKUP(A{row},{hr_id},{hr_fte},0)',
            f'=IF(AND(C{row}="Y",ISNUMBER(D{row})),ROUND(D{row}*E{row}/12,2),"")',
            f'={component("Allowance")}',
            f'={component("Variable")}',
            f'=IF(ISNUMBER(F{row}),ROUND(F{row}+G{row}+H{row},2),"")',
            f'=IF(COUNTIF({pay_id},A{row})=0,"Missing",IF(COUNTIF({pay_id},A{row})>1,"Ambiguous",XLOOKUP(A{row},{pay_id},{pay_gross},"Unknown")))',
            f'=IF(AND(ISNUMBER(I{row}),ISNUMBER(J{row})),ROUND(J{row}-I{row},2),"")',
            f'=IF(C{row}="N",IF(ISNUMBER(J{row}),"Lifecycle review","Not in scope"),IF(OR(D{row}="Ambiguous",J{row}="Ambiguous"),"Approval / key review",IF(J{row}="Missing","Missing payment",IF(J{row}="Unknown","Unknown gross",IF(ABS(K{row})>Parameters!$B$4,"Amount exception","Reconciled")))))',
            f'=IF(ISNUMBER(K{row}),ABS(K{row}),"")',
        ])
    reconciliation = write_sheet(workbook, "Reconciliation", [
        "employee_id", "department", "active", "approved_salary_eur", "fte",
        "expected_base_eur", "approved_allowance_eur", "approved_variable_eur",
        "expected_gross_eur", "actual_gross_eur", "delta_eur", "result", "absolute_delta_eur",
    ], recon_rows)
    reconciliation["D2"].comment = Comment(
        "One effective approved salary event is allowed in this fixture. Multiple events trigger Ambiguous; do not use a first-match salary.", "Portfolio")
    reconciliation["J2"].comment = Comment(
        "Payroll Clean stores nonnumeric gross as Unknown. Never convert a missing amount to zero.", "Portfolio")
    reconciliation.conditional_formatting.add(
        f"K2:K{n+1}", CellIsRule(operator="notBetween", formula=["-Parameters!$B$4", "Parameters!$B$4"],
                                fill=PatternFill("solid", fgColor="FCE3E8"))
    )
    for row in reconciliation.iter_rows(min_row=2):
        for cell in [row[index] for index in [3, 5, 6, 7, 8, 9, 10, 12]]:
            cell.number_format = '"EUR " #,##0.00;("EUR " #,##0.00);"-"'

    lookup_rows = []
    for row, employee in enumerate(list(master["employee_id"].head(8)) + ["EMP9999"], start=2):
        lookup_rows.append([
            employee, f'=IFERROR(XLOOKUP(A{row},{hr_id},{hr_salary}),"Not found")',
            f'=IFERROR(INDEX({hr_salary},MATCH(A{row},{hr_id},0)),"Not found")',
            f'=IFERROR(VLOOKUP(A{row},\'HR Master\'!$A$2:$I${n+1},3,FALSE),"Not found")',
            f'=IF(AND(B{row}=C{row},C{row}=D{row}),"Consistent","Investigate")',
        ])
    write_sheet(workbook, "Lookup Lab", ["employee_id", "XLOOKUP", "INDEX MATCH", "VLOOKUP exact", "Cross-check"], lookup_rows)

    exception_sheet = add_frame(workbook, "Exceptions", result["exceptions"])
    status_column = get_column_letter(list(result["exceptions"]).index("status") + 1)
    statuses = DataValidation(type="list", formula1='"Open / demonstration,Investigating,Resolved / simulated,Escalated"', allow_blank=False)
    exception_sheet.add_data_validation(statuses)
    statuses.add(f"{status_column}2:{status_column}{len(result['exceptions'])+1}")
    exception_sheet.column_dimensions["H"].width = 74
    exception_sheet.column_dimensions["G"].width = 64

    weekly = result["time_weekly"].copy()
    weekly["week"] = pd.to_datetime(weekly["week"])
    add_frame(workbook, "Time Weekly", weekly)
    t = len(weekly)
    week_emp, week_hours, week_days = [range_ref("Time Weekly", column, t) for column in ["A", "C", "D"]]
    time_rows = []
    for row, entry in enumerate(result["time_summary"].itertuples(), start=2):
        time_rows.append([
            entry.employee_id, entry.department,
            f'=COUNTIF({week_emp},A{row})',
            f'=COUNTIFS({week_emp},A{row},{week_days},5)',
            f'=IFERROR(AVERAGEIF({week_emp},A{row},{week_hours}),"Unknown")',
            f'=IF(D{row}<>Parameters!$B$7,"Incomplete / review",IF(E{row}>Parameters!$B$6,"Above screen / review","Below screen"))',
        ])
    write_sheet(workbook, "Time Review", ["employee_id", "department", "weeks", "complete_weeks", "average_hours", "result"], time_rows)

    add_frame(workbook, "Absence Raw", sources["absence_raw"])
    add_frame(workbook, "Absence Days", result["absence_days"])
    ad = len(result["absence_days"])
    absence_emp, absence_date = [range_ref("Absence Days", column, ad) for column in ["A", "B"]]
    calendar_rows = []
    for month in ["2026-07", "2026-08", "2026-09", "2026-10"]:
        start = pd.Timestamp(month + "-01")
        for _, person in master.iterrows():
            row = len(calendar_rows) + 2
            calendar_rows.append([
                person["employee_id"], person["department"], start.to_pydatetime(),
                person["start_date"], person["end_date"], person["fte"],
                f'=IF(MAX(D{row},C{row})>MIN(IF(E{row}="",EOMONTH(C{row},0),E{row}),EOMONTH(C{row},0)),0,NETWORKDAYS(MAX(D{row},C{row}),MIN(IF(E{row}="",EOMONTH(C{row},0),E{row}),EOMONTH(C{row},0))))',
                f'=G{row}*F{row}*Parameters!$B$10',
                f'=COUNTIFS({absence_emp},A{row},{absence_date},">="&C{row},{absence_date},"<="&EOMONTH(C{row},0))',
                f'=I{row}*F{row}*Parameters!$B$10',
            ])
    write_sheet(workbook, "Absence Exposure", [
        "employee_id", "department", "month", "hire_date", "end_date", "fte",
        "scheduled_days", "scheduled_hours", "lost_days", "lost_hours",
    ], calendar_rows)
    c = len(calendar_rows)
    calendar_dept, calendar_month, scheduled, lost = [
        range_ref("Absence Exposure", column, c) for column in ["B", "C", "H", "J"]
    ]
    summary_rows = []
    for month in ["2026-07", "2026-08", "2026-09", "2026-10"]:
        for department in DEPARTMENTS:
            row = len(summary_rows) + 2
            summary_rows.append([
                pd.Timestamp(month + "-01").to_pydatetime(), department,
                f'=SUMIFS({scheduled},{calendar_month},A{row},{calendar_dept},B{row})',
                f'=SUMIFS({lost},{calendar_month},A{row},{calendar_dept},B{row})',
                f'=IF(C{row}=0,"Unknown",D{row}/C{row})',
            ])
    absence_sheet = write_sheet(workbook, "Absence Summary", ["month", "department", "scheduled_hours", "lost_hours", "rate"], summary_rows)
    for row in range(2, 22):
        absence_sheet.cell(row, 5).number_format = "0.00%"

    visa_rows = []
    for row, entry in enumerate(result["visa"].itertuples(), start=2):
        visa_rows.append([
            entry.case_id, entry.employee_id, entry.expiry_date, entry.status,
            entry.owner, entry.evidence, f'=C{row}-Parameters!$B$3',
            f'=C{row}-Parameters!$B$5',
            f'=IF(G{row}<0,"Expired / verify",IF(G{row}>Parameters!$B$5,"Over horizon",IF(G{row}<=30,"0-30 days","31-"&Parameters!$B$5&" days")))',
        ])
    write_sheet(workbook, "Visa Tracker", [
        "case_id", "employee_id", "expiry_date", "renewal_status", "owner", "evidence",
        "days_remaining", "demo_action_by", "window",
    ], visa_rows)
    case_rows = []
    for row, entry in enumerate(result["cases"].itertuples(), start=2):
        case_rows.append([
            entry.case_id, entry.employee_id, entry.case_type, entry.next_review,
            entry.status, entry.owner, entry.documentation,
            f'=MAX(0,Parameters!$B$3-D{row})',
            f'=IF(OR(H{row}>0,F{row}="",G{row}="Missing"),"Governance follow-up","Scheduled")',
        ])
    write_sheet(workbook, "Case Tracker", [
        "case_id", "employee_id", "case_type", "next_review", "status", "owner",
        "documentation", "days_overdue", "result",
    ], case_rows)
    provenance = json.loads((ROOT / "data" / "public" / "provenance.json").read_text())
    write_sheet(workbook, "Public Sources", ["Field", "Value"], [
        [key, str(provenance[key])] for key in [
            "publisher", "dataset", "url", "retrieved_utc", "publisher_updated", "sha256",
            "license", "license_url", "methodology_url", "background_url", "selection",
        ]
    ])
    add_frame(workbook, "Public Context", public)
    mapping = write_sheet(workbook, "System Mapping", ["System / grain", "Key / field mapping", "Capture control / limitation"], [
        ["HR master / one resolved employee", "employee_id -> employeeNumber-style key; start_date -> hireDate-style field", "BambooHR-style design only, not a validated BambooHR import schema or API integration."],
        ["Employment history / effective interval", "employee_id + effective_start + effective_end", "Nonoverlapping intervals; hire/end dates; contractual status reconciled to approvals."],
        ["Compensation / approved event", "employee_id + kind + effective date + approval_id", "Exactly one active base-salary event; segregate approver and payroll preparer."],
        ["Payroll / employee-month-payment", "employee_id + period + payment_ref", "Duplicate/conflict guards, valid amounts, gross components and payroll cutoff."],
        ["Absence / episode and unioned date", "episode_id; employee_id + scheduled date", "Date validity, overlap union, roster exposure and worked-time cross-check."],
        ["Time / employee-date-shift", "employee_id + date + shift identity", "Actual worked time, break timing, coverage and leave adjustments; do not substitute paid-hours aggregates."],
        ["Visa / permission record", "case_id + employee_id + validity interval", "Authorised evidence/provider, expiry/renewal review, minimised sensitive documents."],
        ["Case / HR workflow", "case_id + owner + review date", "Restricted case access; metadata reporting only; substantive ER judgement remains human."],
        ["Power BI model / design only", "Employee snapshot, Date, Pay Components, Absence Days, Exposure, Time, Case facts", "Single-direction one-to-many dimensions; avoid double-counting employee records across facts. No Power BI file is delivered."],
    ])
    mapping.column_dimensions["C"].width = 100
    sop = write_sheet(workbook, "SOP", ["Stage", "Owner", "Control / output"], [
        ["01 Acquire", "People Systems", "Immutable dated extracts, source totals, schema/key contracts and restricted access."],
        ["02 Validate", "People Systems", "Typed fields, dates, reference keys, full-record duplicates and conflicting payloads."],
        ["03 Quarantine", "Source owner", "Retain original row references; critical missing/conflicting data is not silently repaired."],
        ["04 Reconcile", "Payroll Control", "Exact current-period joins, effective approvals, lifecycle dates and comparable amount base."],
        ["05 Investigate", "People Operations + Payroll", "Confirm the root cause against source evidence; seeded cases are demonstrations, not real investigation outcomes."],
        ["06 Correct", "Authorised source owner", "Approve a source-system correction; never change pay or employee status from an automated flag."],
        ["07 Verify", "Independent reviewer", "Rerun control, confirm source and payment evidence, retain before/after audit trail."],
        ["08 Close", "Accountable control owner", "Evidence, resolution date and reviewer recorded; exceptions in this fixture remain open demonstrations."],
        ["Absence follow-up", "People Operations", "Review metadata and overlaps privately; seek human HR judgement for sickness cases."],
        ["PIP / ER escalation", "HR case owner", "Check owner, next review and documentation; escalate substantive case questions rather than automate decisions."],
        ["Visa coordination", "Immigration Coordinator", "Confirm employee/provider evidence, renewal submission, expiry and closure criteria with qualified specialists."],
        ["Governance", "People Operations lead", "Review aging, recurrence and completeness; thresholds and proposed improvements need real operational approval."],
    ])
    sop.column_dimensions["C"].width = 110
    write_sheet(workbook, "Dashboard", ["Metric", "Value", "Denominator / definition"], [
        ["Validated active headcount", f'=COUNTIF({hr_active},"Y")', "As-of valid canonical HR records; not the full seeded roster."],
        ["Active FTE", f'=SUMIF({hr_active},"Y",{hr_fte})', "Contractual FTE for that same active base."],
        ["Reconciled employees", f'=COUNTIF(Reconciliation!L2:L{n+1},"Reconciled")', "Current valid employees with known matched gross within tolerance."],
        ["Amount exceptions", f'=COUNTIF(Reconciliation!L2:L{n+1},"Amount exception")', "Not a confirmed over/underpayment finding."],
        ["Comparable expected EUR", f'=SUMIF(Reconciliation!L2:L{n+1},"Reconciled",Reconciliation!I2:I{n+1})+SUMIF(Reconciliation!L2:L{n+1},"Amount exception",Reconciliation!I2:I{n+1})', "Known expected and actual gross for the same matched active rows."],
        ["Comparable actual EUR", f'=SUMIF(Reconciliation!L2:L{n+1},"Reconciled",Reconciliation!J2:J{n+1})+SUMIF(Reconciliation!L2:L{n+1},"Amount exception",Reconciliation!J2:J{n+1})', "Unknown, unmatched, inactive and invalid-master amounts excluded."],
        ["Signed discrepancy EUR", f'=SUM(Reconciliation!K2:K{n+1})', "Net signed difference; positive and negative amounts can offset."],
        ["Absolute discrepancy EUR", f'=SUM(Reconciliation!M2:M{n+1})', "Sum of absolute differences; distinct from net difference."],
        ["Absence rate", '=IF(SUM(\'Absence Summary\'!C2:C21)=0,"Unknown",SUM(\'Absence Summary\'!D2:D21)/SUM(\'Absence Summary\'!C2:C21))', "Lost / scheduled FTE-weighted hours, weekdays only."],
        ["Working time above screen", f'=COUNTIF(\'Time Review\'!F2:F{len(time_rows)+1},"Above screen / review")', "Only complete 17-week logs; not statutory compliance."],
        ["Working time incomplete", f'=COUNTIF(\'Time Review\'!F2:F{len(time_rows)+1},"Incomplete / review")', "Missing coverage remains a separate uncertainty."],
        ["Visa expiry within horizon", f'=COUNTIFS(\'Visa Tracker\'!G2:G{len(visa_rows)+1},">=0",\'Visa Tracker\'!G2:G{len(visa_rows)+1},"<="&Parameters!B5)', "Nonexpired within demonstration horizon; expired tracked separately."],
        ["Expired visa records", f'=COUNTIF(\'Visa Tracker\'!G2:G{len(visa_rows)+1},"<0")', "Requires permission/evidence review, not a legal status finding."],
        ["Case follow-ups", f'=COUNTIF(\'Case Tracker\'!I2:I{len(case_rows)+1},"Governance follow-up")', "Overdue, missing owner or missing documentation."],
    ])
    workbook["Dashboard"]["B10"].number_format = "0.00%"
    workbook["Dashboard"].column_dimensions["A"].width = 36
    workbook["Dashboard"].column_dimensions["C"].width = 100
    workbook._sheets.insert(1, workbook._sheets.pop(workbook.sheetnames.index("Dashboard")))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(TARGET)
    return TARGET


def calculate_and_pivot(path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    excel = None
    book = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AskToUpdateLinks = False
        excel.AutomationSecurity = 3
        book = excel.Workbooks.Open(str(path.resolve()), UpdateLinks=0, ReadOnly=False)
        for name in ["Reconciliation", "Lookup Lab"]:
            sheet = book.Worksheets(name)
            formulas = sheet.UsedRange.Formula2
            sheet.UsedRange.Formula2 = tuple(
                tuple(item.replace("_xlfn.", "") if isinstance(item, str) and item.startswith("=") else item for item in row)
                for row in formulas
            )
        excel.CalculateFullRebuild()
        for name, source, row_field, column_field, amount_field in [
            ("Payroll Pivot", "Reconciliation", "department", "result", "delta_eur"),
            ("Case Pivot", "Case Tracker", "case_type", "result", "case_id"),
        ]:
            sheet = book.Worksheets.Add(After=book.Worksheets(book.Worksheets.Count))
            sheet.Name = name
            sheet.Cells(1, 1).Value = "SYNTHETIC DATA / native refreshable Excel PivotTable"
            sheet.Cells(1, 1).Font.Bold = True
            source_sheet = book.Worksheets(source)
            last_row = source_sheet.UsedRange.Rows.Count
            last_column = source_sheet.UsedRange.Columns.Count
            cache = book.PivotCaches().Create(
                SourceType=1, SourceData=f"'{source}'!R1C1:R{last_row}C{last_column}"
            )
            pivot = cache.CreatePivotTable(
                TableDestination=sheet.Range("A4"), TableName=name.replace(" ", "") + "Table"
            )
            pivot.PivotFields(row_field).Orientation = 1
            pivot.PivotFields(column_field).Orientation = 2
            pivot.AddDataField(pivot.PivotFields(amount_field), "Signed discrepancy EUR" if source == "Reconciliation" else "Case count",
                               -4157 if source == "Reconciliation" else -4112)
            pivot.TableStyle2 = "PivotStyleMedium9"
            pivot.RefreshTable()
            sheet.Columns.AutoFit()
        excel.CalculateFullRebuild()
        book.Save()
        version = str(excel.Version)
        book.Close(SaveChanges=True)
        book = None
    finally:
        if book is not None:
            book.Close(SaveChanges=False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()
    cached = load_workbook(path, data_only=True)
    formulas = load_workbook(path, data_only=False)
    errors, missing, count, blank_results = [], [], 0, 0
    for sheet in formulas:
        for row in sheet:
            for cell in row:
                result = cached[sheet.title][cell.coordinate]
                if result.data_type == "e":
                    errors.append(f"{sheet.title}!{cell.coordinate}: {result.value}")
                if cell.data_type == "f":
                    count += 1
                    if result.value is None:
                        blank_results += 1
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                document = ET.fromstring(archive.read(name))
                for cell in document.findall(".//s:c", namespace):
                    if cell.find("s:f", namespace) is not None and cell.find("s:v", namespace) is None:
                        missing.append(f"{name}!{cell.get('r')}")
    report = {"engine": f"Microsoft Excel {version}", "formula_count": count,
              "formula_errors": errors, "uncached_formula_cells": missing,
              "intentional_blank_formula_results": blank_results,
              "pivot_tables": sum(len(sheet._pivots) for sheet in formulas)}
    (ROOT / "outputs" / "excel_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    cached.close()
    formulas.close()
    if errors or missing or report["pivot_tables"] != 2:
        raise ValueError(f"Excel validation failed: {report}")
    print(json.dumps(report, indent=2))
    return report
