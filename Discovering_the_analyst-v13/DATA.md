# DATA.md — artefact registry

All raw artefacts live read-only under `data/raw/`, never committed.
`sha256` values below were computed on the copies in hand on 2026-09-16;
re-verify after any re-download (`sha256sum -c` against this file's values).
Entries marked ⬜ are pending on the analysis machine. Hashes are SHA-256 unless
labelled otherwise (`shasum` without `-a 256` gives SHA-1).

## Target-paper artefacts

| # | Artefact | Source / DOI | Version pinned | sha256 | Status |
|---|----------|--------------|----------------|--------|--------|
| A1 | Deep-IAM code deposit (audited object), CC BY 4.0 | 10.5281/zenodo.15280653 | **v1.0.0**, published 2025-04-25 (cited by the paper) | SHA-1 0b59a7bb97ee8ce9a0ca505f32aa191ca28b0c5c; ⬜ SHA-256 | ✔ |
| A2 | Deep-IAM code deposit (2026 update), CC BY 4.0 | concept DOI 10.5281/zenodo.15280652 → version DOI of v1.0.1: 10.5281/zenodo.19751070 | v1.0.1, 2026-04-25 | SHA-1 ff7817b5d9cac8ae4419447f565bbcf554df7248; ⬜ SHA-256 | ✔ diff vs A1 archived in `docs/diff_v100_v101/` (D7) |
| A3 | 30,000 synthetic scenarios (`Scenarios3000/`: Gen_/Real_ C1234, C56, C78), CC BY 4.0 | 10.5281/zenodo.15240553 | record labelled v2, published 2025-04-18 | per file, below | ✔ Phase 0 fidelity PASS (1,620/1,620, `results/phase0_synthetic_fidelity.json`) |
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

A3 per-file sha256 (from `results/phase0_synthetic_fidelity.json`):

| File | Scenarios | sha256 |
|------|-----------|--------|
| Gen_C1234.csv | 10,000 | 7046b5b0f1706f37c21dc5af291a4ad817fe63808c643542bce9d89a10f23035 |
| Gen_C56.csv | 10,000 | fd957b50a0819fff73a50812b7158b8c2ad75306696fd6c2db9e6ff0b5eb7aae |
| Gen_C78.csv | 10,000 | af9afb445fcc07cb3ecc0890fb2e727f15222365a43d2cc188b662cbc94c0e19 |
| Real_C1234.csv | 554 | 2a7d7327c7945ef5978b75edd3ebf7e5ecbfff1d01b40eac93cbf939cdaa3751 |
| Real_C56.csv | 237 | bd5df3a919f2d4a52c0fffc6142f98e17071f3ec70967b592de8980bab6d8b87 |
| Real_C78.csv | 110 | a773fa8cda1dd778fb818e3efac080671be72115ba8f04a489bf4432b0968c2d |

**Version policy.** A1 (v1.0.0) is the audited object: it is the artefact the
published claims rest on and the one the pre-registration pins. A2 (v1.0.1)
adds two files — `Configuration of Environments.txt` and
`Policy-Generative Model/Secondary-data-generate.ipynb` — with no changelog
on Zenodo. The A1↔A2 diff must be produced and archived (`docs/diff_v100_v101/`)
before the protocol freeze. Done: the diff shows the two added files, one
README line and .DS_Store noise only, and `Secondary-data-generate.ipynb` is
the generator of the deposited data, so v1.0.0 alone cannot reproduce the
deposit or Fig. 5 (DISCREPANCIES.md D7). Both deposits are CC BY 4.0, so the
archived diff, which reproduces the added notebook in full, may be published
with attribution to Li et al. and the record DOIs.

## AR6 database artefacts

| # | Artefact | Source | Version | sha256 | Status |
|---|----------|--------|---------|--------|--------|
| B1 | AR6 Scenarios Database metadata_indicators | IIASA AR6 Scenario Explorer (registration + licence) / 10.5281/zenodo.7197970 | **v1.1** | 1c1d70208bcf48c5… | ✔ verified: `meta_Ch3vetted_withclimate` = 1,202 rows; per-category counts match ED Table 1 exactly (see `results/phase0_metadata_check.json`) |
| B2 | AR6 Scenarios Database World timeseries CSV (~400 MB) | same | **v1.1** | ⬜ compute locally | on analysis machine; set path in `config/local_paths.yaml` |

**Availability (resolved in Phase 0).** Both reconstructed populations
(680/308/172 and 554/237/110) were reproduced exactly from the downloadable
v1.1 World CSV, so no scenario the paper used is missing from the bulk
download.

**Licence.** The AR6 Scenario Explorer licence permits scientific use but
restricts redistribution of substantial parts of the data. Raw AR6 files
(B1, B2) are therefore never committed or deposited, only cited. The derived
lists in `data/derived/` contain model and scenario identifiers and category
labels, no data values; check them against the licence FAQ before the
repository becomes public.

## Provenance rules

1. Nothing in `data/raw/` is ever edited; derived objects go to `data/derived/`
   with the generating script + config recorded in the filename or sidecar JSON.
2. Every table in the pre-registration protocol cites the artefact IDs above.
3. Access dates: all items above first retrieved 2026-09 (record exact dates
   per item when hashing on the analysis machine).
