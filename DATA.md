# DATA.md — artefact registry

All raw artefacts live read-only under `data/raw/`, untracked since the v16
clean-up (2e1ea40, 24 October 2026). Every earlier commit contains them, which is why
the repository stays private (history note in `docs/FREEZE_CHECKLIST.md`).
`sha256` values below were computed on the copies in hand on 2026-09-16 and
re-verified on 2026-10-24 against the copies committed in 7ee280d. The raw
files are also listed one by one in `docs/data_raw_manifest.sha256`, so the
whole folder is verified from the repository root with
`shasum -a 256 -c docs/data_raw_manifest.sha256 | grep -v ': OK$'`, which
prints only mismatches and missing files. Entries marked ⬜ are pending on the
analysis machine. Hashes are SHA-256 unless labelled otherwise (`shasum`
without `-a 256` gives SHA-1).

## Target-paper artefacts

| # | Artefact | Source / DOI | Version pinned | sha256 | Status |
|---|----------|--------------|----------------|--------|--------|
| A1 | Deep-IAM code deposit (audited object), CC BY 4.0 | 10.5281/zenodo.15280653 | **v1.0.0**, published 2025-04-25 (cited by the paper) | archive: Zenodo MD5 f79d8b2511ea5fa92c06ebec3f25693b (`Anderson111-maker/Deep-IAM-v1.0.0.zip`, 144.6 MB); unpacked tree: per file in the manifest (207 files); SHA-1 0b59a7bb97ee8ce9a0ca505f32aa191ca28b0c5c (recorded 2026-09) | ✔ |
| A2 | Deep-IAM code deposit (2026 update), CC BY 4.0 | concept DOI 10.5281/zenodo.15280652 → version DOI of v1.0.1: 10.5281/zenodo.19751070 | v1.0.1, 2026-04-25 | archive: Zenodo MD5 2796d01e68e7a185172ee2685e26e1c7 (`Anderson111-maker/Deep-IAM-v1.0.1.zip`, 144.6 MB); unpacked tree: per file in the manifest (209 files); SHA-1 ff7817b5d9cac8ae4419447f565bbcf554df7248 (recorded 2026-09) | ✔ diff vs A1 archived in `docs/diff_v100_v101/` (D7) |
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

**Pins for A1 and A2.** The Deep-IAM zips are not kept locally:
`data/raw/Anderson111/` holds the unpacked trees, which are what the scripts
read. The archives are pinned by the MD5 that Zenodo publishes with each file
(re-verify a re-download with `md5 <zip>` on macOS or `md5sum <zip>`), and
the unpacked trees file by file in `docs/data_raw_manifest.sha256`, without
the authors' `.DS_Store` files. The SHA-1 values were recorded in September
2026 without a note of the file hashed, and are kept for the record only.

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
| B2 | AR6 Scenarios Database World timeseries CSV (361,767,203 bytes) | same | **v1.1** | 4cf39b6b0d968e25ed389318acb1674f92146f977e9db4bfb7970f048ff73977 (Git LFS object id of the copy committed in 7ee280d) | ✔ pinned; full file restored on the analysis machine and verified against the manifest, 2026-10-24 (see note) |

**B2 on the analysis machine.** On 2026-10-24 the copy in `data/raw/` hashed
to 0e73f807742fdf748e86c9dab5f3de1f8fb29ba8bef8e3487f7a02e2017f7a69, which is
the SHA-256 of the 134-byte Git LFS pointer, not of the data: the folder was
checked out without LFS. The pin above is the LFS object id, which is the
SHA-256 of the file committed on 2026-09-21. The object is in the repository's
LFS store on GitHub: on 2026-10-24 it was downloaded and its SHA-256
recomputed, then deleted. The full file was restored on the analysis machine
the same day with `git lfs pull`, before `data/raw/` was untracked, and the
manifest check passed. On any other machine, with Git LFS installed, run from
the repository root
`git show d501294:data/raw/AR6_Scenarios_Database_World_v1.1/AR6_Scenarios_Database_World_v1.1.csv | git lfs smudge > data/raw/AR6_Scenarios_Database_World_v1.1/AR6_Scenarios_Database_World_v1.1.csv`
(tested on 2026-10-24: the output hashes to the pinned value) and confirm the
SHA-256 before any script reads the file.

**Availability (resolved in Phase 0).** Both reconstructed populations
(680/308/172 and 554/237/110) were reproduced exactly from the downloadable
v1.1 World CSV, so no scenario the paper used is missing from the bulk
download.

**Licence.** The AR6 Scenario Explorer licence permits scientific use but
restricts redistribution of substantial parts of the data. Raw AR6 files
(B1, B2) are therefore not tracked or deposited, only cited. The derived
lists in `data/derived/` contain model and scenario identifiers and category
labels, no data values; check them against the licence FAQ before the
repository becomes public.

## Provenance rules

1. Nothing in `data/raw/` is ever edited; derived objects go to `data/derived/`
   with the generating script + config recorded in the filename or sidecar JSON.
2. Every table in the pre-registration protocol cites the artefact IDs above.
3. Access dates: all items above first retrieved 2026-09 (record exact dates
   per item when hashing on the analysis machine).
