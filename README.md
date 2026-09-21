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
  scenarios (claim X5).

## Noise-floor design principle

The authors state (repo README, v1.0.0/v1.0.1) that TSGM training is not
reproducible even with fixed seeds; they distribute trained weights (h5).
We therefore estimate the training-stochasticity noise floor — the OT
distance between synthetic ensembles from seed-only replications with all
factors at paper values — and pre-register that a factor counts as
influential only if its OT displacement exceeds this floor. Replication has
two modes: (a) regenerate from the authors' shipped h5 weights (should be
near-exact up to the latent-sampling seed, numpy seed 3 per SI S3);
(b) retrain from scratch (bounded below by the authors' own admission).

## Layout

```
DATA.md              artefact registry: DOIs, versions, sha256, access dates
DISCREPANCIES.md     documentation-internal inconsistencies of the target paper
config/paper_values.yaml   factor table: paper values + candidate ranges (draft)
phase0/01_metadata_check.py            AR6 metadata vs Extended Data Table 1
phase0/02_training_set_reconstruction.py  raw World CSV -> the 1,160 training set
phase0/03_synthetic_fidelity.py        Gen_/Real_ CSVs vs Source Data Fig. 3
data/raw/            read-only local copies of deposits (not committed)
data/derived/        outputs of phase0 scripts
results/             machine-readable reports (JSON)
```

Python ≥3.10; `pip install -r requirements.txt`.
