# DISCREPANCIES.md — documentation-internal inconsistencies of Li et al. (2025)

Catalogue of contradictions and undeclared degrees of freedom found in the
paper + SI + Extended Data + code deposit, established **before any GSA run**.
Analogue of the exact-replication issues section for Li P.-H. et al. (2023).
Status: OPEN (not yet adjudicated) / CONFIRMED (verified against code/data) /
RESOLVED (explanation found, note it).

## D1 — Training not reproducible by the authors' own account. [CONFIRMED by repo README]
Repo README: with TSGM, "even with random seeds, randomness occurs", hence
shipped h5 weights. Consequences: (a) seed variability (factor G6) is
irreducible; (b) defines the noise-floor design (see repo README of this
project); (c) exact-replication targets are the *generations from shipped
weights* (latent noise: numpy seed 3, SI S3), not retraining.

## D2 — Training-set arithmetic does not close: 1,202 vs 1,160. [RESOLVED 2026-09]
ED Table 1: 1,202 vetted (C1234=700, C56=309, C78=193).
SI S3.1 training counts: 680 + 308 + 172 = 1,160; CGAN tensor (1160, 10, 5).
42 scenarios dropped with no stated criterion — per category: C1234 −20,
C56 −1, C78 −21 (11% of the smallest group). **Resolved by `02_training_set_reconstruction.py`** (results/phase0_training_set.json):
the exact rule is *complete 2020–2100 coverage on the 5 feature variables,
Kyoto Gases NOT required* — reproduces 680/308/172 to the scenario; the 42
dropped are listed in `data/derived/dropped42_2020_2100_5features.csv`.
The rule remains UNDECLARED in the paper (the filter exists nowhere in
Methods/SI); it stays an undeclared-DOF entry for the protocol, now with
known content. Note the asymmetry it reveals: Kyoto is exempted (supporting
D3's label reading) and the grid is 2020–2100, not the Methods' 2010–2100
(feeding D5).

## D3 — Six key variables declared, five in the tensor. [OPEN]
SI S3.1 names six (PrimaryEnergy_Coal/Oil/Gas, FinalEnergy_Liquid,
CarbonSequestration, Kyoto Gases) then describes tensors as "(680, 10, 5) …
5 key variables". Hypothesis: Kyoto Gases is the conditioning/label variable,
not a feature. Adjudicate from the training notebooks in A1.

## D4 — Epoch/learning-rate contradictions, SI vs Extended Data Table 3. [OPEN]
- CGAN: SI S3.2 → 500 epochs, lr 1e-4; ED Table 3 → 1,500 epochs, lr 1e-4.
- RCGAN: SI S3.3 → 1,200 epochs, lr 1e-3; ED Table 3 → 1,800 epochs, lr 1e-3.
Which configuration produced Table 1 / ED Table 2 is undetermined from the
documentation. Directly relevant to claim X4 (VAE superiority): the GAN
baselines' training budget is what is in dispute. The shipped h5 files are
weights-only and carry no epoch count, so adjudication goes through the
v1.0.0 notebooks (`phase0/06_code_scan.py`, tag EPOCHS). If still ambiguous,
"which documented config" stays an explicit two-level factor nested in G5.

## D5 — Time-grid inconsistency. [SHARPENED 2026-09]
Methods: values 2010–2100, 10-year step (10 points). SI S2.1: "time step of 9
(2020 to 2100)"; SI S3.1 tensors "(·, 10, ·)". Now confirmed from
`Secondary-data-generate.ipynb` (v1.0.1): the extended/deposited pipeline
builds `X = np.zeros((data_num, 9, nft))` on **2020–2100 (9 steps)**, and the
D2 completeness filter is likewise 2020–2100. So the 9-step grid governs the
deposited data and Fig. 5, while SI S3.1's 10-step claim matches at most the
6-variable models. Record per-figure grid in the protocol.

## D6 — Deposit folder `Scenarios3000` vs 30,000 scenarios. [RESOLVED 2026-09]
Row counts verified by `03_synthetic_fidelity.py`: Gen files = 10,000 each
(30,000 total ✓); folder name is sloppy. Real files = 554/237/110 → see D9.

## D7 — v1.0.0 vs v1.0.1 of the code deposit. [CONFIRMED 2026-09]
Diff archived (`docs/diff_v100_v101/`). v1.0.1 = v1.0.0 + two ADDED files
(`diff -urN` shows them as "differ" only because -N compares against empty;
`nbdiff` confirms the notebook is absent from v1.0.0) + one README line
(the Zenodo link) + .DS_Store noise. Nothing else changed.
`Secondary-data-generate.ipynb` is confirmed as the generator of the
deposited data: it trains the VAE on the extended 16-variable set (5
features + Kyoto + 10 electricity fuel-level variables, CS pre-imputed from
`Carbon_Sequestration_CCS_imputed.csv`), latent dim 10, generation noise
`tf.random.normal((10000,10))` with global seed 3, per-category decoders.
**Consequence: v1.0.0 — the version the paper cites — cannot reproduce the
deposited synthetic scenarios or Fig. 5.** The generating code appeared ten
months after publication, unannounced. Protocol wording: audited object
v1.0.0 + `Secondary-data-generate.ipynb` and `Configuration of
Environments.txt` from v1.0.1 admitted as documented supplements.

## D8 — Upstream leverage of imputation. [DESIGN NOTE]
Mean-imputation by year × climate category (Methods) is applied *before*
feature selection and training, and the 100-variable pool is defined by a
>80%-reporting completeness criterion. Both sit upstream of everything else;
factor G4's innocuous description understates its leverage. Also note the
imputation conditions on the category label — the label later predicted in
the label-transfer benchmark (potential circularity to examine when
operationalising X4).

## D9 — Second undocumented drop: 1,160 → 901 (554/237/110). [RESOLVED 2026-09]
The deposited Real_*.csv hold 554/237/110 scenarios (901 total), matching
Fig. 4a (n=554), ED Fig. 2 legends and Table 1/ED Table 2 testing samples —
not the SI S3.1 training counts (680/308/172). Mechanism indicated by
`Secondary-data-generate.ipynb`: "intersection of the models and scenarios
contained in each variable" over the 16-variable set. So the paper's
figures and label-transfer benchmark run on a 901-scenario subset produced
by a second undeclared completeness filter (C78: 172 → 110, i.e. −36% of the
smallest category). **Resolved by `04_evaluation_subset.py`** (results/phase0_evaluation_subset.json):
the exact rule is *complete 2020–2100 coverage on the 5 feature variables AND
all 10 electricity fuel-level variables, Kyoto Gases again exempt* —
reproduces 554/237/110 to the scenario. Wrinkle worth recording: the exact
match requires **raw** CS completeness, although the notebook loads
`Carbon_Sequestration_CCS_imputed.csv` — the CS-imputed variant differs only
in C78 (119 vs 110), i.e. 9 scenarios have everything but raw CS and were
nonetheless excluded. So the intersection was computed on pre-imputation
availability while training consumed the imputed file. Feeds G1 and the
population declarations in the operational rules for X1–X4.

## D10 — Unit inconsistency: deposit in Mt, Source Data in Gt. [RESOLVED 2026-09]
All 514 pre-harmonization fidelity failures were exact ×1000 ratios confined
to CarbonSequestration (244) and KyotoGases (270 = all); every EJ variable
passed at 2% rtol untouched. Deposit stores Mt(CO2/-eq), Fig. 3 source data
Gt. Harmonization now built into `03_synthetic_fidelity.py` (UNIT_SCALE);
re-run expected to PASS. Benign, but goes in the documentation-hygiene list.
Curio noted in passing: Real_C78 CarbonSequestration medians of exactly
0.0001 Mt (100 tCO2) in early decades look like an imputation floor —
inspect when the imputed CS file is examined.

## D11 — Deposited generation not tied to documented seed or shipped weights. [ESTABLISHED 2026-09, Phase 0B]
Regeneration from the shipped decoder weights under the documented seed 3
(three latent-stream readings tested) yields entirely different samples
(median elementwise rel. dev. 0.33–0.45). Distributionally, the regenerated
ensemble matches the deposit to 1.8% of spread in the median (p95 10.3%) but
sits ~4.4x above the two-independent-draws Monte Carlo floor, with the
excess in tails and tight-spread cells (CS 2020). Scaler-bounds diagnostic:
0/48 feature-category flags — Real_*.csv consistent with the scaler-fit
data. Leading explanation: the shipped h5 checkpoint is not the one that
generated the deposit (README describes multiple training sessions with
"comparable" results). Consequence: even the nominally deterministic half of
the published pipeline cannot be tied to its own archived outputs. Extends
D1 from training to generation. Reports: results/phase0b_regeneration_run{1,2}.json
and results/phase0b_regeneration.json (final).

## D12 — The model documented in SI S3 is not the model behind the figures. [OPEN — Phase 0C]
SI S3.1–S3.2 document generators trained on 1,160 scenarios with five
features on a 10-step grid (VAE tensors "(680, 10, 5)"; CGAN tensor
"(1160, 10, 5)"). The Methods instead describe generation of the key
variables together with all electricity fuel-level variables, and every
published result checked in Phase 0 corresponds to that extended
configuration: Fig. 3 and ED Fig. 2 match the deposited 16-variable, 9-step
generation of `Secondary-data-generate.ipynb`, trained on the 901-set (D9;
Phase 0 items 3 and 4; Phase 0B), and Fig. 4a and the Table 1 test sets carry
the 901-set's sizes (554/237/110). Consequences: (a) the paper's own
configuration, hence the paper value of factor G1, is the 901-rule, not the
1,160-rule (corrected in protocol v0.2); (b) open: whether the CGAN and
RCGAN baselines of Table 1 / ED Table 2 were trained on the 5-feature,
1,160-scenario configuration (as SI S3.2 states) or on the extended one (as
the Methods state). If the former, the published VAE-versus-GAN comparison
was not like-for-like: the generators would differ in training population
(901 versus 1,160 scenarios) and in the variables available to the
label-transfer classifier (16 versus 5). Adjudicate from the v1.0.0 notebooks
(`phase0/06_code_scan.py`, tags SHAPES, FEATURES, DATA_IN). Our X4 rule is
like-for-like by construction, whatever the outcome.
