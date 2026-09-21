# DATA.md — artefact registry

All raw artefacts live read-only under `data/raw/`, never committed.
`sha256` values below were computed on the copies in hand on 2026-09-16;
re-verify after any re-download (`sha256sum -c` against this file's values).
Entries marked ⬜ are pending download/verification on the analysis machine.

## Target-paper artefacts

| # | Artefact | Source / DOI | Version pinned | sha256 | Status |
|---|----------|--------------|----------------|--------|--------|
| A1 | Deep-IAM code deposit (audited object) | 10.5281/zenodo.15280653 | **v1.0.0** (cited by the paper) | 0b59a7bb97ee8ce9a0ca505f32aa191ca28b0c5c | ✔ |
| A2 | Deep-IAM code deposit (2026 update) | concept DOI 10.5281/zenodo.15280652 → version DOI of v1.0.1 (10.5281/zenodo.19751070) | v1.0.1, 2026-04-25 | ff7817b5d9cac8ae4419447f565bbcf554df7248 | ⬜diff vs A1 |
| A3 | 30,000 synthetic scenarios (`Scenarios3000/`: Gen_/Real_ C1234, C56, C78) | 10.5281/zenodo.15240553 | as published | ⬜ per-file hashes | downloaded; ⬜ hash + Phase 0 fidelity |
| A4 | Paper PDF | 10.1038/s41558-025-02352-8 | VoR 2025-06-13 | 7c4cb08176bfb164… | ✔ in hand |
| A5 | Supplementary Information (Texts 1–3, Figs S1–S10, Tables S1–S3) | article page | as published | 704f0773ec0f5e65… | ✔ in hand |
| A6 | Source Data Fig. 2 | article page | as published | d303e48867ac667e… | ✔ |
| A7 | Source Data Fig. 3 (per-category quantiles, Gen/Real, by year) | article page | as published | 2c33d046612555af… | ✔ — reference for `03_synthetic_fidelity.py` |
| A8 | Source Data Fig. 4 | article page | as published | ac1cacc73626ac42… | ✔ |
| A9 | Source Data Fig. 5 | article page | as published | 1931995921536489… | ✔ |
| A10 | Source Data Extended Data Fig. 1 | article page | as published | b066a84189e37fb3… | ✔ |
| A11 | Source Data Extended Data Fig. 2 | article page | as published | ee03d3da522ae697… | ✔ |
| A12 | Source Data Extended Data Tables 1–3 | article page | as published | 77924fc40b081688… / 2df90d0e180c68e1… / 0a1db050b58c1ef0… | ✔ |
| A13 | Deep-IAM repo README | inside A1/A2 | — | 0771f166429919f3… (v1.0.1 copy) | ✔ |

**Version policy.** A1 (v1.0.0) is the audited object: it is the artefact the
published claims rest on and the one the pre-registration pins. A2 (v1.0.1)
adds two files — `Configuration of Environments.txt` and
`Policy-Generative Model/Secondary-data-generate.ipynb` — with no changelog
on Zenodo. The A1↔A2 diff must be produced and archived (`docs/diff_v100_v101/`)
before the protocol freeze; any difference beyond the two added files is a
finding. Working hypothesis to test: `Secondary-data-generate.ipynb`
produces the electricity-sector-extended generation behind Fig. 5, i.e.
v1.0.0 alone may not reproduce Fig. 5 (→ DISCREPANCIES.md D7).

## AR6 database artefacts

| # | Artefact | Source | Version | sha256 | Status |
|---|----------|--------|---------|--------|--------|
| B1 | AR6 Scenarios Database metadata_indicators | IIASA AR6 Scenario Explorer (registration + licence) / 10.5281/zenodo.7197970 | **v1.1** | 1c1d70208bcf48c5… | ✔ verified: `meta_Ch3vetted_withclimate` = 1,202 rows; per-category counts match ED Table 1 exactly (see `results/phase0_metadata_check.json`) |
| B2 | AR6 Scenarios Database World timeseries CSV (~400 MB) | same | **v1.1** | ⬜ compute locally | on analysis machine; set path in `config/local_paths.yaml` |

**Licence note (⬜ verify at Phase 0):** confirm that every one of the 1,202
vetted scenarios (and in particular the 1,160 actually trained on) is present
in the downloadable v1.1 World CSV — some explorer scenarios are
licence-restricted and excluded from bulk downloads. Absence of any is a
protocol-relevant constraint to document.

## Provenance rules

1. Nothing in `data/raw/` is ever edited; derived objects go to `data/derived/`
   with the generating script + config recorded in the filename or sidecar JSON.
2. Every table in the pre-registration protocol cites the artefact IDs above.
3. Access dates: all items above first retrieved 2026-09 (record exact dates
   per item when hashing on the analysis machine).
