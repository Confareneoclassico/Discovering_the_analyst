#!/usr/bin/env python3
"""Phase 0B: executability and determinism of the generation stage.

Evaluates no claim rule. The script repeats the one nominally deterministic
link of the pipeline as Secondary-data-generate.ipynb (Deep-IAM v1.0.1) runs
it, and compares the result with the deposited Gen_*.csv, scenario by scenario
and as distributions.

Transcribed from the notebook's code cells:
  - architecture: tsgm.models.zoo["vae_conv5"](seq_len=9, feat_dim=16, latent_dim=10)
  - weights: 'Policy-decoder{1,2,3}_weights-Se.h5' (1 = C1234, 2 = C56, 3 = C78), loaded with
    load_weights(), in the 'Policy-Generative Model' folder of the code deposit
  - scalers: TSFeatureWiseScaler((0, 1)), fit per category on the training tensors, which the D9
    reconstruction and Phase 0F identify with the deposited Real_*.csv
  - latents: z1, z2, z3 = tf.random.normal((10000, 10)), drawn in this order after
    tf.random.set_seed(3) and np.random.seed(3). SI S3 names numpy.random.randn instead, and the
    cell may have been run twice, so three readings are generated and compared
  - feature order (last axis of the decoder output): features_names of the notebook
  - saving (cell 17, convert_to_wide_format_and_save): the i-th generated scenario is labelled
    'Scenario:<i+1>', and the table is sorted by that label as text before it is written, so
    the rows of the deposited files are in the order Scenario:1, Scenario:10, Scenario:100, ...

Rows are therefore aligned by the integer in the label: row k-1 of a loaded tensor is
Scenario:k, the k-th scenario generated. The first run of this check (19 September 2026) took
the scenarios in file order, which compares unrelated scenarios; its elementwise figures are
reproduced here under the key first_run_file_order, next to those of a deliberately wrong
alignment (each generated scenario against the next deposited one), so that they can be read
for what they were.

Two controls are part of the run. Positive control: the regenerated arrays are written with a
transcription of the notebook's saving routine and read back; the elementwise test must pass
on them, or the check is void. Repeatability: the first reading is generated twice in the
same process and must be identical.

Each category is decided on its own, since the notebook saves the three files separately and a
deposit may combine categories from different executions: the report lists, per category, the
readings that reproduce it (reproduced_by). The conclusion says whether one reading reproduces
all three categories, each category is reproduced by some reading, only some are, or none, and
for the categories no reading reproduces whether their distributions lie within the Monte Carlo
floor. The script stops on a missing decade, an empty or non-numeric value, or identifiers other
than Scenario:1 to Scenario:n, instead of reporting on incomplete data.

Run in the authors' environment (requirements-deepiam-env.txt). A mismatch on another platform
or stack is a determinism finding to report, not an error.

The script itself was tested on mock deposits made with randomly initialised decoders, without
the shipped weights or the deposited Gen files (docs/checks/mock_deposit_for_phase0b.py).

Usage:  python3 05_regeneration_check.py [--paths ../config/local_paths.yaml] [--out report.json]
Needs:  scenarios3000_dir (DATA.md, A3) and deepiam_weights_dir (the 'Policy-Generative Model'
        folder of Deep-IAM v1.0.1, A2) in local_paths.yaml
Output: ../results/phase0b_regeneration.json, or the file given with --out
"""
import argparse, json, platform, re, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ["C1234", "C56", "C78"]
N_GEN, SEQ_LEN, LATENT_DIM, SEED = 10000, 9, 10, 3
TOL = 1e-4          # an element agrees when its relative deviation is at most TOL
YEAR = re.compile(r"(19|20|21)\d\d")

# Order of the notebook (cell 16, features_names). Sixteen features.
FEATURE_ORDER = ["CarbonSequestration", "FinalEnergy_Liquid", "PrimaryEnergy_Coal",
                 "PrimaryEnergy_Gas", "PrimaryEnergy_Oil", "SecondaryEle_Nuclear",
                 "SecondaryEle_Oil", "SecondaryEle_Solar", "SecondaryEle_Wind",
                 "SecondaryEle_Hydro", "SecondaryEle_Geothermal", "SecondaryEle_Gas",
                 "SecondaryEle_Coal", "SecondaryEle_Biomass", "SecondaryEle",
                 "Kyoto_Gases"]
DECODER_FILES = {"C1234": "Policy-decoder1_weights-Se.h5",
                 "C56":   "Policy-decoder2_weights-Se.h5",
                 "C78":   "Policy-decoder3_weights-Se.h5"}


def canon(x):
    return re.sub(r"[^a-z]", "", str(x).lower())


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def rounded(obj, n=6):
    """The report with floats rounded to n significant digits."""
    if isinstance(obj, float):
        return float(f"{obj:.{n}g}") if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: rounded(v, n) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rounded(v, n) for v in obj]
    return obj


def load_tensor(path, feature_order, order="label"):
    """Deposit CSV (one row per scenario and variable, one column per year) -> tensor
    (scenarios, years, features) in the given feature order, with the order of its rows.

    order="label": row k-1 is Scenario:k, the order in which the notebook generated or stacked
    the scenarios. order="file": scenarios in order of first appearance in the file, as the
    first run of this check read them."""
    df = pd.read_csv(path)
    if not {"Scenario", "Variable"} <= set(df.columns):
        raise SystemExit(f"{path.name}: expected the columns Scenario and Variable, found {list(df.columns)[:10]}")
    years = sorted((c for c in df.columns if YEAR.fullmatch(str(c))), key=int)
    if [int(y) for y in years] != list(range(2020, 2101, 10)):
        raise SystemExit(f"{path.name}: year columns {years}, expected the nine decades 2020 to 2100")
    values = df[years].apply(pd.to_numeric, errors="coerce")
    bad = ~np.isfinite(values.to_numpy(float))
    if bad.any():
        i, j = np.argwhere(bad)[0]
        raise SystemExit(f"{path.name}: {int(bad.sum())} empty or non-numeric value(s), the first at "
                         f"{df['Scenario'].iloc[i]}, {df['Variable'].iloc[i]}, {years[j]}")
    df[years] = values
    number = df["Scenario"].astype(str).str.extract(r"^Scenario:(\d+)$")[0]
    if number.isna().any():
        raise SystemExit(f"{path.name}: identifiers are not of the form Scenario:<integer>")
    df["_k"] = number.astype(int)
    n = int(df["_k"].nunique())
    if sorted(df["_k"].unique()) != list(range(1, n + 1)):
        raise SystemExit(f"{path.name}: identifiers are not Scenario:1 ... Scenario:{n}")
    df["_v"] = df["Variable"].map(canon)
    appearance = df["_k"].drop_duplicates().tolist()
    if appearance == list(range(1, n + 1)):
        rows = "numeric order of the labels"
    elif appearance == sorted(range(1, n + 1), key=str):
        rows = "text order of the labels"
    else:
        rows = "other"
    wanted = list(range(1, n + 1)) if order == "label" else appearance
    mats = []
    for f in feature_order:
        sub = df[df["_v"] == canon(f)]
        if len(sub) != n or not sub["_k"].is_unique:
            raise SystemExit(f"{path.name}, {f}: expected one row for each of the {n} scenarios, found {len(sub)}")
        mats.append(sub.set_index("_k").loc[wanted, years].to_numpy(float))
    return np.stack(mats, axis=-1), [int(y) for y in years], rows


def write_as_notebook(data_array, feature_names, path):
    """Transcription of convert_to_wide_format_and_save (Secondary-data-generate.ipynb, cell 17), with the
    output path as an argument: one record per scenario and feature, the i-th scenario labelled
    'Scenario:<i+1>', the table sorted by that label and written as CSV."""
    n_indices, n_time_steps, n_features = data_array.shape
    time_steps = list(range(2020, 2101, 10))
    data_records = []
    for i in range(n_indices):
        for f_idx, feature in enumerate(feature_names):
            record = {"Scenario": "Scenario:" + str(i + 1), "Variable": feature}
            for t_idx, year in enumerate(time_steps):
                record[str(year)] = data_array[i, t_idx, f_idx]
            data_records.append(record)
    df = pd.DataFrame(data_records)
    df = df.sort_values(by="Scenario")
    df.to_csv(path, index=False, encoding="utf-8-sig")


def elementwise(out, ref):
    """Agreement of two aligned tensors (scenarios, years, features), element by element."""
    rel = np.abs(out - ref) / np.maximum(np.abs(ref), 1e-6)
    iqr = np.quantile(ref, 0.75, axis=0) - np.quantile(ref, 0.25, axis=0)          # (years, features)
    nmax = float((np.abs(out - ref) / np.maximum(iqr, 1e-6)).max())
    a, b = out - out.mean(axis=0), ref - ref.mean(axis=0)
    den = np.sqrt((a ** 2).sum(axis=0) * (b ** 2).sum(axis=0))
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = (a * b).sum(axis=0) / den               # across scenarios, per year and feature
    corr = corr[np.isfinite(corr)]
    return {"median_rel_dev": float(np.median(rel)),
            "iqr_normalized_max_dev": nmax,
            "frac_within_tol": float((rel <= TOL).mean()),
            "median_correlation": float(np.median(corr)) if corr.size else None,
            "PASS": bool(np.median(rel) <= TOL and nmax <= 1e-2)}


def latents_variant(variant):
    """category -> (N_GEN, LATENT_DIM); z1, z2, z3 drawn in this order from one stream."""
    import tensorflow as tf
    if variant == "tf_global_seed":            # the notebook as written
        tf.random.set_seed(SEED)
        np.random.seed(SEED)
        return {c: tf.random.normal((N_GEN, LATENT_DIM)).numpy() for c in CATEGORIES}
    if variant == "tf_second_execution":       # cell 15 run twice without re-seeding
        tf.random.set_seed(SEED)
        np.random.seed(SEED)
        for _ in CATEGORIES:                    # the draws of the first execution are discarded
            tf.random.normal((N_GEN, LATENT_DIM))
        return {c: tf.random.normal((N_GEN, LATENT_DIM)).numpy() for c in CATEGORIES}
    if variant == "numpy_randn":               # the reading of SI S3
        rs = np.random.RandomState(SEED)
        return {c: rs.randn(N_GEN, LATENT_DIM) for c in CATEGORIES}
    raise ValueError(variant)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    ap.add_argument("--out", default=str(ROOT / "results" / "phase0b_regeneration.json"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    dep = Path(paths["scenarios3000_dir"]).expanduser()
    wdir = Path(paths["deepiam_weights_dir"]).expanduser()

    import tsgm
    import tensorflow as tf

    report = {"seed": SEED, "tol": TOL, "feature_order": FEATURE_ORDER,
              "alignment": "row k-1 of every tensor is Scenario:k, the k-th scenario generated",
              "env": {"python": sys.version.split()[0], "tensorflow": tf.__version__,
                      "tsgm": getattr(tsgm, "__version__", "?"), "numpy": np.__version__,
                      "pandas": pd.__version__, "platform": sys.platform, "machine": platform.machine()},
              "deposit_row_order": {}, "real_shapes": {}, "variants": {}}

    scalers, real, gen_ref, gen_file_order, decoders = {}, {}, {}, {}, {}
    for c in CATEGORIES:
        Xr, _, rows_r = load_tensor(dep / f"Real_{c}.csv", FEATURE_ORDER)
        Xg, _, rows_g = load_tensor(dep / f"Gen_{c}.csv", FEATURE_ORDER)
        gen_file_order[c], _, _ = load_tensor(dep / f"Gen_{c}.csv", FEATURE_ORDER, order="file")
        if Xg.shape != (N_GEN, SEQ_LEN, len(FEATURE_ORDER)):
            raise SystemExit(f"Gen_{c}.csv: shape {Xg.shape}, expected {(N_GEN, SEQ_LEN, len(FEATURE_ORDER))}")
        sc = tsgm.utils.TSFeatureWiseScaler((0, 1))
        sc.fit(Xr)
        scalers[c], real[c], gen_ref[c] = sc, Xr, Xg
        arch = tsgm.models.zoo["vae_conv5"](SEQ_LEN, len(FEATURE_ORDER), LATENT_DIM)
        arch.decoder.load_weights(str(wdir / DECODER_FILES[c]))
        decoders[c] = arch.decoder
        report["real_shapes"][c] = list(Xr.shape)
        report["deposit_row_order"][f"Real_{c}.csv"] = rows_r
        report["deposit_row_order"][f"Gen_{c}.csv"] = rows_g

    def generate(variant):
        z = latents_variant(variant)
        out = {}
        for c in CATEGORIES:
            x = decoders[c](z[c].astype("float32"))
            # tsgm's inverse_transform subtracts in place: it is given the TF tensor, as in the notebook
            # (np.asarray of an eager tensor is read-only), and the result is converted afterwards
            out[c] = np.asarray(scalers[c].inverse_transform(x))
            if not np.isfinite(out[c]).all():
                raise SystemExit(f"reading '{variant}', {c}: the decoder produced non-finite values")
        return out

    regen = {}
    for variant in ["tf_global_seed", "tf_second_execution", "numpy_randn"]:
        regen[variant] = generate(variant)
        vrep = {}
        for c in CATEGORIES:
            out = regen[variant][c]
            vrep[c] = elementwise(out, gen_ref[c])
            wrong = elementwise(np.roll(out, 1, axis=0), gen_ref[c])
            first = elementwise(out, gen_file_order[c])
            vrep[c]["wrong_alignment_shift_by_one"] = {k: wrong[k] for k in ["median_rel_dev", "frac_within_tol",
                                                                             "median_correlation"]}
            vrep[c]["first_run_file_order"] = {k: first[k] for k in ["median_rel_dev", "iqr_normalized_max_dev",
                                                                     "frac_within_tol", "median_correlation"]}
        vrep["PASS_all"] = all(vrep[c]["PASS"] for c in CATEGORIES)
        report["variants"][variant] = vrep

    # ---- Controls ----
    again = generate("tf_global_seed")
    repeatable = all(np.array_equal(again[c], regen["tf_global_seed"][c]) for c in CATEGORIES)
    control = {"what": "the regenerated arrays (first reading), written with a transcription of the notebook's "
                       "saving routine and read back by this script, compared with themselves",
               "per_category": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for c in CATEGORIES:
            p = Path(tmp) / f"Gen_{c}.csv"
            write_as_notebook(regen["tf_global_seed"][c], FEATURE_ORDER, p)
            back, _, rows = load_tensor(p, FEATURE_ORDER)
            e = elementwise(regen["tf_global_seed"][c], back)
            control["per_category"][c] = {"rows_as_written": rows, "median_rel_dev": e["median_rel_dev"],
                                          "frac_within_tol": e["frac_within_tol"], "PASS": e["PASS"]}
    control["PASS"] = all(v["PASS"] for v in control["per_category"].values())
    report["controls"] = {"positive_control": control, "regeneration_repeatable_in_process": bool(repeatable)}

    # ---- Distributions: the regenerated ensemble against the deposit, whatever the samples ----
    # Quantile deviations are divided by the reference spread (Q90 - Q10 per year and feature), not by the
    # quantile itself: a quantile near zero of a phased-out variable would otherwise turn a tiny absolute
    # difference into a huge relative one. The relative version is kept as a secondary figure.
    QS = [0.10, 0.25, 0.50, 0.75, 0.90]

    def qdev_metrics(A, B):
        """Quantile deviations of ensemble A from reference B: divided by the spread of B, and relative."""
        qa, qb = np.quantile(A, QS, axis=0), np.quantile(B, QS, axis=0)   # (quantiles, years, features)
        spread = np.maximum(qb[-1] - qb[0], 1e-6)
        sn = np.abs(qa - qb) / spread[None, :, :]
        rel = np.abs(qa - qb) / np.maximum(np.abs(qb), 1e-6)
        return sn, rel

    def faithful(sn, sn_self):
        """Faithful as distributions: deviations from the deposit within twice those of two independent
        10,000-draw ensembles through one decoder, or small in absolute terms."""
        med, p95 = float(np.median(sn)), float(np.quantile(sn, 0.95))
        ratio_med = med / max(float(np.median(sn_self)), 1e-9)
        ratio_p95 = p95 / max(float(np.quantile(sn_self, 0.95)), 1e-9)
        return ratio_med, ratio_p95, bool((ratio_med <= 2.0 and ratio_p95 <= 2.0) or (med <= 0.02 and p95 <= 0.10))

    dist = {"per_category": {}, "worst_cells_spread_normalized": []}
    sn_all, selfnoise_all = [], []
    ours = regen["tf_global_seed"]
    ours2 = regen["numpy_randn"]               # an independent draw through the same decoder
    for c in CATEGORIES:
        sn, rel = qdev_metrics(ours[c], gen_ref[c])
        sn_self, _ = qdev_metrics(ours2[c], ours[c])   # Monte Carlo floor
        ratio_med, ratio_p95, ok = faithful(sn, sn_self)
        dist["per_category"][c] = {
            "median_sn_qdev": float(np.median(sn)),
            "p95_sn_qdev": float(np.quantile(sn, 0.95)),
            "max_sn_qdev": float(sn.max()),
            "selfnoise_median_sn_qdev": float(np.median(sn_self)),
            "selfnoise_p95_sn_qdev": float(np.quantile(sn_self, 0.95)),
            "median_rel_qdev": float(np.median(rel)),
            "excess_ratio_median": ratio_med,
            "excess_ratio_p95": ratio_p95,
            "PASS_distributional": ok,
        }
        sn_all.append(sn); selfnoise_all.append(sn_self)
        wq, wt, wf = np.unravel_index(np.argsort(sn, axis=None)[-3:], sn.shape)
        for q, t, f in zip(wq, wt, wf):
            dist["worst_cells_spread_normalized"].append(
                {"cat": c, "q": QS[q], "year": 2020 + 10 * int(t),
                 "feature": FEATURE_ORDER[f], "sn_dev": float(sn[q, t, f])})
    A = np.concatenate([x.ravel() for x in sn_all])
    N = np.concatenate([x.ravel() for x in selfnoise_all])
    ratio_med, ratio_p95, ok = faithful(A, N)
    dist["overall"] = {"median_sn_qdev": float(np.median(A)),
                       "p95_sn_qdev": float(np.quantile(A, 0.95)),
                       "selfnoise_median": float(np.median(N)),
                       "selfnoise_p95": float(np.quantile(N, 0.95)),
                       "excess_ratio_median": ratio_med,
                       "excess_ratio_p95": ratio_p95}
    dist["PASS_distributional"] = ok           # the three categories pooled
    report["distributional"] = dist

    # ---- Scaler bounds: are the Real_*.csv the data the authors' scaler was fit on? ----
    # The decoder's output is roughly bounded by the scaler fit on the training tensors, so the deposited
    # Gen values should lie within the minimum and maximum of the Real files. A feature whose deposited
    # values exceed those bounds by more than 1% of the span points to a scaler fit on other data.
    sb = {}
    for c in CATEGORIES:
        rmin, rmax = real[c].min(axis=(0, 1)), real[c].max(axis=(0, 1))          # per feature
        gmin, gmax = gen_ref[c].min(axis=(0, 1)), gen_ref[c].max(axis=(0, 1))
        span = np.maximum(rmax - rmin, 1e-6)
        under = (rmin - gmin) / span
        over = (gmax - rmax) / span
        flags = [{"feature": FEATURE_ORDER[i],
                  "below_min_frac_of_span": float(under[i]),
                  "above_max_frac_of_span": float(over[i])}
                 for i in range(len(FEATURE_ORDER)) if under[i] > 0.01 or over[i] > 0.01]
        sb[c] = {"n_features_flagged": len(flags), "flagged": flags}
    report["scaler_bounds"] = sb
    n_flagged = sum(sb[c]["n_features_flagged"] for c in CATEGORIES)

    # Each category is decided on its own: the notebook saves the categories separately (cell 18 writes
    # only C1234), so a deposit may combine categories from different executions.
    readings = list(report["variants"])
    by = {c: [v for v in readings if report["variants"][v][c]["PASS"]] for c in CATEGORIES}
    report["reproduced_by"] = by
    single = next((v for v in readings if report["variants"][v]["PASS_all"]), None)
    done = [c for c in CATEGORIES if by[c]]
    rest = [c for c in CATEGORIES if not by[c]]

    def readings_of(cs):
        return ", ".join(f"{c} by reading '{by[c][0]}'" for c in cs)

    valid = control["PASS"] and repeatable
    if not valid:
        report["conclusion"] = ("CHECK VOID: a control failed (positive control "
                                f"{'passed' if control['PASS'] else 'failed'}, regeneration "
                                f"{'repeatable' if repeatable else 'not repeatable'} in process)")
    elif single:
        report["conclusion"] = f"EXACT reproduction by reading '{single}'"
    elif not rest:
        report["conclusion"] = (f"EXACT reproduction, category by category: {readings_of(done)}; "
                                "no single reading reproduces all three")
    elif done:
        within = [c for c in rest if dist["per_category"][c]["PASS_distributional"]]
        beyond = [c for c in rest if c not in within]
        report["conclusion"] = (f"PARTLY REPRODUCED: exactly {readings_of(done)}; by no reading "
                                + "; ".join(part for part in [
                                    f"{', '.join(within)}, whose distributions are within the Monte Carlo floor"
                                    if within else "",
                                    f"{', '.join(beyond)}, whose distributions deviate beyond the Monte Carlo floor"
                                    if beyond else ""] if part))
    elif dist["PASS_distributional"]:
        report["conclusion"] = ("EXECUTABLE AND FAITHFUL AS DISTRIBUTIONS (within the Monte Carlo noise of "
                                "independent draws); the deposited samples are not reproduced from the "
                                "documented seed")
    else:
        report["conclusion"] = ("NOT REPRODUCED: no reading reproduces the deposited samples, and the "
                                "distributions deviate from the deposit beyond the Monte Carlo floor. "
                                + (f"The scaler-bounds diagnostic flags {n_flagged} feature(s): the authors' "
                                   "scaler may have been fit on other data than Real_*.csv."
                                   if n_flagged else
                                   "The scaler-bounds diagnostic flags no feature, so the Real_*.csv are "
                                   "consistent with the scaler-fit data; the shipped weights may differ from "
                                   "those that generated the deposit."))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_lf(out, json.dumps(rounded(report), indent=2) + "\n")
    print(json.dumps(rounded(report), indent=2))
    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
