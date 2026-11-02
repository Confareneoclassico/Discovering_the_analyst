#!/usr/bin/env python3
"""Phase 0E: model groups behind claim X5, from identifiers and reporting coverage.

Claim X5 asks whether the synthetic ensemble inherits the model mix of the real
one. The paper (SI S2.3 and Table S3) merges the AR6 model versions into
frameworks following Dekker et al. (2023, Nature 624, 309-316) and keeps the
first nine. This script maps every AR6 model name of the 1,202 vetted scenarios
to a group with the mapping of config/paper_values.yaml
(fixed.claims.X5.labels), stops on any name the mapping does not cover or any
listed name that does not occur, and counts scenarios per group and category in
the 1,202 vetted scenarios, the 1,160 scenarios of the D2 rule and the 901-set.
Since the 1,160-set already has the five features complete, the D9 rule removes
a scenario from it only for an incomplete electricity variable. The script
therefore also records, for the removed scenarios, which of the ten electricity
variables of the D9 rule are not reported at all and which miss a decade
between 2020 and 2100.

Finally it fixes the folds of the X5 classifier before the freeze, from
identifiers alone: the 901 scenarios are ordered by category, group and the
SHA-256 of "model|scenario", dealt to folds 1 to 5 in turn (so every category
and every group within a category is spread evenly over the folds), and written in the
order of that key, which is also the row order for training, to
data/derived/x5_folds_901.csv.

It reads identifiers (model, scenario and category from the AR6 metadata, the
two derived scenario lists) and, from the AR6 World CSV, only whether each of
the ten electricity variables has a value in each decade. No scenario value
enters the report. No synthetic file is read and no claim rule is evaluated.
The output contains no timestamp or environment information, so a re-run on the
same inputs reproduces it byte for byte.

Usage:  python3 09_model_groups.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0e_model_groups.json, ../data/derived/x5_folds_901.csv
"""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
AGG = {"C1": "C1234", "C2": "C1234", "C3": "C1234", "C4": "C1234",
       "C5": "C56", "C6": "C56", "C7": "C78", "C8": "C78"}
CATEGORIES = ["C1234", "C56", "C78"]
KEY = ["Model", "Scenario"]
YEARS = [str(y) for y in range(2020, 2101, 10)]
ELEC = ["Secondary Energy|Electricity", "Secondary Energy|Electricity|Biomass",
        "Secondary Energy|Electricity|Coal", "Secondary Energy|Electricity|Gas",
        "Secondary Energy|Electricity|Geothermal", "Secondary Energy|Electricity|Hydro",
        "Secondary Energy|Electricity|Nuclear", "Secondary Energy|Electricity|Oil",
        "Secondary Energy|Electricity|Solar", "Secondary Energy|Electricity|Wind"]   # as in 04_evaluation_subset.py


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counts(df, groups):
    """Scenarios per group and aggregate category, with totals."""
    t = pd.crosstab(df["group"], df["agg"]).reindex(index=groups, columns=CATEGORIES, fill_value=0)
    out = {g: {**{c: int(t.loc[g, c]) for c in CATEGORIES}, "total": int(t.loc[g].sum())} for g in groups}
    out["all"] = {**{c: int(t[c].sum()) for c in CATEGORIES}, "total": int(t.values.sum())}
    return out


def electricity_status(world_path, index):
    """Per scenario of `index` and electricity variable: 'complete', 'gaps' (reported, a decade missing)
    or 'absent' (not reported). Only the presence of values is kept."""
    parts = []
    for chunk in pd.read_csv(world_path, chunksize=200_000, usecols=KEY + ["Region", "Variable"] + YEARS):
        parts.append(chunk[(chunk["Region"] == "World") & chunk["Variable"].isin(ELEC)])
    w = pd.concat(parts, ignore_index=True)
    w["complete"] = w[YEARS].notna().all(axis=1)
    comp = w.pivot_table(index=KEY, columns="Variable", values="complete", aggfunc="max")
    comp = comp.reindex(index=index, columns=ELEC)
    return comp.apply(lambda col: col.map({True: "complete", False: "gaps"}).fillna("absent"))


def x5_folds(df901, n_folds=5):
    """Folds of claim X5 from identifiers only, independent of row order and of any library's RNG."""
    t = df901[KEY + ["agg", "group"]].copy()
    t["key"] = [hashlib.sha256(f"{m}|{s}".encode("utf-8")).hexdigest() for m, s in zip(t["Model"], t["Scenario"])]
    t = t.sort_values(["agg", "group", "key"]).reset_index(drop=True)
    t["fold"] = t.index % n_folds + 1
    return t.sort_values("key").reset_index(drop=True)[["key"] + KEY + ["agg", "group", "fold"]]


def check_counts(name, table, expected):
    got = {c: table["all"][c] for c in CATEGORIES}
    if got != expected:
        raise SystemExit(f"{name}: expected {expected} scenarios per category, found {got}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    cfg = yaml.safe_load(open(ROOT / "config" / "paper_values.yaml"))
    lab = cfg["fixed"]["claims"]["X5"]["labels"]
    levels = cfg["factors"]["G1_population"]["levels"]

    to_group = {v: g for g, vs in lab["versions"].items() for v in vs}
    to_group.update({v: "not grouped" for v in lab["not_grouped"]})
    groups = sorted(lab["versions"]) + ["not grouped"]

    meta_path = Path(paths["ar6_metadata_xlsx"]).expanduser()
    world_path = Path(paths["ar6_world_csv"]).expanduser()
    if world_path.stat().st_size < 1024:
        raise SystemExit(f"{world_path} is a Git LFS pointer, not the data: restore it as in DATA.md, B2")
    dropped_path = ROOT / "data" / "derived" / "dropped42_2020_2100_5features.csv"
    kept_path = ROOT / "data" / "derived" / "kept901_5feat+elec10.csv"
    for p in (meta_path, world_path, dropped_path, kept_path):
        if "gen_" in p.name.lower():
            raise SystemExit("Refusing to read a synthetic file before the freeze: " + p.name)

    meta = pd.read_excel(meta_path, sheet_name="meta_Ch3vetted_withclimate", usecols=KEY + ["Category"])
    meta = meta[meta["Category"].isin(AGG)].assign(agg=lambda d: d["Category"].map(AGG))
    if meta.duplicated(KEY).any():
        raise SystemExit("duplicate model-scenario pairs in the metadata")
    names = set(meta["Model"])
    unknown = sorted(names - set(to_group))
    unused = sorted(set(to_group) - names)
    if unknown or unused:
        raise SystemExit(f"mapping does not match the metadata. Unmapped names: {unknown}. "
                         f"Listed names not found: {unused}")
    meta["group"] = meta["Model"].map(to_group)

    dropped = pd.read_csv(dropped_path)[KEY]
    kept = pd.read_csv(kept_path)[KEY]
    in_dropped = meta.set_index(KEY).index.isin(dropped.set_index(KEY).index)
    in_kept = meta.set_index(KEY).index.isin(kept.set_index(KEY).index)
    if in_dropped.sum() != len(dropped) or in_kept.sum() != len(kept) or (in_dropped & in_kept).any():
        raise SystemExit("derived lists do not nest in the 1,202 vetted scenarios")

    sets = {"1202": meta, "1160": meta[~in_dropped], "901": meta[in_kept]}
    table = {k: counts(v, groups) for k, v in sets.items()}
    for k in sets:
        check_counts(k, table[k], levels[k]["counts"])

    removed_d9 = counts(meta[~in_dropped & ~in_kept], groups)
    m1160 = sets["1160"].set_index(KEY)
    status = electricity_status(world_path, m1160.index)
    kept_mask = m1160.index.isin(kept.set_index(KEY).index)
    complete = (status == "complete").all(axis=1)
    if not complete[kept_mask].all() or complete[~kept_mask].any():
        raise SystemExit("the D9 rule does not separate the 901-set from the rest of the 1,160-set "
                         "on the ten electricity variables")
    removed = status[~kept_mask].join(m1160["group"])
    elec_removed = {}
    for g, sub in removed.groupby("group"):
        elec_removed[g] = {"n_removed": int(len(sub)),
                           "absent": {v: int((sub[v] == "absent").sum()) for v in ELEC if (sub[v] == "absent").any()},
                           "gaps": {v: int((sub[v] == "gaps").sum()) for v in ELEC if (sub[v] == "gaps").any()}}
    lost_c78 = {g: table["1202"][g]["C78"] - table["901"][g]["C78"] for g in groups}
    lost_c78["all"] = table["1202"]["all"]["C78"] - table["901"]["all"]["C78"]

    present = [g for g in groups if g != "not grouped" and table["901"][g]["total"] > 0]
    if table["901"]["not grouped"]["total"] > 0:
        raise SystemExit("a scenario of an ungrouped model is in the 901-set")
    if present != sorted(lab["used"]):
        raise SystemExit(f"labels present in the 901-set {present} differ from the configured labels {lab['used']}")
    n901 = table["901"]["all"]["total"]
    majority = max(present, key=lambda g: table["901"][g]["total"])
    majority_cat = {}
    for c in CATEGORIES:
        g = max(present, key=lambda g: table["901"][g][c])
        n_c = table["901"]["all"][c]
        majority_cat[c] = {"group": g, "n": table["901"][g][c], "n_total": n_c,
                           "rate": round(table["901"][g][c] / n_c, 6)}
    by_name = {}
    for name in sorted(lab["not_grouped"]):
        by_name[name] = {k: {c: int(((v["Model"] == name) & (v["agg"] == c)).sum()) for c in CATEGORIES}
                         for k, v in sets.items()}

    folds = x5_folds(sets["901"])
    folds_path = ROOT / "data" / "derived" / "x5_folds_901.csv"
    folds.to_csv(folds_path, index=False)
    fold_counts = {g: [int(((folds["group"] == g) & (folds["fold"] == f)).sum()) for f in range(1, 6)] for g in present}
    fold_counts["all"] = [int((folds["fold"] == f).sum()) for f in range(1, 6)]
    fold_counts_cat = {c: [int(((folds["agg"] == c) & (folds["fold"] == f)).sum()) for f in range(1, 6)]
                       for c in CATEGORIES}

    report = {
        "inputs_sha256": {"B1, AR6 metadata_indicators v1.1": sha256(meta_path),
                          "B2, AR6 World CSV v1.1": sha256(world_path),
                          "data/derived/" + dropped_path.name: sha256(dropped_path),
                          "data/derived/" + kept_path.name: sha256(kept_path)},
        "definitions": {
            "1202": "meta_Ch3vetted_withclimate, categories C1 to C8 (Extended Data Table 1)",
            "1160": "1202 minus data/derived/dropped42_2020_2100_5features.csv (D2 rule, SI S3.1 counts)",
            "901": "data/derived/kept901_5feat+elec10.csv (D9 rule, the deposited Real_*.csv)",
            "groups": "AR6 model names merged into frameworks as in config/paper_values.yaml, "
                      "fixed.claims.X5.labels (SI S2.3 and Table S3)",
            "electricity": "World region, decades 2020-2100; absent = variable not reported for the scenario, "
                           "gaps = reported with at least one decade missing",
        },
        "mapping": {g: sorted(m for m, gg in to_group.items() if gg == g) for g in groups},
        "counts": table,
        "removed_by_D9_rule_1160_to_901": removed_d9,
        "lost_in_C78_1202_to_901": lost_c78,
        "not_grouped_by_model_name": by_name,
        "electricity_variables_incomplete_among_removed": elec_removed,
        "paper_nine_absent_from_901": [g for g in lab["paper_nine"] if table["901"][g]["total"] == 0],
        "labels_901": present,
        "n_labels_901": len(present),
        "smallest_label_901": {"group": min(present, key=lambda g: table["901"][g]["total"]),
                               "n": min(table["901"][g]["total"] for g in present)},
        "majority_label_901": {"group": majority, "n": table["901"][majority]["total"], "n_total": n901,
                               "rate": round(table["901"][majority]["total"] / n901, 6)},
        "majority_label_901_by_category": majority_cat,
        "x5_folds": {
            "file": "data/derived/x5_folds_901.csv",
            "sha256": sha256(folds_path),
            "rule": "order the 901 scenarios by category, group and SHA-256 of 'model|scenario'; deal folds 1-5 "
                    "in turn; store and train in the order of the SHA-256 key",
            "scenarios_per_fold_by_group": fold_counts,
            "scenarios_per_fold_by_category": fold_counts_cat,
        },
    }
    dest = ROOT / "results" / "phase0e_model_groups.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n")

    print(f"{'group':12s}" + "".join(f"{k:>18s}" for k in sets) + f"{'removed by D9':>18s}")
    for g in groups + ["all"]:
        cells = [table[k][g] for k in sets] + [removed_d9[g]]
        print(f"{g:12s}" + "".join(f"{c['C1234']}/{c['C56']}/{c['C78']} ({c['total']})".rjust(18) for c in cells))
    print("Paper's nine absent from the 901-set:", report["paper_nine_absent_from_901"])
    print("C78 lost from 1,202 to 901:", {g: v for g, v in lost_c78.items() if v})
    for g, r in elec_removed.items():
        print(f"Removed {g} ({r['n_removed']}): absent {r['absent']}; gaps {r['gaps']}")
    print("Labels in the 901-set:", len(present), present)
    print("Majority label:", report["majority_label_901"])
    print("Majority by category:", majority_cat)
    print("Not grouped by name:", by_name)
    print("Folds:", fold_counts["all"], fold_counts_cat, "->", folds_path.relative_to(ROOT))
    print("Written:", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
