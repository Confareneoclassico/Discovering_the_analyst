#!/usr/bin/env python3
"""Phase 0.3: validate the deposited scenarios against the paper's Source Data Fig. 3.

Source Data Fig. 3 (sheets Fig3a to Fig3f, header in the second row) gives, per
Type (Gen_C1234, Real_C1234, ...) and Year, the mean, the quantiles 10, 25, 50,
75 and 90 and the whiskers of one variable. This script recomputes the five
quantiles from the deposited Scenarios3000/{Gen,Real}_{C1234,C56,C78}.csv and
compares them with the sheet. The mean and the whiskers are not compared. It
also records the number of scenarios and the SHA-256 of each deposited file
(DATA.md, A3; D6).

Sheets and variables, as in the figure caption:
  a: PrimaryEnergy_Coal   b: PrimaryEnergy_Gas   c: PrimaryEnergy_Oil
  d: FinalEnergy_Liquid   e: CarbonSequestration f: Kyoto_Gases

A quantile agrees with the sheet when
    |ours - ref| <= RTOL * |ref| + ATOL,
with RTOL = 2% and ATOL = 1e-9 in the units of the sheet. The absolute term
only matters for quantiles at or near zero. The summary reports the synthetic
and the real series separately and, within each, the comparisons whose
reference is below NEAR_ZERO, where the absolute term matters. An empty or
non-numeric value of the deposit and an empty cell of the sheet count as
failures, with their own status; a Type of the sheet that is not of the form
Gen_C<n> or Real_C<n> is listed under types_not_compared.

It reads the deposited Gen_ and Real_ files and computes quantiles of single
variables only. No claim rule is evaluated.

Usage:  python3 03_synthetic_fidelity.py [--paths ../config/local_paths.yaml]
Needs:  scenarios3000_dir and source_data_fig3_xlsx in local_paths.yaml (DATA.md, A3 and A7)
Output: ../results/phase0_synthetic_fidelity.json
"""
import argparse, hashlib, json, re
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
SHEET2VAR = {"Fig3a": "PrimaryEnergy_Coal", "Fig3b": "PrimaryEnergy_Gas",
             "Fig3c": "PrimaryEnergy_Oil", "Fig3d": "FinalEnergy_Liquid",
             "Fig3e": "CarbonSequestration", "Fig3f": "KyotoGases"}
QCOLS = {"Quantile_10": 0.10, "Quantile_25": 0.25, "Quantile_50": 0.50,
         "Quantile_75": 0.75, "Quantile_90": 0.90}
RTOL = 0.02          # relative tolerance
ATOL = 1e-9          # absolute allowance, in the units of the sheet
NEAR_ZERO = 1e-6     # references below this are reported separately: there ATOL exceeds 0.1% of the reference

# D10: the deposit stores CarbonSequestration in MtCO2 and Kyoto Gases in MtCO2-eq, while Source
# Data Fig. 3 uses Gt (before harmonisation all failures were exact ratios of 1,000, confined to
# these two variables). The deposit is converted to Gt.
UNIT_SCALE = {"CarbonSequestration": 1e-3, "KyotoGases": 1e-3}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def sig(x, n=6):
    """Round to n significant digits."""
    return float(f"{x:.{n}g}")


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def canon(name):
    return re.sub(r"[^a-z]", "", str(name).lower())


def load_deposit_csv(path):
    """Deposit file -> dict canonical variable name -> DataFrame (rows = scenarios, columns = years as int).
    The deposit has one row per scenario and variable, with one column per year."""
    df = pd.read_csv(path)
    if not {"Scenario", "Variable"} <= set(df.columns):
        raise SystemExit(f"{path.name}: expected the columns Scenario and Variable, found {list(df.columns)[:10]}")
    ycols = [c for c in df.columns if re.fullmatch(r"(19|20|21)\d\d", str(c))]
    out = {}
    for v, g in df.groupby("Variable"):
        if not g["Scenario"].is_unique:
            raise SystemExit(f"{path.name}, {v}: repeated scenario identifiers")
        out[canon(v)] = g[ycols].rename(columns=int).reset_index(drop=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    dep_dir = Path(paths["scenarios3000_dir"]).expanduser()
    ref = pd.ExcelFile(Path(paths["source_data_fig3_xlsx"]).expanduser())

    report = {"rule": "abs(ours - ref) <= rtol * abs(ref) + atol", "rtol": RTOL, "atol": ATOL,
              "near_zero": NEAR_ZERO, "unit_scale_applied": UNIT_SCALE,
              "files": {}, "comparisons": [], "types_not_compared": [], "n_fail": 0}
    loaded = {}

    for sheet, var in SHEET2VAR.items():
        r = ref.parse(sheet, header=1)
        for typ, g in r.groupby("Type"):                    # Gen_C1234, Real_C1234, ...
            m = re.fullmatch(r"(Gen|Real)_(C\d+)", str(typ).strip())
            if not m:                                       # listed, so that nothing is skipped silently
                report["types_not_compared"].append({"sheet": sheet, "type": str(typ), "rows": int(len(g))})
                continue
            kind, cat = m.groups()
            fpath = dep_dir / f"{kind}_{cat}.csv"
            if not fpath.exists():
                report["comparisons"].append({"type": typ, "var": var, "status": "FILE MISSING"})
                report["n_fail"] += 1
                continue
            if fpath.name not in loaded:
                loaded[fpath.name] = load_deposit_csv(fpath)
                report["files"][fpath.name] = {"sha256": sha256(fpath)}
            data = loaded[fpath.name]
            if canon(var) not in data:
                report["comparisons"].append({"type": typ, "var": var, "status": "VAR NOT FOUND",
                                              "available": sorted(data)[:20]})
                report["n_fail"] += 1
                continue
            mat = data[canon(var)]
            report["files"][fpath.name].setdefault("n_scenarios", int(len(mat)))
            for _, row in g.iterrows():
                year = int(row["Year"])
                if year not in mat.columns:
                    report["comparisons"].append({"type": typ, "var": var, "year": year, "status": "YEAR MISSING"})
                    report["n_fail"] += 1
                    continue
                vals = pd.to_numeric(mat[year], errors="coerce").to_numpy(float) * UNIT_SCALE.get(var, 1.0)
                n_missing = int((~np.isfinite(vals)).sum())
                if n_missing:                               # an empty or non-numeric cell in the deposit
                    report["comparisons"].append({"type": typ, "var": var, "year": year,
                                                  "status": "VALUES MISSING", "n_missing": n_missing})
                    report["n_fail"] += 1
                    continue
                for qc, q in QCOLS.items():
                    refv, ourv = float(row[qc]), float(np.quantile(vals, q))
                    if not np.isfinite(refv):               # an empty cell in the sheet
                        report["comparisons"].append({"type": typ, "var": var, "year": year, "stat": qc,
                                                      "status": "REFERENCE MISSING"})
                        report["n_fail"] += 1
                        continue
                    dev = abs(ourv - refv)
                    ok = dev <= RTOL * abs(refv) + ATOL
                    if not ok:
                        report["n_fail"] += 1
                    report["comparisons"].append(
                        {"type": typ, "var": var, "year": year, "stat": qc,
                         "ref": refv, "ours": sig(ourv, 10), "abs_dev": sig(dev, 3),
                         "rel_dev": sig(dev / abs(refv), 3) if refv != 0 else None, "ok": bool(ok)})

    done = [c for c in report["comparisons"] if "ok" in c]

    def split(comparisons):
        away = [c for c in comparisons if abs(c["ref"]) >= NEAR_ZERO]
        near = [c for c in comparisons if abs(c["ref"]) < NEAR_ZERO]
        return {"n": len(comparisons), "n_fail": sum(not c["ok"] for c in comparisons),
                "reference_at_least_near_zero": {
                    "n": len(away), "n_fail": sum(not c["ok"] for c in away),
                    "largest_rel_dev": max((c["rel_dev"] for c in away), default=None)},
                "reference_below_near_zero": {
                    "n": len(near), "n_fail": sum(not c["ok"] for c in near),
                    "largest_abs_dev": max((c["abs_dev"] for c in near), default=None)}}

    report["summary"] = {
        "n_compared": len(done), "n_fail": report["n_fail"],
        "n_not_compared": sum("status" in c for c in report["comparisons"]),
        "types_not_compared": len(report["types_not_compared"]),
        "PASS": report["n_fail"] == 0 and len(done) > 0,
        "synthetic_series": split([c for c in done if c["type"].startswith("Gen")]),
        "real_series": split([c for c in done if c["type"].startswith("Real")]),
    }
    out = ROOT / "results" / "phase0_synthetic_fidelity.json"
    out.parent.mkdir(exist_ok=True)
    write_lf(out, json.dumps(report, indent=2, allow_nan=False) + "\n")   # strict JSON: no NaN can be written
    print(json.dumps(report["summary"], indent=2))
    print({f: v.get("n_scenarios") for f, v in report["files"].items()})


if __name__ == "__main__":
    main()
