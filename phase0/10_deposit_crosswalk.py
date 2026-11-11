#!/usr/bin/env python3
"""Phase 0F: identity of the deposited real set, real data only.

The deposited Real_<category>.csv carry anonymous identifiers ("Scenario:1", ...): no model and
no AR6 scenario name. This script matches every deposited row to an AR6 model-scenario pair by its
values. It thereby
  (i)   verifies the D9 reconstruction (data/derived/kept901_5feat+elec10.csv) scenario by
        scenario, on all sixteen deposited variables;
  (ii)  identifies the AR6 variable behind each deposited variable, Kyoto Gases included, by
        testing the five AR6 candidates for Kyoto Gases;
  (iii) finds the deposited scenarios that duplicate one another (all values of the fifteen
        variables of the D9 rule coinciding in every decade, to within DUP_TOL of the variable's
        largest absolute value), from the deposited values alone, and checks that the groups are
        those that 09_model_groups.py found in the AR6 values and keeps together in the X5 folds
        (data/derived/x5_folds_901.csv);
  (iv)  writes the crosswalk that attaches AR6 identifiers, hence model groups and X5 folds, to
        the deposited rows.

Rule tested: within each category, Scenario:k of the deposit is the k-th scenario of the 901-set
in ascending order of (Model, Scenario), compared as strings by code point.

It reads Real_*.csv, the AR6 World CSV, the derived lists and the configuration. No synthetic file
is read and no claim rule is evaluated. The report holds counts and deviations, no scenario value;
the crosswalk holds identifiers only. The outputs contain no timestamp or environment information
and are written with LF line endings, so a re-run on the same inputs reproduces them byte for byte.

Usage:  python3 10_deposit_crosswalk.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0f_deposit_crosswalk.json, ../data/derived/crosswalk_901.csv
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ["C1234", "C56", "C78"]
KEY = ["Model", "Scenario"]
YEARS = [str(y) for y in range(2020, 2101, 10)]
KYOTO_DEPOSIT = "Kyoto_Gases"
KYOTO_CANDIDATES = ["Emissions|Kyoto Gases",
                    "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR5-GWP100)",
                    "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR6-GWP100)",
                    "AR6 climate diagnostics|Native-with-Infilled|Emissions|Kyoto Gases (AR5-GWP100)",
                    "AR6 climate diagnostics|Native-with-Infilled|Emissions|Kyoto Gases (AR6-GWP100)"]
TOL = 1e-6      # largest admitted deviation, as a share of the variable's largest absolute value in the category
DUP_TOL = 1e-6  # duplicates: every value within this share of the variable's largest absolute value in the deposit
DUP_BAND = 1e-9  # duplicates must in fact agree to this, so that DUP_TOL decides nothing (as in 09_model_groups.py)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sig(x, n=3):
    return float(f"{x:.{n}g}")


def write_lf(path, text):
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def read_world(world_path, variables):
    parts = []
    for chunk in pd.read_csv(world_path, chunksize=200_000, usecols=KEY + ["Region", "Variable"] + YEARS):
        parts.append(chunk[(chunk["Region"] == "World") & chunk["Variable"].isin(variables)])
    w = pd.concat(parts, ignore_index=True)
    if w.duplicated(KEY + ["Variable"]).any():
        raise SystemExit("duplicate model-scenario-variable rows in the World CSV")
    return w.set_index(KEY + ["Variable"])[YEARS].astype(float)


def read_real(path):
    if "gen_" in path.name.lower():
        raise SystemExit("Refusing to read a synthetic file before the freeze: " + path.name)
    df = pd.read_csv(path)
    ids = df["Scenario"].drop_duplicates()
    number = ids.str.replace("Scenario:", "", regex=False).astype(int)
    if sorted(number) != list(range(1, len(ids) + 1)):
        raise SystemExit(f"{path.name}: identifiers are not Scenario:1 ... Scenario:{len(ids)}")
    order = [f"Scenario:{k}" for k in range(1, len(ids) + 1)]
    out = {}
    for v, sub in df.groupby("Variable"):
        if not sub["Scenario"].is_unique:
            raise SystemExit(f"{path.name}, {v}: repeated scenario identifiers")
        out[v] = sub.set_index("Scenario").reindex(order)[YEARS].astype(float).to_numpy()
    return order, out


def scaled_dev(real, ar6):
    """Row-wise largest absolute deviation, as a share of the deposit's largest absolute value."""
    return np.abs(real - ar6).max(axis=1) / np.abs(real).max()


def coincident_groups(S, tol):
    """Groups of rows of S that coincide. Two rows are linked when they differ by at most tol in every column,
    and a group is a set of rows connected by links. Returns one label per row (the position of the first row
    of its group), the largest deviation between two rows of a group and the smallest between rows of
    different groups. A deviation between two rows is their largest absolute difference over the columns."""
    n = len(S)
    label = np.arange(n)
    for i in range(n - 1):
        d = np.abs(S[i + 1:] - S[i]).max(axis=1)
        for j in np.nonzero(d <= tol)[0] + i + 1:
            a, b = sorted((label[i], label[j]))
            label[label == b] = a
    within, between = 0.0, np.inf
    for i in range(n - 1):
        d = np.abs(S[i + 1:] - S[i]).max(axis=1)
        same = label[i + 1:] == label[i]
        if same.any():
            within = max(within, float(d[same].max()))
        if (~same).any():
            between = min(between, float(d[~same].min()))
    return label, within, between


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    cfg = yaml.safe_load(open(ROOT / "config" / "paper_values.yaml"))
    lab = cfg["fixed"]["claims"]["X5"]["labels"]
    to_group = {v: g for g, vs in lab["versions"].items() for v in vs}
    E = cfg["fixed"]["evaluation_set_E"]
    names = E["key_variables"] + E["electricity"]
    if [str(y) for y in E["years"]] != YEARS or sorted(names) != sorted(E["ar6_variables"]):
        raise SystemExit("evaluation_set_E of the configuration does not list the sixteen variables on 2020-2100")
    kyoto_cfg = E["ar6_variables"][KYOTO_DEPOSIT]
    RAW_MAP = {v: E["ar6_variables"][v] for v in names if v != KYOTO_DEPOSIT}     # the fifteen variables of the D9 rule

    world_path = Path(paths["ar6_world_csv"]).expanduser()
    if world_path.stat().st_size < 1024:
        raise SystemExit(f"{world_path} is a Git LFS pointer, not the data: restore it as in DATA.md, B2")
    dep = Path(paths["scenarios3000_dir"]).expanduser()
    kept_path = ROOT / "data" / "derived" / "kept901_5feat+elec10.csv"
    folds_path = ROOT / "data" / "derived" / "x5_folds_901.csv"

    kept = pd.read_csv(kept_path)
    folds = pd.read_csv(folds_path, keep_default_na=False).set_index(KEY)
    world = read_world(world_path, set(RAW_MAP.values()) | set(KYOTO_CANDIDATES))

    def ar6(pairs, variable):
        """AR6 values of `variable` for the model-scenario pairs, in their order; NaN rows where not reported."""
        idx = pd.MultiIndex.from_arrays([pairs["Model"], pairs["Scenario"], [variable] * len(pairs)])
        return world.reindex(idx).to_numpy()

    inputs = {"B2, AR6 World CSV v1.1": sha256(world_path),
              "data/derived/" + kept_path.name: sha256(kept_path),
              "data/derived/" + folds_path.name: sha256(folds_path)}
    per_cat, rows, deposited = {}, [], []
    for c in CATEGORIES:
        f = dep / f"Real_{c}.csv"
        inputs["A3, " + f.name] = sha256(f)
        order, real = read_real(f)
        if set(real) != set(RAW_MAP) | {KYOTO_DEPOSIT}:
            raise SystemExit(f"{f.name}: variables differ from the sixteen expected: {sorted(set(real))}")
        pairs = kept[kept["agg"] == c].sort_values(KEY, kind="mergesort").reset_index(drop=True)
        if len(pairs) != len(order):
            raise SystemExit(f"{f.name}: {len(order)} deposited scenarios, {len(pairs)} in the 901 list")

        dev = {v: scaled_dev(real[v], ar6(pairs, a)) for v, a in RAW_MAP.items()}
        raw_dev = np.max(np.vstack(list(dev.values())), axis=0)
        kyoto = {}
        for cand in KYOTO_CANDIDATES:
            a = ar6(pairs, cand)
            reported = ~np.isnan(a).any(axis=1)
            d = scaled_dev(real[KYOTO_DEPOSIT][reported], a[reported]) if reported.any() else np.array([])
            kyoto[cand] = {"n_reported": int(reported.sum()), "n_equal": int((d <= TOL).sum()),
                           "max_scaled_deviation": sig(d.max()) if len(d) else None}
        k_dev = scaled_dev(real[KYOTO_DEPOSIT], ar6(pairs, kyoto_cfg))
        all_dev = np.maximum(raw_dev, k_dev)
        n_equal = int((all_dev <= TOL).sum())
        if n_equal != len(order):
            raise SystemExit(f"{c}: only {n_equal} of {len(order)} deposited scenarios equal the AR6 values of the "
                             "901 list under the ordering rule: the D9 reconstruction is not confirmed")
        best = [k for k, v in kyoto.items() if v["n_equal"] == len(order)]
        if best != [kyoto_cfg]:
            raise SystemExit(f"{c}: Kyoto Gases candidates equal to the deposit {best}, configured {kyoto_cfg}")

        if not pd.MultiIndex.from_frame(pairs[KEY]).isin(folds.index).all():
            raise SystemExit(f"{c}: a scenario of the crosswalk is missing from data/derived/x5_folds_901.csv")
        deposited.append({v: real[v] for v in list(RAW_MAP) + [KYOTO_DEPOSIT]})
        per_cat[c] = {
            "n_scenarios": len(order),
            "n_equal_on_all_16_variables": n_equal,
            "max_scaled_deviation": sig(all_dev.max()),
            "kyoto_candidates": kyoto,
        }
        for k, (m, s) in enumerate(zip(pairs["Model"], pairs["Scenario"])):
            rows.append({"category": c, "real_file": f.name, "real_id": order[k], "Model": m, "Scenario": s,
                         "key": hashlib.sha256(f"{m}|{s}".encode("utf-8")).hexdigest()})

    cross = pd.DataFrame(rows)
    if not (cross.set_index(KEY)["key"] == folds["key"].reindex(pd.MultiIndex.from_frame(cross[KEY])).to_numpy()).all():
        raise SystemExit("keys of the crosswalk differ from those of data/derived/x5_folds_901.csv")
    cross_path = ROOT / "data" / "derived" / "crosswalk_901.csv"
    write_lf(cross_path, cross.to_csv(index=False))

    # Duplicates among the deposited scenarios, from the deposited values alone (rows in the order of the crosswalk)
    def scaled(variables):
        blocks = [np.vstack([d[v] for d in deposited]) for v in variables]
        return np.hstack([b / np.abs(b).max() for b in blocks])

    g15, within15, between15 = coincident_groups(scaled(list(RAW_MAP)), DUP_TOL)
    if within15 > DUP_BAND:
        raise SystemExit(f"deposited scenarios treated as duplicates differ by {within15:.3g} of a variable's "
                         f"largest value, more than {DUP_BAND}: the tolerance {DUP_TOL} would decide")
    g15 = pd.Series(g15)
    size15 = g15.map(g15.value_counts())
    # Kyoto Gases are not among the fifteen variables: how far apart are they inside each group of duplicates?
    k = scaled([KYOTO_DEPOSIT])
    kyoto_dev = pd.Series({g: float(np.abs(k[(g15 == g).to_numpy()] - k[g]).max()) for g in g15[size15 > 1].unique()})
    if ((kyoto_dev > 0.5 * DUP_BAND) & (kyoto_dev < 2 * DUP_BAND)).any() \
            or ((kyoto_dev > 0.5 * DUP_TOL) & (kyoto_dev < 2 * DUP_TOL)).any():
        raise SystemExit("a Kyoto Gases deviation inside a group of duplicates lies at a reporting threshold")
    theirs = folds["duplicate_group"].reindex(pd.MultiIndex.from_frame(cross[KEY])).reset_index(drop=True)
    both = pd.DataFrame({"deposit": g15, "folds": theirs})[size15 > 1]
    if ((theirs != "") != (size15 > 1)).any() or (both.groupby("deposit")["folds"].nunique() != 1).any() \
            or (both.groupby("folds")["deposit"].nunique() != 1).any():
        raise SystemExit("the duplicate groups of the deposit differ from those of data/derived/x5_folds_901.csv")
    model_group = cross["Model"].map(to_group)
    for c in CATEGORIES:
        m = (cross["category"] == c).to_numpy()
        per_cat[c]["duplicates_on_15_raw_variables"] = {
            "n_groups": int(g15[m & (size15 > 1)].nunique()), "n_scenarios": int((m & (size15 > 1)).sum())}
    spanning = {what: int(sum(col[g15 == g].nunique() > 1 for g in g15[size15 > 1].unique()))
                for what, col in [("categories", cross["category"]), ("model_groups", model_group),
                                  ("model_versions", cross["Model"])]}

    report = {
        "inputs_sha256": inputs,
        "definitions": {
            "rule": "within each category, Scenario:k of the deposit is the k-th scenario of "
                    "data/derived/kept901_5feat+elec10.csv in ascending order of (Model, Scenario), code-point order",
            "equal": f"largest absolute deviation over the nine decades 2020-2100 at most {TOL} of the deposited "
                     "variable's largest absolute value in the category, on each of the sixteen variables",
            "duplicates": f"deposited scenarios whose values coincide on all compared variables and decades: every "
                          f"value differs by at most {DUP_TOL} of the variable's largest absolute value in the deposit "
                          f"(members of a group must agree to {DUP_BAND}); groups are sets of scenarios connected by "
                          "such pairs. The groups on the fifteen variables of the D9 rule are checked against the "
                          "column duplicate_group of data/derived/x5_folds_901.csv, which 09_model_groups.py "
                          "derives from the AR6 values. Kyoto Gases are not among the fifteen: their deviation "
                          "inside a group is the largest absolute difference between a member and the group's "
                          f"first, as a share of the variable's largest absolute value (identical: at most {DUP_BAND})",
        },
        "ar6_variables": {**RAW_MAP, KYOTO_DEPOSIT: kyoto_cfg},
        "per_category": per_cat,
        "all": {"n_scenarios": int(len(cross)),
                "n_equal_on_all_16_variables": sum(per_cat[c]["n_equal_on_all_16_variables"] for c in CATEGORIES),
                "duplicates_on_15_raw_variables": {
                    "n_groups": int(g15[size15 > 1].nunique()), "n_scenarios": int((size15 > 1).sum()),
                    "largest_group": int(size15.max()),
                    "identical_within_groups": bool(within15 == 0.0),
                    "smallest_deviation_between_distinct_scenarios": sig(between15),
                    "groups_spanning_categories": spanning["categories"],
                    "groups_spanning_model_groups": spanning["model_groups"],
                    "groups_spanning_model_versions": spanning["model_versions"],
                    "scenarios_by_model_group": {str(k): int(v) for k, v in
                                                 model_group[size15 > 1].value_counts().sort_index().items()},
                    "equal_to_duplicate_groups_of_x5_folds": True,
                    "kyoto_gases_within_groups": {
                        "n_groups_identical": int((kyoto_dev <= DUP_BAND).sum()),
                        "n_scenarios_in_identical_groups": int(sum((g15 == g).sum() for g in
                                                                   kyoto_dev[kyoto_dev <= DUP_BAND].index)),
                        "n_groups_within_tolerance_not_identical": int(((kyoto_dev > DUP_BAND)
                                                                        & (kyoto_dev <= DUP_TOL)).sum()),
                        "n_groups_differing": int((kyoto_dev > DUP_TOL).sum()),
                        "smallest_deviation_among_differing": sig(kyoto_dev[kyoto_dev > DUP_TOL].min())
                                                              if (kyoto_dev > DUP_TOL).any() else None,
                        "largest_deviation": sig(kyoto_dev.max())}}},
        "crosswalk": {"file": "data/derived/crosswalk_901.csv", "sha256": sha256(cross_path)},
    }
    dest = ROOT / "results" / "phase0f_deposit_crosswalk.json"
    dest.parent.mkdir(exist_ok=True)
    write_lf(dest, json.dumps(report, indent=2) + "\n")

    for c in CATEGORIES:
        p = per_cat[c]
        print(f"{c}: {p['n_equal_on_all_16_variables']} of {p['n_scenarios']} deposited scenarios equal AR6 on all "
              f"16 variables (largest scaled deviation {p['max_scaled_deviation']})")
        for cand, k in p["kyoto_candidates"].items():
            print(f"   Kyoto candidate {cand}: reported {k['n_reported']}, equal {k['n_equal']}")
        print(f"   duplicates in the deposit on the 15 raw variables: {p['duplicates_on_15_raw_variables']}")
    print("All:", report["all"])
    print("Written:", dest.relative_to(ROOT), "and", cross_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
