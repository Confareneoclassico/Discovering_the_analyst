# Freeze checklist (release candidate v0.4 to deposited v1.0)

Steps run in this order. Nothing in steps 1 to 6 trains a model or evaluates
a claim rule.

1. Analysis machine. Done on 24 October 2026: Phase 0C run and transcribed
   (protocol section 3 item 8, X3 aggregation, D4, D12 to D14, G8), the full
   AR6 World CSV restored from the LFS store (DATA.md, B2), every raw file
   verified with `shasum -a 256 -c docs/data_raw_manifest.sha256 | grep -v ': OK$'`
   (no output), and the repository cleaned up in 2e1ea40. Done on 27 October
   2026: Phase 0D (`phase0/08_denominator_guard.py`, real data only), whose
   binding cells the protocol cites. Re-running it on the analysis machine
   must leave `results/phase0d_denominator_guard.json` unchanged. Re-run the
   manifest check on the analysis machine just before the freeze.

2. Co-author decision on the blue text of the release candidate. Approved in
   G. Vannucci's reply to v0.3 (relayed 27 October 2026), and black in v0.4:
   the X1a normalisation, the withdrawal of G9, the evaluation set E and the
   given-data design as primary. Her further requests are blue text in v0.4:
   the per-category band, denominator floor and maximum deviation of X1a,
   dummy columns matched to the partitions as the null reference, a
   pre-stated reading of the residual, the comparison across cases in
   relative terms and the two-step deposit. Pending: approval of the v0.4
   blue text and of the remaining v0.3 precision fixes. Record approvals with
   date in this file.

3. Author block: include or not (commented block with full affiliations is in
   the .tex header); confirm order. Deferred by the co-authors.

4. Freeze scope: decided as G. Vannucci proposed (protocol section 10 in
   v0.4). The deposit freezes the protocol, the configuration and the Phase 0
   reports. The analysis code follows as a new version of the same Zenodo
   record, before the first run (step 11).

5. Zenodo: create a new manual upload, press "Reserve DOI", copy the DOI.

6. Build v1.0: in `protocol/preregistration.tex` set `\frozentrue`, fill the
   date and the reserved DOI, and accept or delete each `\prop{...}`. The
   frozen build fails on any remaining `\todo`, so a successful build is the
   placeholder check. Also confirm that
   `grep -n "proposed\|approved\|phase0c\|phase0d" config/paper_values.yaml`
   returns only comments that are still true.

7. Git: commit the frozen YAML, DATA.md, DISCREPANCIES.md, DEVIATIONS.md,
   results/ and the frozen PDF (`git add -f protocol/preregistration.pdf`,
   since PDFs are git-ignored), and tag the commit `prereg-v1.0`.

8. Upload to the reserved Zenodo record: protocol PDF and .tex, DATA.md,
   DISCREPANCIES.md, DEVIATIONS.md (empty), config/paper_values.yaml,
   results/*.json and *.txt, the phase0/ scripts, docs/diff_v100_v101/,
   docs/data_raw_manifest.sha256, requirements files, and a
   tarball of the tagged commit made with
   `git archive --format=tar.gz -o prereg-v1.0.tar.gz prereg-v1.0`, which
   contains tracked files only. Publish.

9. After publication, the deposited files are never edited. Every departure
   goes into DEVIATIONS.md, and results affected by a deviation are reported
   separately.

After the freeze:

10. Write to the authors of the target paper with the DOI, asking whether the
    rules of protocol section 4 represent their claims fairly, together with
    the factual questions behind D9, D13 and D14. Any change their answers
    prompt is logged in DEVIATIONS.md, before the first run if they arrive in
    time.

11. Code deposit, before any run (a run is any training of a generator or any
    evaluation of a claim rule on generated data, pilots included). Write the
    analysis harness under the frozen specification, test it on mock data
    generated without the pipeline (including the null values of the indices
    and the conservativeness of the secondary criteria of protocol section
    8), lock the environment, tag the commit
    `harness-v1.0`, and publish it as a new version of the same Zenodo record
    with the commit hash in its description. Only then start the runs.

Note on history. Every commit before the v16 clean-up (2e1ea40, 24 October
2026), that is 7ee280d of 21 September to d501294, contains `data/raw/`: the
AR6 World CSV (via LFS) and metadata, the paper PDF, the SI and the Source
Data files. Their redistribution is restricted (AR6 licence, Springer Nature
copyright). Keep Confareneoclassico/Discovering_the_analyst private. If a
public GitHub mirror is wanted, push it from a fresh history (e.g. an orphan
branch at the tagged commit) to a new repository, never by changing this
repository's visibility.
