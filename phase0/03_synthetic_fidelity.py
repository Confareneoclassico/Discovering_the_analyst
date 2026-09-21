#!/usr/bin/env python3
"""Phase 0.3 — validate the Zenodo synthetic deposit against the paper's own
Source Data Fig. 3.

Source Data Fig. 3 (sheets Fig3a–Fig3f, header row 2) gives, per Type
(e.g. Gen_C1234, Real_C1234) and Year: Mean, Quantile_10/25/50/75/90,
Whisker_lower/upper, Units. We recompute the same statistics from the
downloaded Scenarios3000/{Gen,Real}_{C1234,C56,C78}.csv and compare within
tolerance. Also settles D6 (row counts: 10,000 per Gen file expected) and
records per-file sha256 for DATA.md (A3).

The Fig3 sheet -> variable mapping follows the figure caption:
  a: PrimaryEnergy_Coal   b: PrimaryEnergy_Gas   c: PrimaryEnergy_Oil
  d: FinalEnergy_Liquid   e: CarbonSequestration f: KyotoGases
The column layout of the deposit CSVs must be confirmed on first run
(wide years x variables? long?) — the loader below sniffs both and stops
with a clear message if neither matches.

Output: ../results/phase0_synthetic_fidelity.json
"""
import json, argparse, hashlib, re
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

SHEET2VAR = {"Fig3a": "PrimaryEnergy_Coal", "Fig3b": "PrimaryEnergy_Gas",
             "Fig3c": "PrimaryEnergy_Oil", "Fig3d": "FinalEnergy_Liquid",
             "Fig3e": "CarbonSequestration", "Fig3f": "KyotoGases"}
QCOLS = {"Quantile_10": 0.10, "Quantile_25": 0.25, "Quantile_50": 0.50,
         "Quantile_75": 0.75, "Quantile_90": 0.90}
RTOL = 0.02   # 2% relative tolerance; tighten/loosen consciously and log it

# D10: the deposit stores CarbonSequestration in MtCO2 and KyotoGases in
# MtCO2-eq, while Source Data Fig. 3 uses Gt (verified 2026-09: all 514
# pre-harmonization failures were exact x1000 ratios, confined to these two
# variables; all EJ variables passed untouched). Harmonize deposit -> Gt.
UNIT_SCALE = {"CarbonSequestration": 1e-3, "KyotoGases": 1e-3}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def load_deposit_csv(path):
    """Return dict variable -> DataFrame(rows=scenarios, cols=years[int])."""
    df = pd.read_csv(path)
    year_pat = re.compile(r"^(19|20|21)\d\d$")
    # Case A: long format with Variable + year columns
    if "Variable" in df.columns:
        ycols = [c for c in df.columns if year_pat.match(str(c))]
        return {v: g[ycols].rename(columns=int).reset_index(drop=True)
                for v, g in df.groupby("Variable")}
    # Case B: wide format, columns like "<Variable>_<year>" or "<Variable>|<year>"
    out = {}
    split_pat = re.compile(r"^(.*?)[_|., ]((?:19|20|21)\d\d)$")
    groups = {}
    for c in df.columns:
        m = split_pat.match(str(c))
        if m:
            groups.setdefault(m.group(1), {})[int(m.group(2))] = c
    for var, ymap in groups.items():
        out[var] = df[[ymap[y] for y in sorted(ymap)]].set_axis(sorted(ymap), axis=1)
    if not out:
        raise SystemExit(f"Unrecognised layout in {path}: columns={list(df.columns)[:10]} …\n"
                         f"Inspect manually and extend load_deposit_csv().")
    return out


def canon(name):
    return re.sub(r"[^a-z]", "", str(name).lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    dep_dir = Path(paths["scenarios3000_dir"]).expanduser()
    ref = pd.ExcelFile(paths["source_data_fig3_xlsx"])

    report = {"rtol": RTOL, "unit_scale_applied": UNIT_SCALE,
              "files": {}, "comparisons": [], "n_fail": 0}

    for sheet, var in SHEET2VAR.items():
        r = ref.parse(sheet, header=1)
        for typ, g in r.groupby("Type"):                    # e.g. Gen_C1234 / Real_C1234
            m = re.match(r"(Gen|Real)_(C\d+)", str(typ))
            if not m:
                continue
            kind, cat = m.groups()
            fpath = dep_dir / f"{kind}_{cat}.csv"
            if not fpath.exists():
                report["comparisons"].append({"type": typ, "var": var, "status": "FILE MISSING"})
                report["n_fail"] += 1
                continue
            if fpath.name not in report["files"]:
                report["files"][fpath.name] = {"sha256": sha256(fpath)}
            data = load_deposit_csv(fpath)
            # match variable by canonical name
            key = next((k for k in data if canon(k) == canon(var)), None)
            if key is None:
                report["comparisons"].append({"type": typ, "var": var, "status": "VAR NOT FOUND",
                                              "available": sorted(map(str, data))[:20]})
                report["n_fail"] += 1
                continue
            mat = data[key]
            report["files"][fpath.name].setdefault("n_scenarios", int(len(mat)))
            for _, row in g.iterrows():
                year = int(row["Year"])
                if year not in mat.columns:
                    continue
                vals = mat[year].astype(float).to_numpy() * UNIT_SCALE.get(var, 1.0)
                for qc, q in QCOLS.items():
                    refv, ourv = float(row[qc]), float(np.quantile(vals, q))
                    ok = np.isclose(ourv, refv, rtol=RTOL, atol=1e-9 + 0.001 * abs(refv))
                    if not ok:
                        report["n_fail"] += 1
                    report["comparisons"].append(
                        {"type": typ, "var": var, "year": year, "stat": qc,
                         "ref": refv, "ours": round(ourv, 4), "ok": bool(ok)})

    n_tot = sum(1 for c in report["comparisons"] if "ok" in c)
    report["summary"] = {"n_compared": n_tot, "n_fail": report["n_fail"],
                         "PASS": report["n_fail"] == 0 and n_tot > 0}
    out = Path(__file__).parent.parent / "results" / "phase0_synthetic_fidelity.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["summary"], indent=2))
    print({f: v.get("n_scenarios") for f, v in report["files"].items()})


if __name__ == "__main__":
    main()
