#!/usr/bin/env python3
"""Phase 0B — executability & determinism check of the generation stage.

Evaluates NO claim rule. Reproduces the deterministic link of the pipeline
exactly as Secondary-data-generate.ipynb (v1.0.1) does, and compares
elementwise against the deposited Gen_*.csv.

Everything below is transcribed from the notebook (cells extracted from the
archived v1.0.0/v1.0.1 diff):
  - architecture: tsgm.models.zoo["vae_conv5"](seq_len=9, feat_dim=16, latent_dim=10)
  - weights: weights-only h5 loaded with load_weights(), files
    'Policy-encoder{1,2,3}_weights-Se.h5' / 'Policy-decoder{1,2,3}_weights-Se.h5'
    (1=C1234, 2=C56, 3=C78), sitting in the 'Policy-Generative Model' folder
    of the code deposit (bare filenames = notebook cwd)
  - scalers: TSFeatureWiseScaler((0,1)) fit per category on the training
    tensors, which per the D9 reconstruction are the deposited Real_*.csv
  - latents: z1,z2,z3 = tf.random.normal((10000,10)) drawn sequentially
    after tf.random.set_seed(3); np.random.seed(3) also set. SI S3 instead
    says numpy.random.randn — both variants are generated and compared.
  - feature order (decoder output axis) = features_names in the notebook,
    hardcoded below; Kyoto_Gases is a generated feature, appended last.

Run in the PINNED environment (requirements-deepiam-env.txt). A mismatch on
another platform/stack is a determinism finding to transcribe, not an error.

Config keys in local_paths.yaml:
  scenarios3000_dir:   deposit with Gen_/Real_*.csv
  deepiam_weights_dir: the 'Policy-Generative Model' folder of Deep-IAM v1.0.1

Output: ../results/phase0b_regeneration.json
"""
import json, argparse, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

CATEGORIES = ["C1234", "C56", "C78"]
N_GEN, SEQ_LEN, LATENT_DIM, SEED = 10000, 9, 10, 3
TOL = 1e-4          # PASS threshold on max |rel dev|; actual value reported regardless

# Exact notebook order (cell: features_names). nft = 16.
FEATURE_ORDER = ["CarbonSequestration", "FinalEnergy_Liquid", "PrimaryEnergy_Coal",
                 "PrimaryEnergy_Gas", "PrimaryEnergy_Oil", "SecondaryEle_Nuclear",
                 "SecondaryEle_Oil", "SecondaryEle_Solar", "SecondaryEle_Wind",
                 "SecondaryEle_Hydro", "SecondaryEle_Geothermal", "SecondaryEle_Gas",
                 "SecondaryEle_Coal", "SecondaryEle_Biomass", "SecondaryEle",
                 "Kyoto_Gases"]
DECODER_FILES = {"C1234": "Policy-decoder1_weights-Se.h5",
                 "C56":   "Policy-decoder2_weights-Se.h5",
                 "C78":   "Policy-decoder3_weights-Se.h5"}


def load_tensor(path, feature_order):
    """Deposit CSV -> tensor (n, T, F) in the given feature order.

    Layout A (the deposit's actual format, per convert_to_wide_format_and_save):
      one row per (Scenario, Variable), year columns 2020..2100.
    Layout B (fallback): wide '<Var>_<year>' columns, one row per scenario.
    Scenario order is preserved as first appearance (= generation order).
    """
    df = pd.read_csv(path)
    canon = lambda x: re.sub(r"[^a-z]", "", str(x).lower())
    ypat = re.compile(r"^(19|20|21)\d\d$")

    if "Variable" in df.columns:                          # Layout A
        ycols = [c for c in df.columns if ypat.match(str(c))]
        years = sorted(ycols, key=lambda c: int(c))
        scen_col = "Scenario" if "Scenario" in df.columns else df.columns[0]
        df["_v"] = df["Variable"].map(canon)
        bykey = dict(zip(df["_v"], df["Variable"]))
        missing = [f for f in feature_order if canon(f) not in bykey]
        if missing:
            raise SystemExit(f"{path}: features not found: {missing}; "
                             f"available: {sorted(df['Variable'].unique())}")
        scen_order = df[scen_col].drop_duplicates().tolist()
        mats = []
        for f in feature_order:
            sub = (df[df["_v"] == canon(f)]
                   .drop_duplicates(subset=scen_col)
                   .set_index(scen_col)
                   .reindex(scen_order))
            mats.append(sub[years].to_numpy(float))
        return np.stack(mats, axis=-1), [int(y) for y in years]

    # Layout B fallback: wide '<Var>_<year>' columns
    pat = re.compile(r"^(.*?)[_|., ]((?:19|20|21)\d\d)$")
    groups = {}
    for c in df.columns:
        m = pat.match(str(c))
        if m:
            groups.setdefault(m.group(1), {})[int(m.group(2))] = c
    bykey = {canon(k): k for k in groups}
    missing = [f for f in feature_order if canon(f) not in bykey]
    if missing:
        raise SystemExit(f"{path}: features not found: {missing}; available: {sorted(groups)}")
    years = sorted(next(iter(groups.values())))
    X = np.stack([df[[groups[bykey[canon(f)]][y] for y in years]].to_numpy(float)
                  for f in feature_order], axis=-1)
    return X, years


def latents_variant(variant):
    """category -> (N_GEN, LATENT_DIM); z1,z2,z3 sequential from one stream."""
    if variant == "tf_global_seed":            # notebook reading
        import tensorflow as tf
        tf.random.set_seed(SEED)
        np.random.seed(SEED)
        return {c: tf.random.normal((N_GEN, LATENT_DIM)).numpy() for c in CATEGORIES}
    if variant == "tf_second_execution":       # cell 15 run twice without re-seeding
        import tensorflow as tf
        tf.random.set_seed(SEED)
        np.random.seed(SEED)
        for _ in CATEGORIES:                    # discard first execution's draws
            tf.random.normal((N_GEN, LATENT_DIM))
        return {c: tf.random.normal((N_GEN, LATENT_DIM)).numpy() for c in CATEGORIES}
    if variant == "numpy_randn":               # SI S3 reading
        rs = np.random.RandomState(SEED)
        return {c: rs.randn(N_GEN, LATENT_DIM) for c in CATEGORIES}
    raise ValueError(variant)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    dep = Path(paths["scenarios3000_dir"]).expanduser()
    wdir = Path(paths["deepiam_weights_dir"]).expanduser()

    import tsgm
    import tensorflow as tf

    report = {"seed": SEED, "tol": TOL, "feature_order": FEATURE_ORDER,
              "env": {"python": sys.version.split()[0], "tensorflow": tf.__version__,
                      "tsgm": getattr(tsgm, "__version__", "?"), "platform": sys.platform},
              "variants": {}}

    scalers, gen_ref, decoders, regen = {}, {}, {}, {}
    for c in CATEGORIES:
        Xr, _ = load_tensor(dep / f"Real_{c}.csv", FEATURE_ORDER)
        Xg, _ = load_tensor(dep / f"Gen_{c}.csv", FEATURE_ORDER)
        sc = tsgm.utils.TSFeatureWiseScaler((0, 1))
        sc.fit(Xr)
        scalers[c], gen_ref[c] = sc, Xg
        arch = tsgm.models.zoo["vae_conv5"](SEQ_LEN, len(FEATURE_ORDER), LATENT_DIM)
        arch.decoder.load_weights(str(wdir / DECODER_FILES[c]))
        decoders[c] = arch.decoder
        report.setdefault("real_shapes", {})[c] = list(Xr.shape)

    for variant in ["tf_global_seed", "tf_second_execution", "numpy_randn"]:
        z = latents_variant(variant)
        vrep = {}
        for c in CATEGORIES:
            out = decoders[c](z[c].astype("float32"))
            out = np.asarray(scalers[c].inverse_transform(out))
            ref = gen_ref[c]
            if out.shape != ref.shape:
                vrep[c] = {"status": "SHAPE MISMATCH", "ours": list(out.shape), "ref": list(ref.shape)}
                continue
            rel = np.abs(out - ref) / np.maximum(np.abs(ref), 1e-6)
            iqr = np.quantile(ref, 0.75, axis=0) - np.quantile(ref, 0.25, axis=0)  # (T,F)
            nmax = float((np.abs(out - ref) / np.maximum(iqr, 1e-6)).max())
            vrep[c] = {"median_rel_dev": float(np.median(rel)),
                       "iqr_normalized_max_dev": nmax,
                       "frac_within_tol": float((rel <= TOL).mean()),
                       "PASS": bool(np.median(rel) <= TOL and nmax <= 1e-2)}
            regen.setdefault(variant, {})[c] = out
        vrep["PASS_all"] = all(isinstance(v, dict) and v.get("PASS")
                               for k, v in vrep.items() if k in CATEGORIES)
        report["variants"][variant] = vrep

    # ---- Distributional fidelity: our ensemble vs deposit, sample identity aside ----
    # Primary metric: quantile deviation normalized by the reference SPREAD
    # (Q90-Q10 per year x feature), not by |q| -- a near-zero quantile of a
    # phased-out variable otherwise turns tiny absolute differences into
    # huge "relative" deviations. The relative metric is kept as secondary.
    QS = [0.10, 0.25, 0.50, 0.75, 0.90]

    def qdev_metrics(A, B):
        """Quantile deviations of ensemble A vs reference B: spread-normalized + relative."""
        qa, qb = np.quantile(A, QS, axis=0), np.quantile(B, QS, axis=0)   # (Q,T,F)
        spread = np.maximum(qb[-1] - qb[0], 1e-6)                          # (T,F): Q90-Q10 of ref
        sn = np.abs(qa - qb) / spread[None, :, :]
        rel = np.abs(qa - qb) / np.maximum(np.abs(qb), 1e-6)
        return sn, rel

    dist = {"per_category": {}, "worst_cells_spread_normalized": []}
    sn_all, selfnoise_all = [], []
    ours = regen["tf_global_seed"]
    ours2 = regen["numpy_randn"]               # independent draw, same decoder
    for c in CATEGORIES:
        sn, rel = qdev_metrics(ours[c], gen_ref[c])
        sn_self, _ = qdev_metrics(ours2[c], ours[c])   # Monte Carlo noise floor
        dist["per_category"][c] = {
            "median_sn_qdev": float(np.median(sn)),
            "p95_sn_qdev": float(np.quantile(sn, 0.95)),
            "max_sn_qdev": float(sn.max()),
            "selfnoise_median_sn_qdev": float(np.median(sn_self)),
            "selfnoise_p95_sn_qdev": float(np.quantile(sn_self, 0.95)),
            "median_rel_qdev": float(np.median(rel)),
        }
        sn_all.append(sn); selfnoise_all.append(sn_self)
        wq, wt, wf = np.unravel_index(np.argsort(sn, axis=None)[-3:], sn.shape)
        for q, t, f in zip(wq, wt, wf):
            dist["worst_cells_spread_normalized"].append(
                {"cat": c, "q": QS[q], "year": 2020 + 10 * int(t),
                 "feature": FEATURE_ORDER[f], "sn_dev": float(sn[q, t, f])})
    A = np.concatenate([x.ravel() for x in sn_all])
    N = np.concatenate([x.ravel() for x in selfnoise_all])
    dist["overall"] = {"median_sn_qdev": float(np.median(A)),
                       "p95_sn_qdev": float(np.quantile(A, 0.95)),
                       "selfnoise_median": float(np.median(N)),
                       "selfnoise_p95": float(np.quantile(N, 0.95)),
                       "excess_ratio_median": float(np.median(A) / max(np.median(N), 1e-9)),
                       "excess_ratio_p95": float(np.quantile(A, 0.95) / max(np.quantile(N, 0.95), 1e-9))}
    # PASS: deviations vs deposit consistent with two independent 10k draws
    # through one decoder (within 2x the self-noise), or absolutely small.
    dist["PASS_distributional"] = bool(
        (dist["overall"]["excess_ratio_median"] <= 2.0 and
         dist["overall"]["excess_ratio_p95"] <= 2.0)
        or (dist["overall"]["median_sn_qdev"] <= 0.02 and
            dist["overall"]["p95_sn_qdev"] <= 0.10))
    report["distributional"] = dist

    # ---- Scaler-bounds diagnostic: is Real_*.csv really the scaler-fit data? ----
    # The decoder's output is (approx.) bounded by the training scaler, so the
    # deposited Gen values must lie within [min, max] fit on the true training
    # tensors. Features where the deposit exceeds the Real-CSV bounds indicate
    # the authors' scaler was fit on different data.
    sb = {}
    for c in CATEGORIES:
        Xr = None
        Xr, _ = load_tensor(Path(paths["scenarios3000_dir"]).expanduser() / f"Real_{c}.csv", FEATURE_ORDER)
        rmin, rmax = Xr.min(axis=(0, 1)), Xr.max(axis=(0, 1))          # per feature
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

    exact = next((v for v in report["variants"] if report["variants"][v]["PASS_all"]), None)
    if exact:
        report["conclusion"] = f"EXACT reproduction by variant '{exact}'"
    elif dist["PASS_distributional"]:
        report["conclusion"] = ("EXECUTABLE + DISTRIBUTIONALLY FAITHFUL (within Monte Carlo "
                                "noise of independent draws); deposited samples not "
                                "reproducible from the documented seed — determinism "
                                "finding at the generation stage, extending D1")
    else:
        report["conclusion"] = ("Distributional deviations exceed the self-noise floor — "
                                "inspect scaler_bounds and worst_cells_spread_normalized; "
                                "leading suspect: scaler fit data != Real_*.csv")
    out = Path(__file__).parent.parent / "results" / "phase0b_regeneration.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
