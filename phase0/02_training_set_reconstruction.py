#!/usr/bin/env python3
"""Phase 0.2: reconstruct the training set from the AR6 World CSV (D2).

Starting from the 1,202 vetted scenarios, find the filter that yields the
training counts of SI S3.1 (C1234 = 680, C56 = 308, C78 = 172; total 1,160),
that is, identify the 42 scenarios dropped without a stated rule.

Four completeness filters are tested: the five feature variables, with and
without native Kyoto Gases, on the decades 2010-2100 and 2020-2100. A variable
is complete for a scenario when it has a value in every decade of the grid.
Every filter is logged; failing to reproduce the counts would be a finding, not
an error. Result: complete 2020-2100 coverage of the five features, Kyoto Gases
not required, reproduces the counts exactly.

The AR6 names of the five features are confirmed by Phase 0F, which matches
the deposited real scenarios to these variables value by value
(10_deposit_crosswalk.py). The Kyoto Gases tested here are the native
"Emissions|Kyoto Gases". The pipeline uses an infilled diagnostic instead, which
every vetted scenario has in every decade from 2020 to 2100 (it starts in 2015,
so it has no 2010 value): on the 2020-2100 grid of the reproducing filter it
cannot bind (D16).

Usage:  python3 02_training_set_reconstruction.py [--paths ../config/local_paths.yaml]
Needs:  ar6_metadata_xlsx and ar6_world_csv in local_paths.yaml (DATA.md, B1 and B2)
Output: ../results/phase0_training_set.json and, for a filter that reproduces the
        counts, ../data/derived/dropped42_<grid>_<variant>.csv (the dropped scenarios)
"""
import argparse, json
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
KEY_VARIABLES = {
    "PrimaryEnergy_Coal": "Primary Energy|Coal",
    "PrimaryEnergy_Oil": "Primary Energy|Oil",
    "PrimaryEnergy_Gas": "Primary Energy|Gas",
    "FinalEnergy_Liquid": "Final Energy|Liquids",
    "CarbonSequestration": "Carbon Sequestration|CCS",
    "KyotoGases": "Emissions|Kyoto Gases",          # native variable; not the one the pipeline uses (D16)
}
AGG = {"C1234": ["C1", "C2", "C3", "C4"], "C56": ["C5", "C6"], "C78": ["C7", "C8"]}
TARGET = {"C1234": 680, "C56": 308, "C78": 172}
GRIDS = {"2010_2100": list(range(2010, 2101, 10)), "2020_2100": list(range(2020, 2101, 10))}


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def load_world_subset(csv_path, variables, chunksize=200_000):
    """World-region rows of the requested variables, streamed from the World CSV."""
    keep = []
    for chunk in pd.read_csv(csv_path, chunksize=chunksize):
        keep.append(chunk[(chunk["Region"] == "World") & chunk["Variable"].isin(variables)])
    return pd.concat(keep, ignore_index=True)


def completeness_table(df_long, years):
    """Scenario x variable: True if the variable has a value in every one of `years`."""
    ycols = [str(y) for y in years]
    missing = [y for y in ycols if y not in df_long.columns]
    if missing:
        raise SystemExit(f"year columns missing from the World CSV: {missing}")
    t = pd.DataFrame({"Model": df_long["Model"], "Scenario": df_long["Scenario"], "Variable": df_long["Variable"],
                      "_complete": df_long[ycols].notna().all(axis=1)})
    t = t.pivot_table(index=["Model", "Scenario"], columns="Variable", values="_complete",
                      aggfunc="max", fill_value=False)
    return t.astype(bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))

    meta = pd.read_excel(Path(paths["ar6_metadata_xlsx"]).expanduser(), sheet_name="meta_Ch3vetted_withclimate")
    meta["agg"] = meta["Category"].map({c: a for a, cs in AGG.items() for c in cs})
    vetted = meta.set_index(["Model", "Scenario"])["agg"]
    if not vetted.index.is_unique:
        raise SystemExit("duplicate model-scenario pairs in the metadata")

    world = load_world_subset(Path(paths["ar6_world_csv"]).expanduser(), set(KEY_VARIABLES.values()))

    report = {"target": TARGET, "filters_tested": []}
    feature_vars = [v for k, v in KEY_VARIABLES.items() if k != "KyotoGases"]

    for grid_name, years in GRIDS.items():
        comp = completeness_table(world, years).reindex(vetted.index, fill_value=False)
        variants = {
            "5features": feature_vars,
            "5features+kyoto": feature_vars + [KEY_VARIABLES["KyotoGases"]],
        }
        for vname, vars_req in variants.items():
            absent = sorted(set(vars_req) - set(comp.columns))     # variables no scenario reports at all
            mask = comp[vars_req].all(axis=1) if not absent else pd.Series(False, index=comp.index)
            counts = vetted[mask].value_counts().to_dict()
            entry = {"grid": grid_name, "variant": vname,
                     "missing_variable_columns": absent,
                     "counts": {a: int(counts.get(a, 0)) for a in TARGET},
                     "exact_match": all(counts.get(a, 0) == n for a, n in TARGET.items())}
            report["filters_tested"].append(entry)
            if entry["exact_match"]:
                dpath = ROOT / "data" / "derived" / f"dropped42_{grid_name}_{vname}.csv"
                dpath.parent.mkdir(parents=True, exist_ok=True)
                write_lf(dpath, vetted[~mask].reset_index().to_csv(index=False))
                entry["dropped_list"] = dpath.relative_to(ROOT).as_posix()

    report["conclusion"] = ("REPRODUCED" if any(e["exact_match"] for e in report["filters_tested"])
                            else "NOT REPRODUCED under the tested filters: a finding (D2)")
    out = ROOT / "results" / "phase0_training_set.json"
    out.parent.mkdir(exist_ok=True)
    write_lf(out, json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
