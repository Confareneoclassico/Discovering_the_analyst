# Diff between Deep-IAM v1.0.0 and v1.0.1 (D7)

Produced in September 2026 (first committed on 21 September 2026) from the two code deposits
of `DATA.md` (A1 and A2), unpacked side by side:

    diff -urN --brief Deep-IAM_v1.0.0/ Deep-IAM_v1.0.1/ > filelist.txt
    diff -urN Deep-IAM_v1.0.0/ Deep-IAM_v1.0.1/ > full.diff

`filelist.txt` names the four paths that differ. Two files exist only in v1.0.1
(`Configuration of Environments.txt` and `Policy-Generative Model/Secondary-data-generate.ipynb`);
with `-N` an absent file is compared with an empty one, so both are reported as differing and
`full.diff` reproduces them in full, the notebook as deposited. The other two paths are one
line of `README.md` (the Zenodo link) and a `.DS_Store` file. Nothing else changed between the
two versions (`DISCREPANCIES.md`, D7).

Both deposits are CC BY 4.0 (Li et al.; DOIs in `DATA.md`), which is the basis on which the
added files are reproduced here.
