"""A separate fictional cohort illustrating pay gaps and job-level composition."""

from statistics import fmean, median


def pay_statistics(rows):
    groups = {}
    for key, label in [("women", "Women"), ("men", "Men")]:
        values = [row["hourly_eur"] for row in rows if row["gender"] == label]
        groups[key] = {
            "n": len(values),
            "mean": round(fmean(values), 6) if values else None,
            "median": round(median(values), 6) if values else None,
        }
    for measure in ["mean", "median"]:
        reference, comparison = groups["men"][measure], groups["women"][measure]
        groups[f"{measure}_gap_pct"] = (
            round((reference - comparison) / reference * 100, 6)
            if reference is not None and reference > 0 and comparison is not None else None
        )
    return groups


def make_pay_lens():
    rows, levels = [], []
    for index, (title, rate, women, men) in enumerate([
        ("Support", 18, 36, 14),
        ("Specialist", 28, 34, 26),
        ("Manager", 42, 20, 34),
        ("Leadership", 62, 10, 26),
    ], 1):
        level = f"G{index}"
        for gender, count in [("Women", women), ("Men", men)]:
            for pair in range(count // 2):
                offset = round(rate * (0.03 + 0.11 * ((pair * 13 + 7) % 29) / 28), 2)
                for sign in [-1, 1]:
                    rows.append({
                        "id": f"GP{len(rows) + 1:03}",
                        "gender": gender, "level": level,
                        "hourly_eur": round(rate + sign * offset, 2),
                    })
        levels.append({
            "id": level, "title": title,
            **pay_statistics([row for row in rows if row["level"] == level]),
        })
    return {
        "scope": "Separate illustrative cohort: 200 fictional people; no employer data.",
        "pay_basis": "Hourly base pay in EUR; excludes bonus, overtime and benefits.",
        "definition": "(Men's statistic - women's statistic) / men's statistic x 100.",
        "construction": "Paired rates deliberately give equal means and medians within each level. Different job-level representation creates the overall gap.",
        "limitations": "A descriptive, constructed example, not an equal-pay assessment or statutory report. Women/men are illustrative categories, not an exhaustive gender model.",
        "rows": rows, "levels": levels, "overall": pay_statistics(rows),
    }
