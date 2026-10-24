#!/usr/bin/env python3
"""Phase 0C.1: static scan of the Deep-IAM v1.0.0 notebooks. Nothing is executed.

Adjudicates from source code, before the freeze:
  D4   CGAN/RCGAN epochs (SI versus ED Table 3)
  D12  feature set and tensor shapes behind the GAN baselines of Table 1
  X3   how the electricity sum-check error is aggregated over decades
  G8   random-forest settings of the label-transfer benchmark

Usage:  python3 06_code_scan.py [--paths ../config/local_paths.yaml]
Needs:  deepiam_v100_dir in local_paths.yaml (unpacked Deep-IAM v1.0.0)
Output: ../results/phase0c_code_scan.txt
"""
import argparse, json, re
from pathlib import Path
import yaml

PATTERNS = {
    "EPOCHS":     r"\bepochs?\s*=\s*\d+|\.fit\([^)]*epoch",
    "BATCH":      r"\bbatch_size\s*=\s*\d+",
    "LR":         r"initial_learning_rate|decay_steps|decay_rate|learning_rate\s*=",
    "ARCH":       r"zoo\[|latent_dim|feat_dim|seq_len",
    "SHAPES":     r"np\.zeros\(\(|\.reshape\(|tensor.*shape|\.shape\b",
    "FEATURES":   r"features?_names\s*=|Variables\s*=\s*\[",
    "SUMCHECK":   r"(?i)sum.?check|gen_?total|SecondaryEle\b[^,\]]*[-/]|abs\([^)]*-[^)]*\)\s*/|\.sum\(axis",
    "CLASSIFIER": r"RandomForestClassifier\(|XGBClassifier\(|LogisticRegression\(",
    "METRICS":    r"accuracy_score|classification_report|confusion_matrix|precision_recall",
    "SEEDS":      r"set_seed|random\.seed|random_state\s*=|RandomState\(",
    "WEIGHTS":    r"\.h5\b|load_weights|save_weights",
    "DATA_IN":    r"read_csv\(|np\.load\(",
}
RX = {k: re.compile(v) for k, v in PATTERNS.items()}


def scan_source(name, cells, out):
    hits = 0
    for ci, src in cells:
        for li, line in enumerate(src.splitlines(), 1):
            tags = [k for k, rx in RX.items() if rx.search(line)]
            if tags:
                hits += 1
                out.append(f"{name} :: cell {ci} :: line {li} :: {','.join(tags)} :: {line.strip()[:220]}")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default=str(Path(__file__).parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    root = Path(paths["deepiam_v100_dir"]).expanduser()
    if not root.is_dir():
        raise SystemExit(f"deepiam_v100_dir not found: {root}")

    out, summary = [], []
    for nb in sorted(root.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in nb.parts:
            continue
        try:
            js = json.loads(nb.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            summary.append(f"UNREADABLE {nb.relative_to(root)}: {e}")
            continue
        cells = [(i, "".join(c.get("source", []))) for i, c in enumerate(js.get("cells", []))
                 if c.get("cell_type") == "code"]
        out.append(f"\n===== {nb.relative_to(root)} ({len(cells)} code cells) =====")
        n = scan_source(str(nb.relative_to(root)), cells, out)
        summary.append(f"{n:5d} hits  {nb.relative_to(root)}")
    for py in sorted(root.rglob("*.py")):
        out.append(f"\n===== {py.relative_to(root)} (script) =====")
        n = scan_source(str(py.relative_to(root)), [(0, py.read_text(errors='replace'))], out)
        summary.append(f"{n:5d} hits  {py.relative_to(root)}")

    report = ["Phase 0C.1 static code scan of Deep-IAM v1.0.0 (no execution)",
              f"root: {root}", "", "Per-file hit counts:"] + summary + ["", "Matches:"] + out
    dest = Path(__file__).parent.parent / "results" / "phase0c_code_scan.txt"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(summary))
    print(f"\nFull listing written to {dest}")


if __name__ == "__main__":
    main()
