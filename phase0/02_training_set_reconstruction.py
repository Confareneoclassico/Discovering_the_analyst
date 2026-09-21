#!/usr/bin/env python3
"""Phase 0.2 — reconstruct the training set from the raw AR6 World CSV.

Goal (DISCREPANCIES.md D2): starting from the 1,202 vetted scenarios, find
the filter that yields the SI S3.1 training counts (C1234=680, C56=308,
C78=172; total 1,160), i.e. identify the 42 silently dropped scenarios.

Strategy: test completeness filters on the candidate key variables over the
2010–2100 (and, per D5, 2020–2100) grids, in increasing strictness, and
report which — if any — reproduces the counts exactly. Everything is logged;
failure to reproduce is a finding, not an error.

Runs on the analysis machine (World CSV ~400 MB, path in local_paths.yaml).
Output: ../results/phase0_training_set.json and
        ../data/derived/training_candidates_<filter>.csv

NOTE: the AR6 variable names for the paper's key variables must be confirmed
against the Deep-IAM notebooks (Kmeans / data_world_single_variable.ipynb)
before trusting results — edit KEY_VARIABLES below if the notebooks differ.
"""
import json, argparse, itertools
from pathlib import Path
import pandas as pd
import yaml

# Candidate mapping paper-name -> AR6 'Variable' string. CONFIRM AGAINST CODE (D3).
KEY_VARIABLES = {
    "PrimaryEnergy_Coal": "Primary Energy|Coal",
    "PrimaryEnergy_Oil": "Primary Energy|Oil",
    "PrimaryEnergy_Gas": "Primary Energy|Gas",
    "FinalEnergy_Liquid": "Final Energy|Liquids",
    "CarbonSequestration": "Carbon Sequestration|CCS",   # alt: "Carbon Sequestration|CCS|Biomass"? confirm
    "KyotoGases": "Emissions|Kyoto Gases",
}
AGG = {"C1234": ["C1", "C2", "C3", "C4"], "C56": ["C5", "C6"], "C78": ["C7", "C8"]}
TARGET = {"C1234": 680, "C56": 308, "C78": 172}
GRIDS = {"2010_2100": list(range(2010, 2101, 10)), "2020_2100": list(range(2020, 2101, 10))}


def load_world_subset(csv_path, variables, chunksize=200_000):
    """Stream the World CSV, keeping only rows for the requested variables."""
    keep = []
    usecols = None
    for chunk in pd.read_csv(csv_path, chunksize=chunksize, usecols=usecols):
        keep.append(chunk[chunk["Variable"].isin(variables)])
    return pd.concat(keep, ignore_index=True)


def completeness_table(df_long, years):
    """scenario-key x variable -> True if all `years` present and non-null."""
    ycols = [str(y) for y in years if str(y) in df_long.columns] or \
            [y for y in years if y in df_long.columns]
    ok = df_long[ycols].notna().all(axis=1)
    t = df_long.assign(_complete=ok).pivot_table(
        index=["Model", "Scenario"], columns="Variable", values="_complete",
        aggfunc="max", fill_value=False)
    return t.astype(bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))

    meta = pd.read_excel(paths["ar6_metadata_xlsx"], sheet_name="meta_Ch3vetted_withclimate")
    meta["agg"] = meta["Category"].map({c: a for a, cs in AGG.items() for c in cs})
    vetted = meta.set_index(["Model", "Scenario"])["agg"]

    world = load_world_subset(paths["ar6_world_csv"], set(KEY_VARIABLES.values()))
    world = world[world["Region"] == "World"] if "Region" in world.columns else world

    report = {"target": TARGET, "filters_tested": []}
    feature_vars = [v for k, v in KEY_VARIABLES.items() if k != "KyotoGases"]

    for grid_name, years in GRIDS.items():
        comp = completeness_table(world, years)
        comp = comp.reindex(vetted.index).fillna(False)
        # filter variants: require completeness on the 5 features, +/- Kyoto Gases
        variants = {
            "5features": feature_vars,
            "5features+kyoto": feature_vars + [KEY_VARIABLES["KyotoGases"]],
        }
        for vname, vars_req in variants.items():
            have = [v for v in vars_req if v in comp.columns]
            mask = comp[have].all(axis=1) if have else pd.Series(False, index=comp.index)
            counts = vetted[mask].value_counts().to_dict()
            entry = {"grid": grid_name, "variant": vname,
                     "missing_variable_columns": sorted(set(vars_req) - set(comp.columns)),
                     "counts": {a: int(counts.get(a, 0)) for a in TARGET},
                     "exact_match": all(counts.get(a, 0) == n for a, n in TARGET.items())}
            report["filters_tested"].append(entry)
            if entry["exact_match"]:
                dropped = vetted[~mask]
                dpath = Path(__file__).parent.parent / "data" / "derived" / f"dropped42_{grid_name}_{vname}.csv"
                dpath.parent.mkdir(parents=True, exist_ok=True)
                dropped.reset_index().to_csv(dpath, index=False)
                entry["dropped_list"] = str(dpath)

    report["conclusion"] = ("REPRODUCED" if any(e["exact_match"] for e in report["filters_tested"])
                            else "NOT REPRODUCED under tested filters — finding (D2)")
    out = Path(__file__).parent.parent / "results" / "phase0_training_set.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
