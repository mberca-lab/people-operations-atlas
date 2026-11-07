import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import nbformat
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analysis import analyse, employee_key, make_sources, resolve_duplicates
from sources import decode_cube, load_public
from review_scenarios import absence_on_roster, calendar_time_review, make_review_pack, prorated_pay


class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public, cls.provenance = load_public()
        cls.sources = make_sources()
        cls.result = analyse(cls.sources)
        cls.review = make_review_pack(cls.sources, cls.result)
        cls.cache = load_workbook(ROOT / "outputs" / "People_Operations_Control_Workbook.xlsx", data_only=True, read_only=True)
        cls.recon_excel = {row[0]: row for row in cls.cache["Reconciliation"].iter_rows(min_row=2, values_only=True)}

    @classmethod
    def tearDownClass(cls):
        cls.cache.close()

    def test_public_snapshot_hash_and_selection(self):
        self.assertEqual(len(self.public), 3150)
        self.assertEqual(self.public["quarter"].min(), "2019Q1")
        self.assertEqual(self.public["quarter"].max(), "2026Q2")
        self.assertFalse(self.public["value"].isna().any())
        self.assertFalse(self.public.duplicated(["metric_code", "quarter", "sector_code"]).any())
        self.assertEqual(set(self.public.groupby("metric_code")["unit"].first()), {"Number", "Euro", "Hours"})

    def test_json_stat_order_and_missing_are_preserved(self):
        cube = {"id": ["metric", "sector"], "dimension": {
            "metric": {"category": {"index": {"b": 1, "a": 0}}},
            "sector": {"category": {"index": ["x", "y"]}}},
            "value": {"0": 0, "2": 20, "3": 30}}
        frame = decode_cube(cube)
        self.assertEqual(frame[["metric", "sector"]].values.tolist(), [["a", "x"], ["a", "y"], ["b", "x"], ["b", "y"]])
        self.assertEqual(frame.iloc[0]["value"], 0)
        self.assertTrue(pd.isna(frame.iloc[1]["value"]))
        self.assertEqual(frame.iloc[2]["value"], 20)

    def test_equivalent_payloads_collapse_conflicts_do_not(self):
        frame = pd.DataFrame({"id": ["a", "a", "b", "b"], "value": [100, 100, 200, 201], "source": [1, 2, 3, 4]})
        clean, conflicts, duplicates = resolve_duplicates(frame, "id", ["value"])
        self.assertEqual(clean["id"].tolist(), ["a"])
        self.assertEqual(duplicates, 1)
        self.assertEqual(conflicts[0][0], "b")
        self.assertEqual(conflicts[0][1]["source"].tolist(), [3, 4])
        self.assertEqual(employee_key(" emp 0001 "), "EMP0001")

    def test_master_population_and_lifecycle_gates(self):
        qa = self.result["qa"]
        self.assertEqual((qa["hr_raw_rows"], qa["hr_unique_keys"], qa["hr_valid_records"]), (364, 360, 355))
        self.assertEqual((qa["active_headcount"], qa["active_fte"]), (344, 324))
        self.assertFalse(self.result["hr_clean"]["employee_id"].isin(["EMP0060", "EMP0007", "EMP0020", "EMP0030", "EMP0041"]).any())
        self.assertFalse(self.result["active_hr"]["employee_id"].isin(["EMP0028", "EMP0355"]).any())
        self.assertEqual(len(self.result["active_hr"]), len(self.result["reconciliation"]))

    def test_invalid_end_dates_and_zero_salary_are_rejected(self):
        sources = {name: frame.copy() for name, frame in self.sources.items()}
        hr = sources["hr_raw"]
        hr.loc[hr["employee_id"].map(employee_key).eq("EMP0001"), "end_date"] = "not a date"
        hr.loc[hr["employee_id"].map(employee_key).eq("EMP0002"), "annual_salary_eur"] = 0
        result = analyse(sources)
        self.assertFalse(result["active_hr"]["employee_id"].isin(["EMP0001", "EMP0002"]).any())
        messages = result["exceptions"].set_index("employee_id")["detail"]
        self.assertIn("end date", str(messages.loc["EMP0001"]))
        self.assertIn("salary", str(messages.loc["EMP0002"]))

    def test_payroll_unknown_unmapped_and_conflict_are_not_zero(self):
        recon = self.result["reconciliation"].set_index("employee_id")
        self.assertEqual(recon.loc["EMP0024", "result"], "Unknown gross")
        self.assertTrue(pd.isna(recon.loc["EMP0024", "gross_eur"]))
        for employee in ["EMP0033", "EMP0099", "EMP0101"]:
            self.assertEqual(recon.loc[employee, "result"], "Missing / quarantined payment")
            self.assertTrue(pd.isna(recon.loc[employee, "delta_eur"]))
        self.assertNotIn("E033", set(self.result["payroll_clean"]["employee_id"]))

    def test_legitimate_changes_pass_and_seeded_variances_reconcile(self):
        recon = self.result["reconciliation"].set_index("employee_id")
        self.assertTrue(recon.loc[["EMP0044", "EMP0055"], "result"].eq("Reconciled").all())
        self.assertEqual(set(recon[recon["result"].eq("Amount exception")].index), {"EMP0005", "EMP0011", "EMP0018"})
        common = recon[recon["delta_eur"].notna()]
        self.assertEqual(len(common), 340)
        self.assertEqual(round(common["gross_eur"].sum() - common["expected_gross_eur"].sum(), 2), 1847.33)
        self.assertEqual(round(common["delta_eur"].abs().sum(), 2), 2652.67)
        self.assertGreater(common["delta_eur"].abs().sum(), abs(common["delta_eur"].sum()))

    def test_absence_union_exposure_and_time_conflict(self):
        qa = self.result["qa"]
        self.assertEqual(qa["absence_naive_valid_days"] - qa["absence_unique_days"], 1)
        self.assertFalse(self.result["absence_days"].duplicated(["employee_id", "date"]).any())
        self.assertEqual(len(self.result["absence_days"]), 296)
        summary = self.result["absence_summary"]
        self.assertTrue(summary["lost_hours"].le(summary["scheduled_hours"]).all())
        self.assertEqual(round(summary["lost_hours"].sum()/summary["scheduled_hours"].sum()*100, 3), qa["absence_rate_pct"])
        self.assertIn("Overlapping absence", set(self.result["exceptions"]["code"]))
        self.assertIn("Absence / time conflict", set(self.result["exceptions"]["code"]))

    def test_peak_week_and_incomplete_are_different(self):
        time = self.result["time_summary"].set_index("employee_id")
        self.assertEqual(time.loc["EMP0150", "peak_hours"], 60)
        self.assertLess(time.loc["EMP0150", "average_hours"], 48)
        self.assertEqual(time.loc["EMP0150", "result"], "Below screen")
        self.assertEqual(time.loc["EMP0103", "complete_weeks"], 16)
        self.assertEqual(time.loc["EMP0103", "result"], "Incomplete / review")
        self.assertIn("Daily rest review", set(self.result["exceptions"]["code"]))
        self.assertIn("Break record review", set(self.result["exceptions"]["code"]))

    def test_entirely_missing_time_record_remains_unknown(self):
        sources = {name: frame.copy() for name, frame in self.sources.items()}
        sources["time_raw"] = sources["time_raw"][sources["time_raw"]["employee_id"].ne("EMP0001")]
        time = analyse(sources)["time_summary"].set_index("employee_id")
        self.assertEqual(time.loc["EMP0001", "complete_weeks"], 0)
        self.assertTrue(pd.isna(time.loc["EMP0001", "average_hours"]))
        self.assertEqual(time.loc["EMP0001", "result"], "Incomplete / review")

    def test_visa_and_cases_use_distinct_nonovercounted_flags(self):
        self.assertEqual(self.result["visa"]["days_remaining"].between(0, 90).sum(), 10)
        self.assertEqual(self.result["visa"]["days_remaining"].lt(0).sum(), 2)
        self.assertEqual(self.result["cases"]["result"].eq("Governance follow-up").sum(), 10)
        e = self.result["exceptions"]
        self.assertTrue(e["exception_id"].is_unique)
        self.assertTrue(e[["evidence", "action", "owner"]].notna().all().all())
        self.assertTrue(e["status"].eq("Open / demonstration").all())

    def test_excel_dashboard_matches_python(self):
        qa = self.result["qa"]
        expected = [qa[k] for k in [
            "active_headcount", "active_fte", "reconciled_employees", "payroll_amount_exceptions",
            "expected_comparable_eur", "actual_comparable_eur", "signed_payroll_delta_eur",
            "absolute_payroll_delta_eur",
        ]] + [qa["absence_rate_pct"]/100, qa["time_above_screen"], qa["time_incomplete"],
              qa["visa_within_90_days"], qa["visa_expired_records"], qa["case_followups"]]
        actual = [row[1] for row in self.cache["Dashboard"].iter_rows(min_row=2, values_only=True)]
        for index, (value, target) in enumerate(zip(actual, expected)):
            self.assertAlmostEqual(value, target, places=5 if index == 8 else 2, msg=f"Dashboard row {index+2}")

    def test_excel_row_parity_and_unknown_lookup(self):
        for row in self.result["reconciliation"].itertuples():
            excel = self.recon_excel[row.employee_id]
            expected_status = "Missing payment" if row.result == "Missing / quarantined payment" else row.result
            self.assertEqual(excel[11], expected_status, row.employee_id)
            if pd.notna(row.delta_eur):
                self.assertAlmostEqual(excel[10], row.delta_eur, places=2)
            else:
                self.assertIsNone(excel[10])
        lookup = list(self.cache["Lookup Lab"].iter_rows(min_row=2, values_only=True))
        self.assertEqual(lookup[-1][1:4], ("Not found", "Not found", "Not found"))
        self.assertTrue(all(row[4] == "Consistent" for row in lookup))

    def test_excel_absence_and_time_row_parity(self):
        for excel, row in zip(self.cache["Absence Summary"].iter_rows(min_row=2, values_only=True), self.result["absence_summary"].itertuples()):
            self.assertEqual(excel[1], row.department)
            self.assertAlmostEqual(excel[2], row.scheduled_hours, places=2)
            self.assertAlmostEqual(excel[3], row.lost_hours, places=2)
            self.assertAlmostEqual(excel[4]*100, row.rate_pct, places=3)
        python_time = self.result["time_summary"].set_index("employee_id")
        for row in self.cache["Time Review"].iter_rows(min_row=2, values_only=True):
            expected = python_time.loc[row[0]]
            self.assertEqual(row[3], expected["complete_weeks"])
            self.assertAlmostEqual(row[4], expected["average_hours"], places=6)
            self.assertEqual(row[5], expected["result"].replace("Above 48h", "Above screen"))

    def test_excel_no_errors_cached_formulas_and_real_pivots(self):
        report = json.loads((ROOT / "outputs" / "excel_validation.json").read_text())
        self.assertEqual(report["formula_errors"], [])
        self.assertEqual(report["uncached_formula_cells"], [])
        self.assertGreater(report["formula_count"], 10000)
        for sheet in self.cache:
            for row in sheet:
                for cell in row:
                    self.assertNotEqual(cell.data_type, "e", f"{sheet.title}!{getattr(cell, 'coordinate', 'empty')}")
        with ZipFile(ROOT / "outputs" / "People_Operations_Control_Workbook.xlsx") as archive:
            pivots = [name for name in archive.namelist() if name.startswith("xl/pivotTables/pivotTable") and name.endswith(".xml")]
            self.assertEqual(len(pivots), 2)
            self.assertTrue(all(b"<rowFields" in archive.read(name) for name in pivots))

    def test_native_excel_parameter_and_ambiguity_scenarios(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        excel, book = None, None
        temporary = tempfile.TemporaryDirectory(prefix="atlas-scenario-", dir=ROOT / "outputs", ignore_cleanup_errors=True)
        try:
            with temporary as folder:
                path = Path(folder) / "scenario.xlsx"
                shutil.copyfile(ROOT / "outputs" / "People_Operations_Control_Workbook.xlsx", path)
                excel = win32com.client.DispatchEx("Excel.Application")
                excel.Visible = False
                excel.DisplayAlerts = False
                excel.AskToUpdateLinks = False
                excel.AutomationSecurity = 3
                book = excel.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=False)
                parameters, dashboard = book.Worksheets("Parameters"), book.Worksheets("Dashboard")
                parameters.Range("B4").Value = 3000
                parameters.Range("B6").Value = 60
                parameters.Range("B5").Value = 30
                excel.CalculateFullRebuild()
                self.assertEqual(dashboard.Range("B5").Value, 0)
                self.assertEqual(dashboard.Range("B4").Value, 340)
                self.assertEqual(dashboard.Range("B11").Value, 0)
                self.assertEqual(dashboard.Range("B13").Value, self.result["visa"]["days_remaining"].between(0, 30).sum())
                parameters.Range("B4").Value = 0.02
                parameters.Range("B6").Value = 48
                parameters.Range("B5").Value = 90
                proration = book.Worksheets("Proration Examples")
                proration.Range("E2").Value2 = proration.Range("G2").Value2 + 31
                closure = book.Worksheets("Closure Review")
                closure.Range("B7").Value = closure.Range("B8").Value + 100
                calendar = book.Worksheets("Calendar Days")
                calendar.Range("D2").Value = "Unsupported"
                excel.CalculateFullRebuild()
                self.assertEqual(proration.Range("K2").Value, 0)
                self.assertEqual(closure.Range("B10").Value, 100)
                self.assertEqual(closure.Range("B11").Value, "Amount exception")
                self.assertEqual(book.Worksheets("Calendar Review").Range("J2").Value, "Unknown")
                self.assertEqual(dashboard.Range("B4").Value, 337)
                payroll_row = list(self.result["payroll_clean"]["employee_id"]).index("EMP0018") + 2
                payroll = book.Worksheets("Payroll Clean")
                payroll.Cells(payroll_row, 3).Value = self.review["closure"]["expected_gross_eur"]
                payroll.Cells(payroll_row, 4).Value = round(self.review["closure"]["approved_salary_eur"] * self.review["closure"]["fte"] / 12, 2)
                closure.Range("B7").Value = closure.Range("B8").Value
                excel.CalculateFullRebuild()
                book.RefreshAll()
                excel.CalculateFullRebuild()
                self.assertEqual(dashboard.Range("B4").Value, 338)
                self.assertEqual(dashboard.Range("B5").Value, 2)
                self.assertEqual(closure.Range("B18").Value, 338)
                self.assertAlmostEqual(closure.Range("B13").Value, 2250, places=2)
                approvals = book.Worksheets("Approvals")
                approvals.Range("B4").Value = "EMP0018"
                approvals.Range("C4").Value = "Salary"
                approvals.Range("E4").Value = 60000
                excel.CalculateFullRebuild()
                row_index = list(self.recon_excel).index("EMP0018") + 2
                self.assertEqual(book.Worksheets("Reconciliation").Cells(row_index, 4).Value, "Ambiguous")
                self.assertEqual(book.Worksheets("Reconciliation").Cells(row_index, 12).Value, "Approval / key review")
                book.Close(SaveChanges=False)
                book = None
                excel.Quit()
                excel = None
        finally:
            if book is not None:
                book.Close(SaveChanges=False)
            if excel is not None:
                excel.Quit()
            temporary.cleanup()
            pythoncom.CoUninitialize()

    def test_proration_dates_and_contractual_fte(self):
        values = [row["prorated_base_eur"] for row in self.review["proration"]]
        self.assertEqual(values, [3870.97, 3096.77, 2400])
        for hire, end in [("2026-11-01", None), ("2025-01-01", "2026-09-30")]:
            self.assertEqual(prorated_pay(72000, 1, hire, end, "2026-10-01")["prorated_base_eur"], 0)
        for args in [(72000, 0, "2026-10-01", None, "2026-10-01"),
                     (72000, 1, "2026-10-10", "2026-10-01", "2026-10-01"),
                     (float("nan"), 1, "2026-10-01", None, "2026-10-01")]:
            with self.assertRaises(ValueError):
                prorated_pay(*args)

    def test_roster_closure_overlap_and_zero_exposure(self):
        full, part = self.review["roster_summary"]
        self.assertEqual((full["scheduled_hours"], full["lost_hours"]), (157.5, 22.5))
        self.assertEqual((part["scheduled_hours"], part["lost_hours"]), (82.5, 15))
        closed = [row for row in self.review["roster_days"] if row["date"] == "2026-10-26"]
        self.assertTrue(all(row["scheduled_hours"] == row["lost_hours"] == 0 for row in closed))
        empty = {**self.review["roster_inputs"][0], "weekdays": []}
        _, summary = absence_on_roster([empty], [], [], "2026-10-01", "2026-10-31")
        self.assertIsNone(summary[0]["rate_pct"])

    def test_calendar_leave_missing_days_and_invalid_records(self):
        first, leave, missing = self.review["calendar_summary"]
        self.assertGreater(first["average_hours"], 48)
        self.assertEqual((leave["eligible_days"], leave["worked_hours"]), (118, 622.5))
        self.assertAlmostEqual(leave["average_hours"], 622.5 * 7 / 118)
        self.assertEqual(missing["reported_days"], 122)
        self.assertIsNone(missing["average_hours"])
        frame = pd.DataFrame(self.review["calendar_days"])
        with self.assertRaises(ValueError):
            calendar_time_review(pd.concat([frame, frame.iloc[[0]]]), "2026-07-01", ["TIME-01"])
        for hours, kind in [(float("inf"), "None"), (1, "Annual"), (0, "Unsupported")]:
            changed = frame.copy()
            changed.loc[0, ["worked_hours", "leave_kind"]] = [hours, kind]
            self.assertIsNone(calendar_time_review(changed, "2026-07-01", ["TIME-01"])[0]["average_hours"])

    def test_closed_case_retains_original_sources_and_controls(self):
        case = self.review["closure"]
        pd.testing.assert_frame_equal(self.sources["payroll_raw"], make_sources()["payroll_raw"])
        self.assertEqual(self.result["qa"]["reconciled_employees"], 337)
        self.assertEqual(case["corrected_delta_eur"], 0)
        self.assertEqual(case["after_qa"]["reconciled_employees"], 338)
        self.assertEqual(case["after_qa"]["payroll_amount_exceptions"], 2)
        self.assertEqual(case["after_qa"]["absolute_payroll_delta_eur"], 2250)
        self.assertNotEqual(case["original_payroll_sha256"], case["corrected_payroll_sha256"])

    def test_excel_supplementary_scenario_parity(self):
        for excel, row in zip(self.cache["Proration Examples"].iter_rows(min_row=2, values_only=True), self.review["proration"]):
            self.assertEqual(excel[8], row["active_days"])
            self.assertAlmostEqual(excel[10], row["prorated_base_eur"], places=2)
        for excel, row in zip(self.cache["Roster Summary"].iter_rows(min_row=2, values_only=True), self.review["roster_summary"]):
            self.assertEqual(excel[3:5], (row["scheduled_hours"], row["lost_hours"]))
            self.assertAlmostEqual(excel[5] * 100, row["rate_pct"], places=3)
        for excel, row in zip(self.cache["Calendar Review"].iter_rows(min_row=2, values_only=True), self.review["calendar_summary"]):
            self.assertEqual(excel[3:5], (row["required_days"], row["reported_days"]))
            if row["average_hours"] is None:
                self.assertEqual(excel[9], "Unknown")
            else:
                self.assertAlmostEqual(excel[9], row["average_hours"])
        self.assertEqual(self.cache["Closure Review"]["B10"].value, 0)
        self.assertEqual(self.cache["Closure Review"]["B18"].value, 338)
        self.assertEqual(self.cache["Closure Review"]["B15"].value, 2250)

    def test_executed_notebook_and_site_match_current_analysis(self):
        notebook = nbformat.read(ROOT / "analysis.ipynb", as_version=4)
        code = [cell for cell in notebook.cells if cell.cell_type == "code"]
        self.assertTrue(all(cell.execution_count is not None for cell in code))
        self.assertFalse(any(output.output_type == "error" for cell in code for output in cell.outputs))
        payload = json.loads((ROOT / "outputs" / "site_data.json").read_text())
        self.assertEqual(payload["qa"], self.result["qa"])
        self.assertEqual(len(payload["public"]), len(self.public))
        self.assertEqual(len(payload["requirements"]), 29)
        self.assertEqual(payload["provenance"]["sha256"], self.provenance["sha256"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AtlasTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "successful": result.wasSuccessful(),
              "scope": "Source decoding, seeded control fixtures, missing-time edge cases, Python/Excel parity, native Excel scenarios, genuine pivots and executed notebook."}
    (ROOT / "outputs" / "test_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sys.exit(not result.wasSuccessful())
