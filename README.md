# Global sensitivity audit of Li et al. (2025): pre-registration archive

Optimal-transport GSA audit of the scenario-generation pipeline of:

> Li, P., Zhu, R., McJeon, H., Byers, E., Zhou, P. & Ou, Y. (2025).
> Using deep learning to generate key variables in global mitigation scenarios.
> *Nature Climate Change* 15, 760–768. doi:10.1038/s41558-025-02352-8

Part of the MoMP (Modelling of the Modelling Process) series. The pipeline
(the AR6 subset, variable selection and imputation, category aggregation, the
generative model, the synthetic ensemble and its validation) is treated as the
object of analysis. The analyst's methodological choices are the input
factors; the generated multivariate ensemble and the paper's validation claims
are the outputs. Sensitivity indices are optimal-transport based (Wasserstein
displacement of the synthetic ensemble), estimated from given data.

## Phases

- **Phase 0, replication fidelity** (`phase0/`): pin all artefacts
  (`DATA.md`), reproduce the training set from the raw AR6 World CSV,
  validate the published synthetic ensemble against the paper's own source
  data, and match the deposited real scenarios to AR6 one by one. The outcome
  is reported in the pre-registration protocol (`protocol/`, section 3) and in
  `DISCREPANCIES.md`. No GSA output exists at the time of the protocol's
  deposit.
- **Analysis harness** (to come, deposited as a new version of the Zenodo
  record before the first run): the pipeline wrapped as a function of the
  factors of `config/paper_values.yaml`, the design, the OT indices on the
  ensemble outputs and the pass or fail tables of the claims, including the
  source-model classifier of claim X5 on the eight model groups present in
  the 901-set (Phase 0E, protocol Appendix A; D15).

## Noise and null reference

The authors state (repository README, v1.0.0 and v1.0.1) that TSGM training
is not reproducible even with fixed seeds, and Phase 0B found that the
ensemble regenerated from the shipped weights differs from the deposited one
beyond Monte Carlo noise (D11). Training noise is therefore part of every
output. The protocol measures it in two ways: the
noise floor, the distance between ensembles from 20 retrained replicates at
the paper's values, and dummy columns drawn with the factors but never passed
to the pipeline. A factor counts as influential only if its index clearly
exceeds the mean index of the dummies with the same partition (protocol
section 8).

## Layout

```
README.md, DATA.md   this file; artefact registry: DOIs, versions, sha256, access dates
DISCREPANCIES.md     documentation-internal inconsistencies of the target paper (D1 to D17)
DEVIATIONS.md        log of departures from the protocol, empty at deposit
protocol/preregistration.tex           the protocol (and its frozen PDF at deposit)
config/paper_values.yaml               factor space and fixed settings, aligned with the protocol
config/local_paths.example.yaml        template; copy to config/local_paths.yaml (git-ignored)
phase0/01_metadata_check.py            AR6 metadata vs Extended Data Table 1
phase0/02_training_set_reconstruction.py  AR6 World CSV -> the 1,160 training set (D2)
phase0/03_synthetic_fidelity.py        Gen_/Real_ CSVs vs Source Data Fig. 3
phase0/04_evaluation_subset.py         1,160 -> 901 reconstruction (D9)
phase0/05_regeneration_check.py        Phase 0B: regeneration from the shipped weights (D11)
phase0/06_code_scan.py                 Phase 0C: static scan of the v1.0.0 notebooks (D4, D12, X3, G8)
phase0/07_sumcheck_reference.py        Phase 0C: AR6 sum-check reference, real data only (D13)
phase0/08_denominator_guard.py         Phase 0D: real-data denominators of X1a and of the ensemble standardisation
phase0/09_model_groups.py              Phase 0E: model groups of X5, scenarios the D9 rule removes (D15), X5 folds
phase0/10_deposit_crosswalk.py         Phase 0F: deposited real scenarios matched to AR6 (D16, D17), crosswalk
results/             machine-readable reports of the scripts above (JSON, text)
data/derived/        identifier lists written by the scripts: the 42 scenarios dropped by D2, the 901-set,
                     the X5 folds, the crosswalk between the deposited real rows and AR6 (no data values)
data/external/gsa2023/   results, scripts and README of the 2023 case, for the comparison across cases (DATA.md, C1)
data/raw/            read-only local copies of the deposits (git-ignored, not archived; AR6 licence)
docs/FREEZE_CHECKLIST.md               ordered steps from release candidate to deposit, with the approvals
docs/tracked_files.txt                 every file of the repository, one per line; the tree is checked against it
docs/pinned_outputs.sha256             SHA-256 of the outputs of scripts 08, 09 and 10
docs/data_raw_manifest.sha256          SHA-256 of every raw file (World CSV: Git LFS object id)
docs/sha256_uploads_2026-09-16.txt     the same hashes as first recorded on 16 September 2026
docs/diff_v100_v101/                   diff between Deep-IAM v1.0.0 and v1.0.1 (D7)
docs/timing/                           timing benchmark that sized the compute budget (protocol section 6)
docs/checks/check_design_2023.py       structural check of the 2023 design (rows of A and B), design matrix only
docs/checks/mock_deposit_for_phase0b.py   test of script 05 on mock deposits made with random weights
requirements.txt, requirements-deepiam-env.txt   Python packages of the Phase 0 scripts; the authors' pinned environment
.gitignore, .gitattributes             only the files above are tracked; no end-of-line conversion
```

## Re-running Phase 0

Scripts run from `phase0/`, with the machine's paths in `config/local_paths.yaml`. Scripts 01,
02, 04, 09 and 10 need the AR6 files (B1, B2 of `DATA.md`); 03, 05, 07, 08 and 10 the
synthetic-scenario deposit (A3), of which only 03 and 05 open the synthetic files; 03 the
paper's Source Data Fig. 3 (A7); 05 and 06 the Deep-IAM deposits (A1, A2), and 05 the authors'
pinned environment. The order matters only for 02, 04, 09 and 10, which pass the identifier
lists of `data/derived/` to one another.

Every script but 05 is deterministic. Scripts 08, 09 and 10 write no machine-dependent
information and round their figures, so their outputs are pinned by SHA-256 in
`docs/pinned_outputs.sha256` (`shasum -a 256 -c docs/pinned_outputs.sha256` from the repository
root); the pins were reproduced under two Python environments (`requirements.txt`), with
the input lists in shuffled order, and on the analysis machine. Script 05 depends on the
TensorFlow build and reports its environment; it checks itself with a positive control.

Python ≥3.10; `pip install -r requirements.txt`.
