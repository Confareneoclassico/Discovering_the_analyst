# momp-li2025-otgsa

OT-GSA audit of the scenario-generation pipeline of:

> Li, P., Zhu, R., McJeon, H., Byers, E., Zhou, P. & Ou, Y. (2025).
> Using deep learning to generate key variables in global mitigation scenarios.
> *Nature Climate Change* 15, 760–768. doi:10.1038/s41558-025-02352-8

Part of the MoMP (Modelling of the Modelling Process) series. The pipeline —
AR6 subset → variable selection/imputation → category aggregation →
generative model (VAE/CGAN/RCGAN) → synthetic ensemble + validation — is
treated as the object of analysis. The analyst's methodological choices are
the input factors; the generated multivariate ensemble and the paper's
validation claims are the outputs. Sensitivity indices are optimal-transport
based (Wasserstein displacement of the synthetic ensemble), estimated from
given data.

## Phases

- **Phase 0 — Replication fidelity** (`phase0/`): pin all artefacts
  (`DATA.md`), reproduce the training set from the raw AR6 World CSV,
  validate the published synthetic ensemble against the paper's own source
  data. Outcome reported in the pre-registration protocol; no GSA output
  exists at protocol deposit time.
- **Phase 1 — Factorised pipeline** (`02_factorize`, to come): wrap the
  pipeline as f(θ) driven by `config/paper_values.yaml`; one YAML = one run.
- **Phase 2 — Design + OT-GSA** (to come): quasi-random sample over expensive
  factors, inner loop over cheap factors, OT indices on ensemble-level
  outputs, claim-level pass/fail tables.
- **Fingerprint test** (to come): source-IAM classifier on real vs synthetic
  scenarios (claim X5), on the eight model groups present in the 901-set
  (Phase 0E, protocol Appendix A; D15).

## Noise and null reference

The authors state (repo README, v1.0.0/v1.0.1) that TSGM training is not
reproducible even with fixed seeds, and Phase 0B found that regeneration from
the shipped weights reproduces the deposit only distributionally (D11).
Training noise is therefore part of every output. The protocol measures it in
two ways: the noise floor, the distance between ensembles from 20 retrained
replicates at the paper's values, and dummy columns drawn with the factors but
never passed to the pipeline. A factor counts as influential only if its index
clearly exceeds the mean index of the dummies with the same partition
(protocol section 8).

## Layout

```
DATA.md              artefact registry: DOIs, versions, sha256, access dates
DISCREPANCIES.md     documentation-internal inconsistencies of the target paper
config/paper_values.yaml   factor space and fixed settings, aligned with the protocol
config/local_paths.example.yaml   template; copy to config/local_paths.yaml (git-ignored)
phase0/01_metadata_check.py            AR6 metadata vs Extended Data Table 1
phase0/02_training_set_reconstruction.py  raw World CSV -> the 1,160 training set
phase0/03_synthetic_fidelity.py        Gen_/Real_ CSVs vs Source Data Fig. 3
phase0/04_evaluation_subset.py         1,160 -> 901 reconstruction (D9)
phase0/05_regeneration_check.py        Phase 0B: regeneration from shipped weights
phase0/06_code_scan.py                 Phase 0C: static scan of v1.0.0 notebooks (D4, D12, X3, G8)
phase0/07_sumcheck_reference.py        Phase 0C: AR6 sum-check reference, real data only
phase0/08_denominator_guard.py         Phase 0D: real-data denominators of X1a and the ensemble standardisation
phase0/09_model_groups.py              Phase 0E: model groups of X5 and the scenarios the D9 rule removes (D15)
protocol/preregistration.tex           protocol; \frozenfalse = release candidate
docs/FREEZE_CHECKLIST.md               ordered steps from release candidate to deposit
docs/data_raw_manifest.sha256          SHA-256 of every raw file as committed in 7ee280d (World CSV: LFS object id)
DEVIATIONS.md                          empty until the deposit
data/raw/            read-only local copies of deposits (git-ignored; AR6 licence)
data/derived/        outputs of phase0 scripts: identifier lists of the D2 and D9 populations, X5 folds
data/external/gsa2023/   results, script and README of the 2023 case, for the comparison across cases (DATA.md, C1)
results/             machine-readable reports (JSON)
```

Python ≥3.10; `pip install -r requirements.txt`.
