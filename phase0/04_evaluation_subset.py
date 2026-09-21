#!/usr/bin/env python3
"""Phase 0.4 — reconstruct the SECOND undocumented drop (D9): 1,160 -> 901.

The deposited Real_*.csv hold 554/237/110 scenarios (total 901), matching the
paper's own figure legends (Fig. 4a n=554; ED Fig. 2 'AR6, n=554/237/110')
and Table 1 Experiment I testing samples — not the SI S3.1 training counts
(680/308/172). Secondary-data-generate.ipynb (v1.0.1) computes "the
intersection of the models and scenarios contained in each variable" over
the extended 16-variable set (5 features + Kyoto + 10 electricity fuel-level
variables), with Carbon Sequestration pre-imputed.

Hypothesis tested here: 901 = scenarios with complete 2020–2100 coverage on
the 16-variable set, with Carbon Sequestration NOT required (imputed).
Variants toggle CS and Kyoto requirements to find the exact rule.

Output: ../results/phase0_evaluation_subset.json
        ../data/derived/dropped_1160_to_901_<variant>.csv on exact match
"""
import json, argparse
from pathlib import Path
import pandas as pd
import yaml

FEATURES5 = {
    "PrimaryEnergy_Coal": "Primary Energy|Coal",
    "PrimaryEnergy_Oil": "Primary Energy|Oil",
    "PrimaryEnergy_Gas": "Primary Energy|Gas",
    "FinalEnergy_Liquid": "Final Energy|Liquids",
    "CarbonSequestration": "Carbon Sequestration|CCS",
}
KYOTO = "Emissions|Kyoto Gases"
ELEC = ["Secondary Energy|Electricity",
        "Secondary Energy|Electricity|Biomass",
        "Secondary Energy|Electricity|Coal",
        "Secondary Energy|Electricity|Gas",
        "Secondary Energy|Electricity|Geothermal",
        "Secondary Energy|Electricity|Hydro",
        "Secondary Energy|Electricity|Nuclear",
        "Secondary Energy|Electricity|Oil",
        "Secondary Energy|Electricity|Solar",
        "Secondary Energy|Electricity|Wind"]
AGG = {"C1234": ["C1", "C2", "C3", "C4"], "C56": ["C5", "C6"], "C78": ["C7", "C8"]}
TARGET = {"C1234": 554, "C56": 237, "C78": 110}
YEARS = list(range(2020, 2101, 10))


def completeness_table(df_long, years):
    ycols = [c for c in ([str(y) for y in years] if str(years[0]) in df_long.columns else years)
             if c in df_long.columns]
    ok = df_long[ycols].notna().all(axis=1)
    return (df_long.assign(_c=ok)
            .pivot_table(index=["Model", "Scenario"], columns="Variable",
                         values="_c", aggfunc="max", fill_value=False).astype(bool))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))

    meta = pd.read_excel(paths["ar6_metadata_xlsx"], sheet_name="meta_Ch3vetted_withclimate")
    meta["agg"] = meta["Category"].map({c: a for a, cs in AGG.items() for c in cs})
    vetted = meta.set_index(["Model", "Scenario"])["agg"]

    allvars = set(FEATURES5.values()) | {KYOTO} | set(ELEC)
    keep = []
    for chunk in pd.read_csv(paths["ar6_world_csv"], chunksize=200_000):
        keep.append(chunk[chunk["Variable"].isin(allvars)])
    world = pd.concat(keep, ignore_index=True)
    if "Region" in world.columns:
        world = world[world["Region"] == "World"]

    comp = completeness_table(world, YEARS).reindex(vetted.index).fillna(False)
    f4 = [v for k, v in FEATURES5.items() if k != "CarbonSequestration"]
    cs = FEATURES5["CarbonSequestration"]
    variants = {
        "4feat+elec10 (CS imputed, no Kyoto)": f4 + ELEC,
        "4feat+elec10+kyoto (CS imputed)": f4 + ELEC + [KYOTO],
        "5feat+elec10 (CS required, no Kyoto)": f4 + [cs] + ELEC,
        "5feat+elec10+kyoto (all required)": f4 + [cs] + ELEC + [KYOTO],
    }
    report = {"target": TARGET, "years": f"{YEARS[0]}-{YEARS[-1]}", "filters_tested": []}
    for name, req in variants.items():
        have = [v for v in req if v in comp.columns]
        mask = comp[have].all(axis=1)
        counts = vetted[mask].value_counts().to_dict()
        entry = {"variant": name,
                 "missing_variable_columns": sorted(set(req) - set(comp.columns)),
                 "counts": {a: int(counts.get(a, 0)) for a in TARGET},
                 "exact_match": all(counts.get(a, 0) == n for a, n in TARGET.items())}
        if entry["exact_match"]:
            out = Path(__file__).parent.parent / "data" / "derived" / \
                  f"kept901_{name.split()[0]}.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            vetted[mask].reset_index().to_csv(out, index=False)
            entry["kept_list"] = str(out)
        report["filters_tested"].append(entry)

    report["conclusion"] = ("REPRODUCED" if any(e["exact_match"] for e in report["filters_tested"])
                            else "NOT REPRODUCED under tested variants — refine (D9)")
    out = Path(__file__).parent.parent / "results" / "phase0_evaluation_subset.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
