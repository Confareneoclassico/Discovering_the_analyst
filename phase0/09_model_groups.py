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

Finally it fixes the folds of the X5 classifier before the freeze. Scenarios
of the 901-set that duplicate one another form one unit, so that no scenario is
predicted by a classifier that has seen its duplicate. Two scenarios are
duplicates when their AR6 values on the fifteen variables of the D9 rule
coincide in every decade 2020-2100, that is, when every value differs by at
most DUP_TOL times the variable's largest absolute value in the 901-set. The
tolerance only absorbs differences of floating-point representation: the script
stops unless duplicates agree to DUP_BAND, a thousand times tighter, and it
reports how far the closest pair of distinct scenarios lies. The units are
ordered by category, group and the SHA-256 of "model|scenario" (the smallest
among a unit's members) and dealt to folds 1 to 5 in turn, so the units of
every category, and of every group within it, are spread evenly over the folds.
The table is written in the order of the scenarios' keys, which is also the
row order for training, to data/derived/x5_folds_901.csv.

It reads identifiers (model, scenario and category from the AR6 metadata, the
two derived scenario lists) and, from the AR6 World CSV, the fifteen variables
of the D9 rule: whether each electricity variable has a value in each decade,
and how far the scenarios of the 901-set lie from one another. Of the values,
only counts of pairs and two relative deviations enter the outputs. No
synthetic file is read and no claim rule is evaluated.
The outputs contain no timestamp or environment information and are written
with LF line endings, so a re-run on the same inputs reproduces them byte for
byte.

Usage:  python3 09_model_groups.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0e_model_groups.json, ../data/derived/x5_folds_901.csv
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
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
DUP_TOL = 1e-6      # duplicates: every value within this share of the variable's largest absolute value
DUP_BAND = 1e-9     # duplicates must in fact agree to this, so that DUP_TOL decides nothing
NEAR = [1e-3, 1e-2]  # pairs of distinct scenarios closer than these shares are counted, for the record


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sig(x, n=3):
    """Round to n significant digits so that the report does not depend on float noise."""
    return float(f"{x:.{n}g}")


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def counts(df, groups):
    """Scenarios per group and aggregate category, with totals."""
    t = pd.crosstab(df["group"], df["agg"]).reindex(index=groups, columns=CATEGORIES, fill_value=0)
    out = {g: {**{c: int(t.loc[g, c]) for c in CATEGORIES}, "total": int(t.loc[g].sum())} for g in groups}
    out["all"] = {**{c: int(t[c].sum()) for c in CATEGORIES}, "total": int(t.values.sum())}
    return out


def read_world(world_path, variables):
    """World-region rows of the requested variables, decades 2020-2100."""
    parts = []
    for chunk in pd.read_csv(world_path, chunksize=200_000, usecols=KEY + ["Region", "Variable"] + YEARS):
        parts.append(chunk[(chunk["Region"] == "World") & chunk["Variable"].isin(variables)])
    return pd.concat(parts, ignore_index=True)


def electricity_status(w, index):
    """Per scenario of `index` and electricity variable: 'complete', 'gaps' (reported, a decade missing)
    or 'absent' (not reported). Only the presence of values is kept."""
    w = w[w["Variable"].isin(ELEC)].copy()
    w["complete"] = w[YEARS].notna().all(axis=1)
    comp = w.pivot_table(index=KEY, columns="Variable", values="complete", aggfunc="max")
    comp = comp.reindex(index=index, columns=ELEC)
    return comp.apply(lambda col: col.map({True: "complete", False: "gaps"}).fillna("absent"))


def scaled_values(w, df901, variables):
    """AR6 values of the scenarios of df901 (one row each, in its order) on `variables` and the nine decades,
    each variable divided by its largest absolute value over these scenarios and decades."""
    if w.duplicated(KEY + ["Variable"]).any():
        raise SystemExit("duplicate model-scenario-variable rows in the World CSV")
    vals = w.set_index(KEY + ["Variable"])[YEARS].astype(float)
    blocks = [vals.reindex(pd.MultiIndex.from_arrays([df901["Model"], df901["Scenario"], [v] * len(df901)])).to_numpy()
              for v in variables]
    if any(np.isnan(b).any() for b in blocks):
        raise SystemExit("a scenario of the 901-set is incomplete on the fifteen variables of the D9 rule")
    scale = [np.abs(b).max() for b in blocks]
    if min(scale) <= 0:
        raise SystemExit("a variable of the D9 rule is zero throughout the 901-set")
    return np.hstack([b / m for b, m in zip(blocks, scale)])


def coincident_groups(S, tol, near):
    """Groups of rows of S that coincide. Two rows are linked when they differ by at most tol in every column,
    and a group is a set of rows connected by links. Returns one label per row (the position of the first row
    of its group), the largest deviation between two rows of a group, the smallest between rows of different
    groups, and the pairs of rows of different groups that differ by at most max(near), with their deviation.
    A deviation between two rows is their largest absolute difference over the columns."""
    n = len(S)
    label = np.arange(n)
    for i in range(n - 1):
        d = np.abs(S[i + 1:] - S[i]).max(axis=1)
        for j in np.nonzero(d <= tol)[0] + i + 1:
            a, b = sorted((label[i], label[j]))
            label[label == b] = a
    within, between, pairs = 0.0, np.inf, []
    for i in range(n - 1):
        d = np.abs(S[i + 1:] - S[i]).max(axis=1)
        same = label[i + 1:] == label[i]
        if same.any():
            within = max(within, float(d[same].max()))
        if (~same).any():
            between = min(between, float(d[~same].min()))
        for j in np.nonzero(~same & (d <= max(near)))[0]:
            pairs.append((i, i + 1 + int(j), float(d[j])))
    return label, within, between, pairs


def x5_folds(df901, same_values, n_folds=5):
    """Folds of claim X5, independent of row order and of any library's RNG.

    same_values holds one label per scenario of df901: scenarios with the same label are duplicates. They form
    one unit, keyed by the smallest SHA-256 of 'model|scenario' among its members. Units are ordered by
    category, group and key and dealt to the folds in turn."""
    t = df901[KEY + ["agg", "group"]].copy()
    t["key"] = [hashlib.sha256(f"{m}|{s}".encode("utf-8")).hexdigest() for m, s in zip(t["Model"], t["Scenario"])]
    t["same"] = list(same_values)
    t = t.sort_values("key").reset_index(drop=True)
    size = t["same"].map(t["same"].value_counts())
    t["unit"] = t.groupby("same")["key"].transform("min")
    t["duplicate_group"] = ""
    stats = {"n_groups": 0, "n_scenarios": int((size > 1).sum()), "largest_group": int(size.max()),
             "groups_split_by_dealing_scenarios_singly": 0}
    single = t.sort_values(["agg", "group", "key"]).reset_index(drop=True)
    single_fold = pd.Series(single.index % n_folds + 1, index=single["key"])   # the dealing without units, for the record
    for _, members in t[size > 1].groupby("same", sort=False):          # in the order of the smallest key
        if members["agg"].nunique() > 1 or members["group"].nunique() > 1:
            raise SystemExit("a group of duplicates spans categories or model groups: the fold rule does not cover it")
        stats["n_groups"] += 1
        stats["groups_split_by_dealing_scenarios_singly"] += int(single_fold[members["key"]].nunique() > 1)
        t.loc[members.index, "duplicate_group"] = f"D{stats['n_groups']:02d}"
    units = t.drop_duplicates("unit").sort_values(["agg", "group", "unit"]).reset_index(drop=True)
    t["fold"] = t["unit"].map(pd.Series(units.index % n_folds + 1, index=units["unit"]))
    stats["n_units"] = int(len(units))
    return t[["key"] + KEY + ["agg", "group", "duplicate_group", "fold"]], stats


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
    E = cfg["fixed"]["evaluation_set_E"]
    raw15 = [E["ar6_variables"][v] for v in E["key_variables"] + E["electricity"] if v != "Kyoto_Gases"]
    if len(raw15) != 15 or not set(ELEC) <= set(raw15):
        raise SystemExit("evaluation_set_E.ar6_variables does not hold the fifteen variables of the D9 rule")

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
    world = read_world(world_path, raw15)
    status = electricity_status(world, m1160.index)
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

    S = scaled_values(world, sets["901"], raw15)
    same_values, within, between, close = coincident_groups(S, DUP_TOL, NEAR)
    if within > DUP_BAND:
        raise SystemExit(f"scenarios treated as duplicates differ by {within:.3g} of a variable's largest value, more "
                         f"than {DUP_BAND}: the tolerance {DUP_TOL} would decide which scenarios are duplicates")
    folds, duplicates = x5_folds(sets["901"], same_values)
    folds_path = ROOT / "data" / "derived" / "x5_folds_901.csv"
    write_lf(folds_path, folds.to_csv(index=False))
    # pairs of distinct scenarios that are close without being duplicates: they stay separate units
    by_pair = folds.set_index(KEY)
    ident = list(zip(sets["901"]["Model"], sets["901"]["Scenario"]))
    near_pairs = {}
    for thr in NEAR:
        sel = [(ident[i], ident[j]) for i, j, d in close if d <= thr]
        if any(abs(d - thr) <= 1e-6 * thr for _, _, d in close):
            raise SystemExit(f"a pair of scenarios lies at the threshold {thr}: its count would depend on float noise")
        near_pairs[f"{thr:g}"] = {
            "pairs": len(sel),
            "scenarios": len({x for pair in sel for x in pair}),
            "pairs_in_different_folds": int(sum(by_pair.loc[a, "fold"] != by_pair.loc[b, "fold"] for a, b in sel)),
            "pairs_of_different_model_groups": int(sum(by_pair.loc[a, "group"] != by_pair.loc[b, "group"]
                                                       for a, b in sel)),
            "pairs_of_different_categories": int(sum(by_pair.loc[a, "agg"] != by_pair.loc[b, "agg"] for a, b in sel))}
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
            "rule": "duplicates form one unit, keyed by the smallest SHA-256 of 'model|scenario' among its "
                    "members; order the units by category, group and key; deal folds 1-5 in turn; store and train "
                    "in the order of the scenarios' keys",
            "duplicates": {
                "definition": "scenarios of the 901-set whose AR6 values on the fifteen variables of the D9 rule "
                              "coincide in every decade 2020-2100: every value differs by at most the tolerance "
                              "times the variable's largest absolute value in the 901-set; groups are sets of "
                              "scenarios connected by such pairs",
                "tolerance": DUP_TOL,
                "largest_deviation_within_groups_at_most": DUP_BAND,
                "smallest_deviation_between_distinct_scenarios": sig(between),
                **duplicates,
                "close_pairs_not_treated_as_duplicates": {
                    "definition": "pairs of scenarios of different units whose largest deviation over the fifteen "
                                  "variables and nine decades is at most the threshold, as a share of each "
                                  "variable's largest absolute value",
                    **near_pairs}},
            "scenarios_per_fold_by_group": fold_counts,
            "scenarios_per_fold_by_category": fold_counts_cat,
        },
    }
    dest = ROOT / "results" / "phase0e_model_groups.json"
    dest.parent.mkdir(exist_ok=True)
    write_lf(dest, json.dumps(report, indent=2) + "\n")

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
    print("Duplicates:", duplicates)
    print("Folds:", fold_counts["all"], fold_counts_cat, "->", folds_path.relative_to(ROOT))
    print("Written:", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
