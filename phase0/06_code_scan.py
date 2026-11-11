#!/usr/bin/env python3
"""Phase 0C.1: static scan of the Deep-IAM v1.0.0 notebooks. Nothing is executed.

Adjudicates from source code, before the freeze:
  D4   CGAN/RCGAN epochs (SI versus ED Table 3)
  D12  feature set and tensor shapes behind the GAN baselines of Table 1
  X3   how the electricity sum-check error is aggregated over decades
  G8   random-forest settings of the label-transfer benchmark

Only the code cells of the notebooks are read, never their saved outputs. Files are named by
their relative paths with forward slashes and listed folder by folder, and the report names
no local directory, so it is the same on every machine.

Usage:  python3 06_code_scan.py [--paths ../config/local_paths.yaml]
Needs:  deepiam_v100_dir in local_paths.yaml (unpacked Deep-IAM v1.0.0; DATA.md, A1)
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


def write_lf(path, text):
    """Write text with LF line endings on every platform."""
    Path(path).write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


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
    ap.add_argument("--paths", default=str(Path(__file__).resolve().parent.parent / "config" / "local_paths.yaml"))
    args = ap.parse_args()
    paths = yaml.safe_load(open(args.paths))
    root = Path(paths["deepiam_v100_dir"]).expanduser()
    if not root.is_dir():
        raise SystemExit(f"deepiam_v100_dir not found: {root}")

    def listed(pattern):
        """Files under root matching the pattern, named by their relative paths with forward slashes and
        ordered folder by folder (by the components of the path, compared as case-sensitive strings)."""
        found = [(p.relative_to(root).as_posix(), p) for p in root.rglob(pattern)
                 if ".ipynb_checkpoints" not in p.parts]
        return sorted(found, key=lambda t: t[0].split("/"))

    out, summary = [], []
    for name, nb in listed("*.ipynb"):
        try:
            js = json.loads(nb.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            summary.append(f"UNREADABLE {name}: {e}")
            continue
        cells = [(i, "".join(c.get("source", []))) for i, c in enumerate(js.get("cells", []))
                 if c.get("cell_type") == "code"]
        out.append(f"\n===== {name} ({len(cells)} code cells) =====")
        n = scan_source(name, cells, out)
        summary.append(f"{n:5d} hits  {name}")
    for name, py in listed("*.py"):
        out.append(f"\n===== {name} (script) =====")
        n = scan_source(name, [(0, py.read_text(encoding="utf-8", errors="replace"))], out)
        summary.append(f"{n:5d} hits  {name}")

    report = ["Phase 0C.1 static code scan of Deep-IAM v1.0.0 (no execution)",
              "root: the unpacked Deep-IAM v1.0.0 deposit (deepiam_v100_dir; DATA.md, A1)", "",
              "Per-file hit counts:"] + summary + ["", "Matches:"] + out
    dest = Path(__file__).resolve().parent.parent / "results" / "phase0c_code_scan.txt"
    dest.parent.mkdir(exist_ok=True)
    write_lf(dest, "\n".join(report) + "\n")
    print("\n".join(summary))
    print("\nFull listing written to results/" + dest.name)


if __name__ == "__main__":
    main()
