#!/usr/bin/env python3
"""Phase 0C.2: AR6 reference value of the electricity sum-check, real data only.

The paper benchmarks synthetic scenarios against "the 1.2% average error in the
AR6 Scenarios Database" without saying how a scenario's error is aggregated
over decades. This script recomputes that reference on the deposited Real CSVs
(the 901-set) under candidate aggregations and reports which reproduces 1.2%.

It reads ONLY Real_*.csv. Computing sum-check errors of the synthetic
scenarios would evaluate claim X3 at the paper's own configuration, which the
protocol forbids before the freeze; the guard below enforces this.

Usage:  python3 07_sumcheck_reference.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0c_sumcheck_reference.json
"""
import argparse, json, re
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

CATEGORIES = ["C1234", "C56", "C78"]
TOTAL = "SecondaryEle"
FUELS = ["SecondaryEle_Biomass", "SecondaryEle_Coal", "SecondaryEle_Gas", "SecondaryEle_Geothermal",
         "SecondaryEle_Hydro", "SecondaryEle_Nuclear", "SecondaryEle_Oil", "SecondaryEle_Solar",
         "SecondaryEle_Wind"]
PAPER_VALUE = 0.012
canon = lambda s: re.sub(r"[^a-z]", "", str(s).lower())


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def read_real(path):
    if "gen_" in path.name.lower():
        raise SystemExit("Refusing to read a synthetic file before the freeze: " + path.name)
    df = pd.read_csv(path)
    if "Variable" not in df.columns:
        raise SystemExit(f"{path.name}: expected long format with a 'Variable' column")
    years = sorted([c for c in df.columns if re.fullmatch(r"(19|20|21)\d\d", str(c))], key=int)
    scen = "Scenario" if "Scenario" in df.columns else df.columns[0]
    df["_v"] = df["Variable"].map(canon)
    def mat(var):
        sub = df[df["_v"] == canon(var)].drop_duplicates(subset=scen).set_index(scen)
        if sub.empty:
            raise SystemExit(f"{path.name}: variable {var} not found")
        return sub[years].astype(float)
    T = mat(TOTAL)
    F = sum(mat(f).reindex(T.index) for f in FUELS)
    return T.to_numpy(), F.to_numpy(), [int(y) for y in years]


def aggregations(T, F):
    with np.errstate(divide="ignore", invalid="ignore"):
        e = np.abs(T - F) / T                      # scenario x decade relative error (Eq. 3)
        e_cum = np.abs(T.sum(1) - F.sum(1)) / T.sum(1)
    ok = np.isfinite(e)
    per_scen_mean = np.nanmean(np.where(ok, e, np.nan), axis=1)
    per_scen_max = np.nanmax(np.where(ok, e, np.nan), axis=1)
    return {
        "mean_over_decades_then_scenarios": float(np.nanmean(per_scen_mean)),
        "pooled_mean_scenario_decades": float(np.nanmean(e[ok])),
        "cumulative_2020_2100_then_scenarios": float(np.nanmean(e_cum)),
        "max_over_decades_then_scenarios": float(np.nanmean(per_scen_max)),
        "median_of_scenario_means": float(np.nanmedian(per_scen_mean)),
        "pooled_median_scenario_decades": float(np.nanmedian(e[ok])),
        "share_cells_zero_or_missing_total": float(1 - ok.mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).resolve().parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    dep = Path(paths["scenarios3000_dir"]).expanduser()

    Ts, Fs, report = [], [], {"paper_value": PAPER_VALUE, "per_category": {}, "per_decade_mean_901": {}}
    for c in CATEGORIES:
        T, F, years = read_real(dep / f"Real_{c}.csv")
        Ts.append(T); Fs.append(F)
        report["per_category"][c] = {"n_scenarios": int(T.shape[0]), **aggregations(T, F)}
    T, F = np.vstack(Ts), np.vstack(Fs)
    report["pooled_901"] = {"n_scenarios": int(T.shape[0]), **aggregations(T, F)}
    with np.errstate(divide="ignore", invalid="ignore"):
        e = np.abs(T - F) / T
    report["per_decade_mean_901"] = {str(y): float(np.nanmean(e[:, i])) for i, y in enumerate(years)}

    cands = {k: v for k, v in report["pooled_901"].items() if not k.startswith(("n_", "share_"))}
    report["candidates_rounding_to_1.2pct"] = sorted(k for k, v in cands.items() if round(100 * v, 1) == 1.2)
    # two candidates coincide when no cell is missing (the mean of scenario means is then the pooled mean):
    # distances are compared at twelve significant digits and a tie goes to the first name in alphabetical order
    report["closest_candidate"] = min(sorted(cands), key=lambda k: float(f"{abs(cands[k] - PAPER_VALUE):.12g}"))
    report["note"] = ("If exactly one candidate rounds to 1.2%, it is taken as the authors' aggregation "
                      "for X3; if none or several do, the protocol keeps the mean over decades and "
                      "records the ambiguity.")
    dest = Path(__file__).resolve().parent.parent / "results" / "phase0c_sumcheck_reference.json"
    dest.parent.mkdir(exist_ok=True)
    write_lf(dest, json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["pooled_901", "candidates_rounding_to_1.2pct", "closest_candidate"]}, indent=2))


if __name__ == "__main__":
    main()
