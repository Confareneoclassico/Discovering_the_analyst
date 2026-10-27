#!/usr/bin/env python3
"""Phase 0D: denominators of the normalisations, real data only.

Two quantities of the protocol divide by a spread of the REAL 901-set:
  - claim X1a divides quantile differences by the real 10-90 percentile band of
    each key variable, category and decade;
  - the ensemble distance standardises each variable-year marginal of the
    evaluation set E by its real standard deviation in that category.
Where the real spread is close to zero (scenarios harmonised to the 2020 base
year, carbon sequestration reported as zero), the ratio is ill-conditioned. The
protocol therefore floors each denominator at a fraction of the median of that
variable's spreads over the nine decades in the same category. This script
computes, before the freeze, the cells where the floors bind.

It reads ONLY Real_*.csv and the configuration. No synthetic file is read and no
claim rule is evaluated. The output contains no timestamp or environment
information, so a re-run on the same inputs reproduces it byte for byte.

Usage:  python3 08_denominator_guard.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0d_denominator_guard.json
"""
import argparse, hashlib, json, re
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ["C1234", "C56", "C78"]


def sig(x, n=6):
    """Round to n significant digits so that the report does not depend on float noise."""
    return float(f"{x:.{n}g}")


def read_real(path, variables, years, n_expected):
    if "gen_" in path.name.lower():
        raise SystemExit("Refusing to read a synthetic file before the freeze: " + path.name)
    df = pd.read_csv(path)
    if "Variable" not in df.columns:
        raise SystemExit(f"{path.name}: expected long format with a 'Variable' column")
    cols = [str(y) for y in years]
    missing = sorted(set(variables) - set(df["Variable"]))
    if missing:
        raise SystemExit(f"{path.name}: variables not found: {missing}")
    out = {}
    for v in variables:
        sub = df[df["Variable"] == v]
        if not sub["Scenario"].is_unique or len(sub) != n_expected:
            raise SystemExit(f"{path.name}, {v}: expected {n_expected} distinct scenarios, found {len(sub)} rows "
                             f"and {sub['Scenario'].nunique()} distinct")
        out[v] = sub[cols].astype(float).to_numpy()          # scenarios x decades
    return out


def binding(table, floor):
    return [dict(r) for r in table if r["ratio"] < floor]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    cfg = yaml.safe_load(open(ROOT / "config" / "paper_values.yaml"))
    E = cfg["fixed"]["evaluation_set_E"]
    key, years = E["key_variables"], E["years"]
    variables = key + E["electricity"]
    g_x1a = cfg["fixed"]["claims"]["X1a"]["guard"]
    g_sd = cfg["fixed"]["estimator"]["standardisation_guard"]
    floors = sorted({g_x1a["floor_fraction"], *g_x1a["descriptive_floor_fractions"],
                     g_sd["floor_fraction"], *g_sd["descriptive_floor_fractions"]})

    dep = Path(paths["scenarios3000_dir"]).expanduser()
    inputs, bands, sds = {}, [], []
    for c in CATEGORIES:
        f = dep / f"Real_{c}.csv"
        inputs[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        data = read_real(f, variables, years, cfg["factors"]["G1_population"]["levels"]["901"]["counts"][c])
        for v in variables:
            X = data[v]
            band = np.quantile(X, 0.90, axis=0) - np.quantile(X, 0.10, axis=0)   # linear interpolation
            sd = X.std(axis=0, ddof=1)
            mb, ms = np.median(band), np.median(sd)
            for i, y in enumerate(years):
                common = {"variable": v, "category": c, "year": int(y), "n_scenarios": int(X.shape[0]),
                          "zero_fraction": sig(np.mean(X[:, i] == 0), 4)}
                if v in key:
                    bands.append({**common, "band": sig(band[i]), "median_band_over_decades": sig(mb),
                                  "ratio": sig(band[i] / mb)})
                sds.append({**common, "sd": sig(sd[i]), "median_sd_over_decades": sig(ms),
                            "ratio": sig(sd[i] / ms)})

    report = {
        "inputs_sha256": inputs,
        "definitions": {
            "band": "Q90 - Q10 over the scenarios of the real 901-set, per key variable, category and decade "
                    "(numpy quantile, linear interpolation)",
            "sd": "sample standard deviation (ddof = 1) per variable of E, category and decade",
            "ratio": "spread divided by the median of the same variable's spreads over the nine decades, "
                     "within the category",
            "floor": "a denominator is replaced by floor x median over decades when the ratio is below floor",
        },
        "x1a_floor_fraction": g_x1a["floor_fraction"],
        "standardisation_floor_fraction": g_sd["floor_fraction"],
        "x1a_band": {
            "n_cells": len(bands),
            "n_zero_bands": sum(r["band"] == 0 for r in bands),
            "binding_cells": {str(fl): binding(bands, fl) for fl in floors},
        },
        "ensemble_sd": {
            "n_marginals": len(sds),
            "n_zero_sds": sum(r["sd"] == 0 for r in sds),
            "binding_marginals": {str(fl): binding(sds, fl) for fl in floors},
            "max_magnification_without_floor": sig(1 / min(r["ratio"] for r in sds), 3),
        },
    }
    dest = ROOT / "results" / "phase0d_denominator_guard.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n")
    for name, block, k in [("X1a bands", report["x1a_band"], "binding_cells"),
                           ("ensemble SDs", report["ensemble_sd"], "binding_marginals")]:
        print(f"{name}: " + "; ".join(f"floor {fl}: {len(v)}" for fl, v in block[k].items()))
    prim = report["x1a_band"]["binding_cells"][str(g_x1a["floor_fraction"])]
    print("X1a cells at the primary floor:", ", ".join(f"{r['variable']} {r['category']} {r['year']}" for r in prim))
    print("Written:", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
