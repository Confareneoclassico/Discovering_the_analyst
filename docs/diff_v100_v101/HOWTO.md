# Producing the v1.0.0 vs v1.0.1 diff (D7)
1. Download both version tarballs from Zenodo (concept DOI 10.5281/zenodo.15280652).
2. Record both version DOIs and tarball sha256 in DATA.md (A1, A2).
3. Unpack side by side, then:
   diff -urN --brief Deep-IAM_v1.0.0/ Deep-IAM_v1.0.1/ > filelist.diff
   diff -urN Deep-IAM_v1.0.0/ Deep-IAM_v1.0.1/ > full.diff        # text files
   For notebooks, also compare stripped of outputs:
   pip install nbdime && nbdiff --ignore-outputs <a.ipynb> <b.ipynb>
4. Archive filelist.diff + full.diff + nbdiff outputs here.
   Expected per Zenodo file listing: only two ADDED files
   (Configuration of Environments.txt; Policy-Generative Model/Secondary-data-generate.ipynb).
   ANY other change is a finding -> DISCREPANCIES.md D7.
