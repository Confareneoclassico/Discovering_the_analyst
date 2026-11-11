#!/usr/bin/env python3
"""Phase 0.4: reconstruct the second undocumented drop, from 1,160 to 901 scenarios (D9).

The deposited Real_*.csv hold 554/237/110 scenarios (901 in all), the counts of
the paper's figure legends (Fig. 4a, n = 554; ED Fig. 2, "AR6, n = 554/237/110")
and of the testing samples of Table 1, Experiment I. They are not the training
counts of SI S3.1 (680/308/172). Secondary-data-generate.ipynb (v1.0.1)
computes "the intersection of the models and scenarios contained in each
variable" over sixteen variables: the five features, Kyoto Gases and ten
electricity variables, with Carbon Sequestration read from a pre-imputed file.

Four completeness rules on the decades 2020-2100 are tested against the 1,202
vetted scenarios: the four features other than Carbon Sequestration plus the
ten electricity variables, with and without raw Carbon Sequestration, with and
without native Kyoto Gases. Result: all five features and the ten electricity
variables complete, Kyoto Gases not required, reproduces 554/237/110 exactly.
Since this rule contains the D2 rule (the five features complete), the 901-set
lies inside the 1,160-set; 09_model_groups.py checks the nesting.

The Kyoto Gases tested here are the native "Emissions|Kyoto Gases". The
pipeline uses an infilled diagnostic instead, which every vetted scenario has
in every decade from 2020 to 2100, so on this grid Kyoto Gases cannot bind
(D16). Phase 0F confirms the reconstructed set
scenario by scenario against the deposited values (10_deposit_crosswalk.py).

Usage:  python3 04_evaluation_subset.py [--paths ../config/local_paths.yaml]
Needs:  ar6_metadata_xlsx and ar6_world_csv in local_paths.yaml (DATA.md, B1 and B2)
Output: ../results/phase0_evaluation_subset.json and, for a rule that reproduces the
        counts, ../data/derived/kept901_<rule>.csv (the scenarios kept)
"""
import argparse, json
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
FEATURES5 = {
    "PrimaryEnergy_Coal": "Primary Energy|Coal",
    "PrimaryEnergy_Oil": "Primary Energy|Oil",
    "PrimaryEnergy_Gas": "Primary Energy|Gas",
    "FinalEnergy_Liquid": "Final Energy|Liquids",
    "CarbonSequestration": "Carbon Sequestration|CCS",
}
KYOTO = "Emissions|Kyoto Gases"                     # native variable; not the one the pipeline uses (D16)
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


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def completeness_table(df_long, years):
    """Scenario x variable: True if the variable has a value in every one of `years`."""
    ycols = [str(y) for y in years]
    missing = [y for y in ycols if y not in df_long.columns]
    if missing:
        raise SystemExit(f"year columns missing from the World CSV: {missing}")
    t = pd.DataFrame({"Model": df_long["Model"], "Scenario": df_long["Scenario"], "Variable": df_long["Variable"],
                      "_complete": df_long[ycols].notna().all(axis=1)})
    return t.pivot_table(index=["Model", "Scenario"], columns="Variable", values="_complete",
                         aggfunc="max", fill_value=False).astype(bool)


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

    allvars = set(FEATURES5.values()) | {KYOTO} | set(ELEC)
    keep = []
    for chunk in pd.read_csv(Path(paths["ar6_world_csv"]).expanduser(), chunksize=200_000):
        keep.append(chunk[(chunk["Region"] == "World") & chunk["Variable"].isin(allvars)])
    world = pd.concat(keep, ignore_index=True)

    comp = completeness_table(world, YEARS).reindex(vetted.index, fill_value=False)
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
        absent = sorted(set(req) - set(comp.columns))          # variables no scenario reports at all
        mask = comp[req].all(axis=1) if not absent else pd.Series(False, index=comp.index)
        counts = vetted[mask].value_counts().to_dict()
        entry = {"variant": name,
                 "missing_variable_columns": absent,
                 "counts": {a: int(counts.get(a, 0)) for a in TARGET},
                 "exact_match": all(counts.get(a, 0) == n for a, n in TARGET.items())}
        if entry["exact_match"]:
            out = ROOT / "data" / "derived" / f"kept901_{name.split()[0]}.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            write_lf(out, vetted[mask].reset_index().to_csv(index=False))
            entry["kept_list"] = out.relative_to(ROOT).as_posix()
        report["filters_tested"].append(entry)

    report["conclusion"] = ("REPRODUCED" if any(e["exact_match"] for e in report["filters_tested"])
                            else "NOT REPRODUCED under the tested rules: a finding (D9)")
    out = ROOT / "results" / "phase0_evaluation_subset.json"
    out.parent.mkdir(exist_ok=True)
    write_lf(out, json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
