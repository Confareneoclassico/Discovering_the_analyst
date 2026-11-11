#!/usr/bin/env python3
"""Phase 0.1: AR6 metadata versus Extended Data Table 1 of Li et al. (2025).

Verifies that the AR6 v1.1 metadata reproduces the paper's vetted population:
n = 1,202 and the exact count of each category. It also reports the three
aggregated categories against the training counts of SI S3.1 (the gap of 42
scenarios is D2) and the fifteen most frequent model versions. The model groups
of claim X5 are counted in Phase 0E (09_model_groups.py), not here.

Usage:  python3 01_metadata_check.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0_metadata_check.json
"""
import argparse, hashlib, json, sys
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
ED_TABLE1 = {"C1": 97, "C2": 133, "C3": 311, "C4": 159,
             "C5": 212, "C6": 97, "C7": 164, "C8": 29}   # total 1202
AGG = {"C1234": ["C1", "C2", "C3", "C4"], "C56": ["C5", "C6"], "C78": ["C7", "C8"]}
SI_S31_TRAINING = {"C1234": 680, "C56": 308, "C78": 172}  # total 1160 (D2)


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(ROOT / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    meta_path = Path(paths["ar6_metadata_xlsx"]).expanduser()

    df = pd.read_excel(meta_path, sheet_name="meta_Ch3vetted_withclimate")
    counts = df["Category"].value_counts().to_dict()
    per_model = df["Model"].value_counts()
    top15 = sorted(per_model.items(), key=lambda kv: (-kv[1], kv[0]))[:15]   # ties in name order, not in row order

    report = {
        "artefact": meta_path.name,
        "sha256": sha256(meta_path),
        "n_vetted_withclimate": int(len(df)),
        "expected_total": 1202,
        "per_category": {k: int(counts.get(k, 0)) for k in ED_TABLE1},
        "per_category_expected": ED_TABLE1,
        "category_match": {k: counts.get(k, 0) == v for k, v in ED_TABLE1.items()},
        "aggregated": {a: int(sum(counts.get(c, 0) for c in cs)) for a, cs in AGG.items()},
        "si_s31_training_counts": SI_S31_TRAINING,
        "d2_gap_per_agg": {a: int(sum(counts.get(c, 0) for c in cs)) - SI_S31_TRAINING[a]
                            for a, cs in AGG.items()},
        "n_unique_model_versions": int(df["Model"].nunique()),
        "per_model_top15": {str(k): int(v) for k, v in top15},
    }
    ok = report["n_vetted_withclimate"] == 1202 and all(report["category_match"].values())
    report["PASS"] = bool(ok)

    out = ROOT / "results" / "phase0_metadata_check.json"
    out.parent.mkdir(exist_ok=True)
    write_lf(out, json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in
                      ["n_vetted_withclimate", "aggregated", "d2_gap_per_agg", "PASS"]}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
