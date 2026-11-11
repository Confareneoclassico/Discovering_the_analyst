# Freeze checklist (release candidate v0.6 to deposited v1.0)

Steps run in this order. Nothing in steps 1 to 10 trains a model or evaluates
a claim rule.

1. Scripts and their outputs.

   Done so far. 24 October 2026: Phase 0C run and transcribed (protocol
   section 3 item 8, X3 aggregation, D4, D12 to D14, G8), the full AR6 World
   CSV restored from the LFS store (DATA.md, B2), every raw file verified
   against `docs/data_raw_manifest.sha256`, and the repository cleaned up in
   2e1ea40. 27 October: Phase 0D (`phase0/08_denominator_guard.py`). 2
   November: Phase 0E (`phase0/09_model_groups.py`). 10 November: audit before
   archiving, with an independent review of every script. It found that
   script 05 compared the regenerated and the deposited scenarios in the wrong
   order (D11), that the deposited real files are anonymous (hence Phase 0F,
   `phase0/10_deposit_crosswalk.py`, D16), and that the 901-set holds
   duplicated scenarios that the X5 folds of v0.5 separated (D17). All scripts
   were corrected or tightened (alignment by label and a positive control in
   05; exact 2% rule and more digits in 03; duplicates as fold units in 09;
   no machine path in any report; LF line endings; guards that stop a script
   instead of letting it pass on missing columns). Scripts 01, 02, 04 and 06
   to 10 were re-run on 10 November: the outputs of 01, 02, 04, 06, 07 and 08
   are the committed ones but for the machine paths and a final newline, and
   those of 09 and 10 are new. Script 05 was tested on mock deposits made with
   random weights (`docs/checks/mock_deposit_for_phase0b.py`). 11 November: a
   second independent review, of the corrected scripts. It found two gaps in
   05 (a deposit whose categories come from different executions was not
   recognised as reproduced, and an empty value was not caught), empty cells
   in 03 that fell outside its summary, and sentences of the documents that
   the reports do not support. All were corrected, and the mock test was
   extended to seven mock deposits, with decoders that are not flat. Scripts
   01, 02, 04 and 06 to 10 were then re-run under both environments of
   `requirements.txt`, with outputs identical byte for byte.

   Done on the analysis machine, 11 November 2026, with the commit of v0.6
   (269d85e). (a) `phase0/03_synthetic_fidelity.py` and
   `phase0/05_regeneration_check.py` re-run with the corrected scripts (05
   under Python 3.10.21, TensorFlow 2.13.0 and tsgm 0.0.7 on macOS arm64,
   as in September). Their reports replaced those in `results/`, and the
   text was completed from them in the next commit: from 05, protocol
   section 3 item 7 and DISCREPANCIES.md, D11; from 03, protocol section 3
   item 4, DISCREPANCIES.md, D10, and the A3 row of DATA.md. From the
   repository root,
   `grep -rn --include="*.md" --exclude=FREEZE_CHECKLIST.md "PENDING-RERUN" .`
   prints nothing (this file is excluded because it names the marker).
   (b) 08, 09 and 10 re-run, and `shasum -a 256 -c docs/pinned_outputs.sha256`
   printed OK five times.

   To do just before the freeze. (c) Re-run the manifest check of the raw
   files: `shasum -a 256 -c docs/data_raw_manifest.sha256 | grep -v ': OK$'`
   prints nothing.

2. Co-author decision on the blue text of the release candidate. Approved in
   G. Vannucci's reply to v0.3 (relayed 27 October 2026), and black since
   v0.4: the X1a normalisation, the withdrawal of G9, the evaluation set E
   and the given-data design as primary. Approved in her reply to v0.4
   (relayed 2 November 2026), and black in v0.5: all blue text of v0.4,
   including the X1a floor, the projected OT index, the matched dummies, the
   secondary criteria on the residual, log-uniform sampling of the sample
   size and the epochs multiplier, and the remaining v0.3 precision fixes.
   Approved by all co-authors at the meeting of 5 November 2026, and black in
   v0.6: the blue text of v0.5 (out-of-fold reference mixes, model groups
   with their mapping and the Dekker et al. paper, the comparison on the A
   and B matrices of the 2023 design, per-category gates and uniform
   references for X5, folds fixed from identifiers).

   Pending: the blue text of v0.6, all from the audit of 10 and 11 November
   2026. (i) Phase 0B corrected and re-run, including the sentence that
   called the regenerated ensemble distributionally faithful (section 3 item
   7), and the count of the fidelity check under its exact rule (item 4).
   (ii) Phase 0F and
   the crosswalk (section 3 item 11, section 4 X5, section 10). (iii) The
   note on G1 and G4 corrected: complete cases are the 901-set, level 828
   means native Kyoto reporting (section 5, Table 1). (iv) The X5 folds
   redone: duplicated scenarios form one unit in the outer folds and in the
   grid search's inner folds, which replaces the folds file approved on 5
   November (section 4 X5). (v) The estimators of the 2023 case named as its
   README documents them (sections 2 and 7). (vi) The timing benchmark and
   the mock test of script 05 disclosed (abstract, section 3 item 7, section
   6). Record the approval here with its date. Any later blue text needs its
   own approval.

3. External results. Done on 5 November 2026: G. Vannucci's files added in
   3d26d6d, all 19 hashes of the folder's `sha256.txt` verified
   (`final_results.rds` e13147fc...b47dac56, in DATA.md and in the protocol),
   README checked on all points, rows of A and B confirmed from the design
   matrix alone, consent to public deposit given. Done on 9 November 2026: the
   mapping finalised in the README's last section (commit 2b57183) and
   approved; README.md SHA-256 f6803180...06de346f recorded in DATA.md (C1) and
   in the configuration.

   Pending: her answers to four points on `gsa_1.R` raised by the audit (the
   pattern of claim C2 also matches the gas-with-CCS shares; "top 3" and
   the largest coefficient of claim C4 are not restricted by sign, so C4 can
   pick a negative coefficient; growth-rate metrics take part in the correlation
   screening before they are dropped; `jansen_indices_2023.csv` is written by
   no archived script). If any file of the folder changes, update its
   `sha256.txt`, the two hashes in DATA.md (C1), `sha256` and `readme_sha256`
   of `case_2023` in the configuration and the hash in protocol section 7,
   and verify again with
   `(cd data/external/gsa2023 && shasum -a 256 -c sha256.txt)`.

4. Author block: include or not (commented block with full affiliations is in
   the .tex header); confirm order. Deferred by the co-authors. Default at the
   deposit: no author block in the frozen PDF, as in every circulated version;
   the authors are the creators of the Zenodo record, whose metadata can be
   edited after publication.

5. Freeze scope: decided as G. Vannucci proposed (protocol section 10 since
   v0.4). The deposit freezes the protocol, the configuration, the Phase 0
   reports and the external results of step 3. The analysis code follows as
   a new version of the same Zenodo record, before the first run (step 14).

6. Tree. The repository tracks exactly the files listed in
   `docs/tracked_files.txt`, and `.gitignore` ignores everything else in the
   folder. From the repository root,
   `git -c core.quotePath=false ls-files | diff - docs/tracked_files.txt && echo "tree OK"`
   must print `tree OK` and nothing else. A file added to the repository is
   added to the list in the same commit.

7. Zenodo: create a new upload; under "Digital Object Identifier" answer "No"
   to "Do you already have a DOI for this upload?" and press "Get a DOI now!".
   Save the draft and copy the DOI. Deleting the draft loses the DOI.

8. Build v1.0: in `protocol/preregistration.tex` set `\frozentrue`, accept
   every `\prop{...}` approved in step 2, and fill the date and the reserved
   DOI. The frozen build fails on any remaining `\todo`, so a successful build
   is the placeholder check. Retag the configuration ("proposed v0.6" becomes
   "approved"). Record the DOI in DEVIATIONS.md and DATA.md.

9. Git: commit the frozen files and the frozen PDF
   (`git add -f protocol/preregistration.pdf`, since PDFs are git-ignored),
   and tag the commit `prereg-v1.0`. The tagged tree is the list of step 6
   plus the PDF:
   `git -c core.quotePath=false ls-files | grep -v -x 'protocol/preregistration.pdf' | diff - docs/tracked_files.txt && echo "tree OK"`.

10. Upload to the reserved Zenodo record the frozen protocol PDF and its
    .tex, README.md, DATA.md, DISCREPANCIES.md, DEVIATIONS.md (empty) and
    config/paper_values.yaml as separate files, and the whole tagged tree as
    `prereg-v1.0.zip`, made with
    `git archive --format=zip --prefix=prereg-v1.0/ -o prereg-v1.0.zip prereg-v1.0`.
    The archive holds tracked files only, with their paths, which Zenodo
    cannot keep for loose files. Check its content against the list before
    uploading:
    `unzip -Z1 prereg-v1.0.zip | grep -v '/$' | sed 's|^prereg-v1.0/||' | grep -v -x 'protocol/preregistration.pdf' | LC_ALL=C sort | diff - docs/tracked_files.txt && echo "archive OK"`.
    Licence check, to confirm here: the lists in data/derived/ hold model and
    scenario names, category and group labels, fold numbers and hashes of the
    names, no data values, whereas the AR6 licence restricts redistribution of
    substantial parts of the data. The deposit A3 does not publish these
    names: its real files carry anonymous identifiers, which the crosswalk
    resolves. `docs/diff_v100_v101/full.diff` reproduces two files of the
    Deep-IAM deposit, which is CC BY 4.0. Publish.

11. After publication, the deposited files are never edited. Every departure
    goes into DEVIATIONS.md, and results affected by a deviation are reported
    separately.

After the freeze:

12. Write to the authors of the target paper with the DOI, asking whether the
    rules of protocol section 4 represent their claims fairly, together with
    the factual questions behind D9, D11, D13, D14, D15 and D16. Any change
    their answers prompt is logged in DEVIATIONS.md, before the first run if
    they arrive in time.

13. If a public GitHub mirror is wanted, push it from a fresh history (see the
    note below), never by changing this repository's visibility.

14. Code deposit, before any run (a run is any training of a generator or any
    evaluation of a claim rule on generated data, pilots included). Write the
    analysis harness under the frozen specification, test it on mock data
    generated without the pipeline (including the null values of the indices
    and the conservativeness of the secondary criteria of protocol section
    8), lock the environment, tag the commit `harness-v1.0`, and publish it
    as a new version of the same Zenodo record with the commit hash in its
    description. Only then start the runs, and only then compute the
    comparison with the 2023 case.

Note on history. The repository must stay private. Every commit before the
v16 clean-up (2e1ea40, 24 October 2026), that is 7ee280d of 21 September to
d501294, contains `data/raw/`: the AR6 World CSV (via LFS) and metadata, the
paper PDF, the SI and the Source Data files. The commits from 382405c (2
November 2026) to 2b57183 (9 November) contain 38 files of the working folder
that were committed by mistake with `git add -A`, among them the publisher's
PDF of the target paper and the group's draft manuscript. They were removed
from the tree with the v0.6 commit, and the tree is now checked against a list
(step 6), but they remain in those commits. Redistribution of the AR6 data and
of the publisher's PDF is restricted (AR6 licence, Springer Nature copyright).
The Zenodo archive is made from the tagged tree alone and contains none of
this. If a public GitHub mirror is wanted, push it from a fresh history (for
instance an orphan branch at the tagged commit) to a new repository.
