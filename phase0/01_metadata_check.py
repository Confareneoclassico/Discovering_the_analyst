#!/usr/bin/env python3
"""Phase 0.1 — AR6 metadata vs Li et al. (2025) Extended Data Table 1.

Verifies that the local AR6 v1.1 metadata reproduces the paper's vetted
population: n = 1,202 and the exact per-category counts. Also emits the
C1234/C56/C78 aggregation and per-model counts (used later by the
fingerprint test).

Usage: python 01_metadata_check.py [--paths ../config/local_paths.yaml]
Output: ../results/phase0_metadata_check.json
"""
import json, sys, argparse, hashlib
from pathlib import Path
import pandas as pd
import yaml

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    meta_path = Path(paths["ar6_metadata_xlsx"]).expanduser()

    df = pd.read_excel(meta_path, sheet_name="meta_Ch3vetted_withclimate")
    counts = df["Category"].value_counts().to_dict()

    report = {
        "artefact": str(meta_path),
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
        "per_model_top15": df["Model"].value_counts().head(15).to_dict(),
    }
    ok = report["n_vetted_withclimate"] == 1202 and all(report["category_match"].values())
    report["PASS"] = bool(ok)

    out = Path(__file__).parent.parent / "results" / "phase0_metadata_check.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in
                      ["n_vetted_withclimate", "aggregated", "d2_gap_per_agg", "PASS"]}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
