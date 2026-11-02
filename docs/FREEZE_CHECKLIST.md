# Freeze checklist (release candidate v0.5 to deposited v1.0)

Steps run in this order. Nothing in steps 1 to 7 trains a model or evaluates
a claim rule.

1. Analysis machine. Done on 24 October 2026: Phase 0C run and transcribed
   (protocol section 3 item 8, X3 aggregation, D4, D12 to D14, G8), the full
   AR6 World CSV restored from the LFS store (DATA.md, B2), every raw file
   verified with `shasum -a 256 -c docs/data_raw_manifest.sha256 | grep -v ': OK$'`
   (no output), and the repository cleaned up in 2e1ea40. Done on 27 October
   2026: Phase 0D (`phase0/08_denominator_guard.py`, real data only), whose
   binding cells the protocol cites. Done in the sandbox on 2 November 2026:
   Phase 0E (`phase0/09_model_groups.py`, identifiers and the reporting
   coverage of the ten electricity variables), whose counts the protocol
   cites in section 3 and Appendix A and which fixes the X5 folds. Re-run
   both on the analysis machine (09 needs `ar6_metadata_xlsx` and
   `ar6_world_csv` in `config/local_paths.yaml`):
   `results/phase0d_denominator_guard.json` must keep SHA-256
   663423ec45a43ebeb9dabe7ec755a909314f3542f2cb67f16d944db20574a2e6,
   `results/phase0e_model_groups.json` SHA-256
   29e3a5b6d1dd6b360d9b537654237821c85ab3012f3e61909fc2d8b152e1e0c8 and
   `data/derived/x5_folds_901.csv` SHA-256
   0d2be6a4cee9e2fb30df23c08713888b836bcfe896a1032153588f7e95dd8ce4. Re-run
   the manifest check on the analysis machine just before the freeze.

2. Co-author decision on the blue text of the release candidate. Approved in
   G. Vannucci's reply to v0.3 (relayed 27 October 2026), and black since
   v0.4: the X1a normalisation, the withdrawal of G9, the evaluation set E
   and the given-data design as primary. Approved in her reply to v0.4
   (relayed 2 November 2026), and black in v0.5: all blue text of v0.4,
   including the X1a floor, the projected OT index, the matched dummies, the
   secondary criteria on the residual, log-uniform sampling of the sample
   size and the epochs multiplier, and the remaining v0.3 precision fixes.
   Her two X5 questions and her plan for the 2023 runs are blue text in
   v0.5: the out-of-fold reference mixes, the model groups with their
   mapping and the Dekker et al. paper (Appendix A, after Phase 0E and D15),
   and the comparison on the A and B matrices of the 2023 design. Pending:
   approval of the v0.5 blue text, which an independent review of 2 November
   2026 also tightened (per-category gates and uniform references for X5,
   folds fixed from identifiers, the A and B rows identified by the README,
   matching at the level of coordinates). Record approvals with date in this
   file.

3. External results, blocking. G. Vannucci adds the 2023 results file, the
   script that generated it and a README to `data/external/gsa2023/`. Check,
   without computing anything on the runs, that the README gives the design,
   the column dictionary, the rows that form the base matrices A and B (and
   that they are 8,192), and the mapping of the 12 factors to the coordinates
   of G1-G8 (G3, G4 and G5 have two each), saying where a correspondence is
   partial. The freeze waits until these checks pass. Record the SHA-256 of
   the results file in DATA.md (C1); it fills the protocol's third
   placeholder in step 7. Confirm her consent to deposit the files publicly
   with the protocol.

4. Author block: include or not (commented block with full affiliations is in
   the .tex header); confirm order. Deferred by the co-authors.

5. Freeze scope: decided as G. Vannucci proposed (protocol section 10 since
   v0.4). The deposit freezes the protocol, the configuration, the Phase 0
   reports and the external results of step 3. The analysis code follows as
   a new version of the same Zenodo record, before the first run (step 12).

6. Zenodo: create a new manual upload, press "Reserve DOI", copy the DOI.

7. Build v1.0: in `protocol/preregistration.tex` set `\frozentrue`, fill the
   date, the reserved DOI and the SHA-256 of the 2023 results file, and
   accept or delete each `\prop{...}` (and the `\propblock` of the Appendix A
   table). The frozen build fails on any remaining `\todo`, so a successful
   build is the placeholder check: v0.5 fails on exactly these three. Also
   confirm that
   `grep -n "proposed\|approved\|phase0c\|phase0d\|phase0e" config/paper_values.yaml`
   returns only comments that are still true, and fill
   `comparison_across_cases.case_2023.sha256` there.

8. Git: commit the frozen YAML, DATA.md, DISCREPANCIES.md, DEVIATIONS.md,
   results/, data/external/gsa2023/ and the frozen PDF
   (`git add -f protocol/preregistration.pdf`, since PDFs are git-ignored),
   and tag the commit `prereg-v1.0`.

9. Upload to the reserved Zenodo record: protocol PDF and .tex, DATA.md,
   DISCREPANCIES.md, DEVIATIONS.md (empty), config/paper_values.yaml,
   results/*.json and *.txt, the phase0/ scripts, data/derived/,
   docs/diff_v100_v101/, docs/data_raw_manifest.sha256,
   data/external/gsa2023/, requirements files, and a tarball of the tagged commit made with
   `git archive --format=tar.gz -o prereg-v1.0.tar.gz prereg-v1.0`, which
   contains tracked files only. Before uploading, confirm that the
   identifier lists of data/derived/ (model, scenario and category, no data
   values) may be published under the AR6 licence terms. Publish.

10. After publication, the deposited files are never edited. Every departure
    goes into DEVIATIONS.md, and results affected by a deviation are reported
    separately.

After the freeze:

11. Write to the authors of the target paper with the DOI, asking whether the
    rules of protocol section 4 represent their claims fairly, together with
    the factual questions behind D9, D13, D14 and D15. Any change their
    answers prompt is logged in DEVIATIONS.md, before the first run if they
    arrive in time.

12. Code deposit, before any run (a run is any training of a generator or any
    evaluation of a claim rule on generated data, pilots included). Write the
    analysis harness under the frozen specification, test it on mock data
    generated without the pipeline (including the null values of the indices
    and the conservativeness of the secondary criteria of protocol section
    8), lock the environment, tag the commit `harness-v1.0`, and publish it
    as a new version of the same Zenodo record with the commit hash in its
    description. Only then start the runs, and only then compute the
    comparison with the 2023 case.

Note on history. Every commit before the v16 clean-up (2e1ea40, 24 October
2026), that is 7ee280d of 21 September to d501294, contains `data/raw/`: the
AR6 World CSV (via LFS) and metadata, the paper PDF, the SI and the Source
Data files. Their redistribution is restricted (AR6 licence, Springer Nature
copyright). Keep Confareneoclassico/Discovering_the_analyst private. If a
public GitHub mirror is wanted, push it from a fresh history (e.g. an orphan
branch at the tagged commit) to a new repository, never by changing this
repository's visibility.
