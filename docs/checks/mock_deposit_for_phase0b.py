#!/usr/bin/env python3
"""Test of phase0/05_regeneration_check.py on mock deposits. No output of the audited pipeline is
used: the decoders have RANDOM weights, and the only files read are the deposited Real_*.csv,
which the regeneration check needs to fit its scalers. No Gen_ file of the deposit is opened and
no claim rule is evaluated.

The mock decoders have the paper's architecture (tsgm vae_conv5) and random weights, with the
kernel of the last layer multiplied by GAIN. Freshly initialised decoders are nearly flat: two
independent draws through them differ by about 0.05% (median relative deviation), only a few
times the check's tolerance of 1e-4, so a test on them cannot show the tolerance's margin. With
the gain, independent draws differ by about a fifth, and the interquartile range of the generated
values is a quarter to a third of the range of the real data.

Seven mock deposits are written with a transcription of cells 14 to 18 of
Secondary-data-generate.ipynb (seeding, latents, decoding, the saving routine of cell 17), each
in its own process, and the regeneration check is run on each in a further process:

  same_seed_same_weights    seed 3 and the mock weights
                            expected: exact reproduction by the reading 'tf_global_seed', and no
                            reproduction when the files are read in file order, as the first run
                            of the check read them
  same_seed_float_noise     seed 3, the mock weights perturbed by 1e-5 of their value (more than
                            a hundred times the float32 rounding unit, 6e-8)
                            expected: exact reproduction by the reading 'tf_global_seed'
  same_seed_other_weights   seed 3, the mock weights perturbed by 5%
                            expected: not reproduced, correlation with the deposit high,
                            distributions beyond the Monte Carlo floor
  other_seed                seed 4
                            expected: not reproduced, correlation near zero, distributions
                            within the Monte Carlo floor
  mixed_executions          C1234 from a first execution of cell 15, C56 and C78 from a second
                            expected: exact reproduction category by category, C1234 by the
                            reading 'tf_global_seed', C56 and C78 by 'tf_second_execution'
  partly_other_seed         C1234 and C56 with seed 3, C78 drawn after re-seeding with 4
                            expected: partly reproduced, C78 by no reading and within the floor
  empty_cell                same_seed_same_weights with one value of Gen_C56.csv removed
                            expected: the check stops, names the cell and writes no report

Usage:  python mock_deposit_for_phase0b.py REAL_DIR WORK_DIR
        REAL_DIR  folder holding Real_C1234.csv, Real_C56.csv and Real_C78.csv (DATA.md, A3)
        WORK_DIR  empty scratch folder for the mock weights, deposits and reports
Needs:  the environment of requirements-deepiam-env.txt
Result on 11 November 2026 (Python 3.11.17, TensorFlow 2.13.1, tsgm 0.0.7, Linux x86-64, about
six minutes): all expectations hold, printed as nine PASS lines with the conclusion of each run.
Independent draws differ from the mock deposit by 0.18 to 0.22 (median relative deviation),
weights perturbed by 1e-5 by at most 1.2e-5 with an IQR-normalised maximum of 6e-4, both well
inside the tolerances of the check (1e-4 and 1e-2), and weights perturbed by 5% by 0.04 to 0.06
with a correlation of 0.96 and a distributional excess of about 10 over the Monte Carlo floor.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve()
CHECK = HERE.parents[2] / "phase0" / "05_regeneration_check.py"
CATS = ["C1234", "C56", "C78"]
FEATURES = ["CarbonSequestration", "FinalEnergy_Liquid", "PrimaryEnergy_Coal", "PrimaryEnergy_Gas",
            "PrimaryEnergy_Oil", "SecondaryEle_Nuclear", "SecondaryEle_Oil", "SecondaryEle_Solar",
            "SecondaryEle_Wind", "SecondaryEle_Hydro", "SecondaryEle_Geothermal", "SecondaryEle_Gas",
            "SecondaryEle_Coal", "SecondaryEle_Biomass", "SecondaryEle", "Kyoto_Gases"]
GAIN = 500.0
EMPTY = ("Scenario:4321", "SecondaryEle_Wind", "2060")          # the cell removed in empty_cell
# name: (seed, relative perturbation of the weights)
MOCKS = {"same_seed_same_weights": (3, 0.0), "same_seed_float_noise": (3, 1e-5),
         "same_seed_other_weights": (3, 0.05), "other_seed": (4, 0.0),
         "mixed_executions": (3, 0.0), "partly_other_seed": (3, 0.0)}


def make_weights(work):
    """Three decoders of the paper's architecture with random weights, saved under the names of the deposit."""
    import tensorflow as tf, tsgm
    (work / "weights").mkdir(parents=True)
    for i in (1, 2, 3):
        tf.random.set_seed(100 + i)
        decoder = tsgm.models.zoo["vae_conv5"](9, 16, 10).decoder
        w = decoder.get_weights()
        w[-2] = w[-2] * GAIN                     # kernel of the last layer; w[-1] is its bias
        decoder.set_weights(w)
        decoder.save_weights(str(work / "weights" / f"Policy-decoder{i}_weights-Se.h5"))


def make_deposit(real, work, name):
    """One mock deposit: the notebook's generation and saving, with the mock decoders."""
    import numpy as np, pandas as pd, tensorflow as tf, tsgm
    seed, perturb = MOCKS[name]
    dep = work / name
    dep.mkdir()

    def real_tensor(path):
        df = pd.read_csv(path)
        df["k"] = df["Scenario"].str.replace("Scenario:", "", regex=False).astype(int)
        years = [str(y) for y in range(2020, 2101, 10)]
        return np.stack([df[df["Variable"] == f].sort_values("k")[years].to_numpy(float) for f in FEATURES], axis=-1)

    def convert_to_wide_format_and_save(data_array, feature_names, csv_path):
        """Cell 17 of the notebook, with the output file as an argument."""
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
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    decoders, scalers = {}, {}
    for i, c in enumerate(CATS, 1):
        arch = tsgm.models.zoo["vae_conv5"](9, 16, 10)
        arch.decoder.load_weights(str(work / "weights" / f"Policy-decoder{i}_weights-Se.h5"))
        if perturb:
            rs = np.random.RandomState(50 + i)
            arch.decoder.set_weights([w * (1 + perturb * rs.standard_normal(w.shape)) for w in arch.decoder.get_weights()])
        decoders[c] = arch.decoder
        scalers[c] = tsgm.utils.TSFeatureWiseScaler((0, 1))
        scalers[c].fit_transform(real_tensor(real / f"Real_{c}.csv"))
        shutil.copyfile(real / f"Real_{c}.csv", dep / f"Real_{c}.csv")
    tf.random.set_seed(seed)                    # cells 14 and 15
    np.random.seed(seed)
    z = {c: tf.random.normal((10000, 10)) for c in CATS}
    if name == "mixed_executions":              # cell 15 executed a second time; C56 and C78 taken from it
        z2 = {c: tf.random.normal((10000, 10)) for c in CATS}
        z = {"C1234": z["C1234"], "C56": z2["C56"], "C78": z2["C78"]}
    if name == "partly_other_seed":             # C78 drawn again after re-seeding with 4
        tf.random.set_seed(4)
        z["C78"] = tf.random.normal((10000, 10))
    for c in CATS:
        gen = scalers[c].inverse_transform(decoders[c](z[c])).numpy()
        convert_to_wide_format_and_save(gen, FEATURES, dep / f"Gen_{c}.csv")
    write_paths(work, name, dep)


def write_paths(work, name, dep):
    (work / f"paths_{name}.yaml").write_text(
        f"scenarios3000_dir: {json.dumps(str(dep))}\ndeepiam_weights_dir: {json.dumps(str(work / 'weights'))}\n")


def make_empty_cell(work):
    """A copy of same_seed_same_weights with one value of Gen_C56.csv removed, the rest of the file unchanged."""
    src, dep = work / "same_seed_same_weights", work / "empty_cell"
    shutil.copytree(src, dep)
    path = dep / "Gen_C56.csv"
    lines = path.read_text(encoding="utf-8-sig").split("\n")
    column = lines[0].split(",").index(EMPTY[2])
    hits = 0
    for n, line in enumerate(lines):
        fields = line.split(",")
        if fields[:2] == [EMPTY[0], EMPTY[1]]:
            fields[column] = ""
            lines[n] = ",".join(fields)
            hits += 1
    if hits != 1:
        raise SystemExit(f"empty_cell: {hits} rows found for {EMPTY[:2]}")
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    write_paths(work, "empty_cell", dep)


def main():
    if len(sys.argv) == 4:                      # child process: one step
        real, work, step = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
        make_weights(work) if step == "weights" else make_deposit(real, work, step)
        return
    real, work = Path(sys.argv[1]).expanduser().resolve(), Path(sys.argv[2]).expanduser().resolve()
    if work.exists() and any(work.iterdir()):
        raise SystemExit(f"{work} is not empty")
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TF_CPP_MIN_LOG_LEVEL="3")
    for step in ["weights", *MOCKS]:
        subprocess.run([sys.executable, str(HERE), str(real), str(work), step], check=True, env=env)
    make_empty_cell(work)

    reports, runs = {}, {}
    for name in [*MOCKS, "empty_cell"]:
        out = work / f"report_{name}.json"
        runs[name] = subprocess.run([sys.executable, str(CHECK), "--paths", str(work / f"paths_{name}.yaml"),
                                     "--out", str(out)], env=env, capture_output=True, text=True)
        if runs[name].returncode == 0 and out.exists():
            reports[name] = json.loads(out.read_text())

    def facts(name):
        r = reports.get(name)
        if r is None:                           # the check failed: every expectation on this run fails
            return None
        v = r["variants"]["tf_global_seed"]
        return {"conclusion": r["conclusion"],
                "by": r["reproduced_by"],
                "reproduced": any(r["reproduced_by"][c] for c in CATS),
                "correlation": min(v[c]["median_correlation"] for c in CATS),
                "max_abs_correlation": max(abs(v[c]["median_correlation"]) for c in CATS),
                "within_floor": r["distributional"]["PASS_distributional"],
                "C78_within_floor": r["distributional"]["per_category"]["C78"]["PASS_distributional"],
                "file_order_fails": not all(v[c]["first_run_file_order"]["median_rel_dev"] <= r["tol"] for c in CATS)}

    f = {name: facts(name) for name in MOCKS}
    exact_global = lambda x: bool(x) and x["conclusion"].startswith("EXACT reproduction by reading 'tf_global_seed'")
    empty = runs["empty_cell"]
    expected = {
        "same_seed_same_weights": exact_global(f["same_seed_same_weights"])
            and f["same_seed_same_weights"]["correlation"] > 0.999,
        "same_seed_same_weights, read in file order as the first run did, is not reproduced":
            bool(f["same_seed_same_weights"]) and f["same_seed_same_weights"]["file_order_fails"],
        "same_seed_float_noise": exact_global(f["same_seed_float_noise"]),
        "same_seed_other_weights": bool(f["same_seed_other_weights"])
            and not f["same_seed_other_weights"]["reproduced"]
            and f["same_seed_other_weights"]["correlation"] > 0.8
            and not f["same_seed_other_weights"]["within_floor"],
        "other_seed": bool(f["other_seed"]) and not f["other_seed"]["reproduced"]
            and f["other_seed"]["max_abs_correlation"] < 0.05 and f["other_seed"]["within_floor"],
        "mixed_executions": bool(f["mixed_executions"])
            and f["mixed_executions"]["conclusion"].startswith("EXACT reproduction, category by category")
            and f["mixed_executions"]["by"] == {"C1234": ["tf_global_seed"], "C56": ["tf_second_execution"],
                                                "C78": ["tf_second_execution"]},
        "partly_other_seed": bool(f["partly_other_seed"])
            and f["partly_other_seed"]["conclusion"].startswith("PARTLY REPRODUCED")
            and "tf_global_seed" in f["partly_other_seed"]["by"]["C1234"]
            and "tf_global_seed" in f["partly_other_seed"]["by"]["C56"]
            and f["partly_other_seed"]["by"]["C78"] == [] and f["partly_other_seed"]["C78_within_floor"],
        "empty_cell stops the check without a report": empty.returncode != 0
            and not (work / "report_empty_cell.json").exists()
            and "empty or non-numeric" in empty.stderr and EMPTY[0] in empty.stderr,
        "controls of the six runs with a report": len(reports) == len(MOCKS) and all(
            r["controls"]["positive_control"]["PASS"] and r["controls"]["regeneration_repeatable_in_process"]
            for r in reports.values()),
    }
    for name, ok in expected.items():
        print(("PASS  " if ok else "FAIL  ") + name)
    for name, run in runs.items():
        said = reports[name]["conclusion"] if name in reports else \
            f"exit {run.returncode}: {(run.stderr.strip().splitlines() or [''])[-1]}"
        print(f"      {name}: {said}")
    sys.exit(0 if all(expected.values()) else 1)


if __name__ == "__main__":
    main()
