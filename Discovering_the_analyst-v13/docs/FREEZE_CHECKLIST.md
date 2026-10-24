# Freeze checklist (release candidate v0.2 to deposited v1.0)

Steps run in this order. Nothing in steps 1 to 6 trains a model or evaluates
a claim rule.

1. Phase 0C on the analysis machine. Add `deepiam_v100_dir` to
   `config/local_paths.yaml` (the unpacked v1.0.0 tree), then run
   `python3 phase0/06_code_scan.py` and `python3 phase0/07_sumcheck_reference.py`.
   Send `results/phase0c_code_scan.txt` and `results/phase0c_sumcheck_reference.json`
   for transcription into protocol section 3 item 8, the X3 aggregation, the
   status of D4 and D12, and the `rf_code` settings of G8.

2. Co-author decision on the blue text of the release candidate. Four items
   change meaning (X1a normalisation, withdrawal of G9, first-order indices with
   the seed as dummy reference, the fixed evaluation set E); the rest are
   precision fixes. Record approvals with date in this file.

3. Author block: include or not (commented block with full affiliations is in
   the .tex header); confirm order.

4. Decide what the deposit freezes besides the protocol: (a) protocol and
   configuration only, harness written afterwards under the frozen
   specification; or (b) protocol plus the analysis harness, written and
   unit-tested on mock data before the freeze, so that the archived commit
   hash covers the code that will run. Section 10 of the protocol promises a
   harness hash, so (a) requires rewording that sentence.

5. Zenodo: create a new manual upload, press "Reserve DOI", copy the DOI.

6. Build v1.0: in `protocol/preregistration.tex` set `\frozentrue`, fill the
   date, the reserved DOI and the harness hash, and accept or delete each
   `\prop{...}`. The frozen build fails on any remaining `\todo`, so a
   successful build is the placeholder check. Also confirm
   `grep -n "proposed\|phase0c" config/paper_values.yaml` returns only
   comments that are still true.

7. Git: commit the frozen YAML, DATA.md, DISCREPANCIES.md, DEVIATIONS.md,
   results/ and (under 4b) the harness; tag the commit `prereg-v1.0`. The PDF
   records this commit's hash, so the PDF itself is added in a follow-up
   commit with `git add -f protocol/preregistration.pdf` (PDFs are git-ignored).

8. Upload to the reserved Zenodo record: protocol PDF and .tex, DATA.md,
   DISCREPANCIES.md, DEVIATIONS.md (empty), config/paper_values.yaml,
   results/*.json and *.txt, docs/diff_v100_v101/, requirements files, and a
   tarball of the tagged commit made with
   `git archive --format=tar.gz -o prereg-v1.0.tar.gz prereg-v1.0`, which
   contains tracked files only. Publish.

9. After publication, the deposited files are never edited. Every departure
   goes into DEVIATIONS.md, and results affected by a deviation are reported
   separately.

Note on history. The repository's first commit (7ee280d, 21 September 2026)
contains `data/raw/`: the AR6 World CSV (via LFS) and metadata, the paper PDF,
the SI and the Source Data files. Their redistribution is restricted (AR6
licence, Springer Nature copyright). Keep Confareneoclassico/Discovering_the_analyst
private. If a public GitHub mirror is wanted, push it from a fresh history
(e.g. an orphan branch at the tagged commit) to a new repository, never by
changing this repository's visibility.
