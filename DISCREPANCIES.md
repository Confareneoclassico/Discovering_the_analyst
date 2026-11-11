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
(feeding D5). The exemption is explained by D16: the pipeline's Kyoto Gases
are an AR6 diagnostic that every vetted scenario has in every decade from 2020
to 2100, so on that grid they can never bind.

## D3 — Six key variables declared, five in the tensor. [OPEN]
SI S3.1 names six (PrimaryEnergy_Coal/Oil/Gas, FinalEnergy_Liquid,
CarbonSequestration, Kyoto Gases) then describes tensors as "(680, 10, 5) …
5 key variables". Hypothesis: Kyoto Gases is the conditioning/label variable,
not a feature. Adjudicate from the training notebooks in A1. See D12 and D14
(Phase 0C) for the feature sets of the two notebook families, and D16 for the
AR6 variable behind Kyoto Gases.

## D4 — Epoch/learning-rate contradictions, SI vs Extended Data Table 3. [RESOLVED 2026-10, Phase 0C]
- CGAN: SI S3.2 → 500 epochs, lr 1e-4; ED Table 3 → 1,500 epochs, lr 1e-4.
- RCGAN: SI S3.3 → 1,200 epochs, lr 1e-3; ED Table 3 → 1,800 epochs, lr 1e-3.
Resolved by `phase0/06_code_scan.py` (results/phase0c_code_scan.txt): the two
documents describe two different model families in the v1.0.0 deposit. The
SI's numbers are those of the five-feature "Top6" notebooks (CGAN 500 epochs,
RCGAN 1,200, VAE 2,000). ED Table 3's are those of the sixteen-variable
"Secondary" notebooks (VAE 3,000 epochs with batches 50/30, CGAN 1,500, RCGAN
1,800), with two slips: the C78 VAE uses batch size 25 in the code against 30
in the table, and the RCGAN uses decay_steps 1,000 against 200. The paper's
configuration, and therefore our paper values, follow the Secondary code. The
nested two-level factor in G5 is dropped. See D12 for which family produced
the published results.

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
population declarations in the operational rules for X1–X4. Which scenarios the rule removes,
by model, is established under D15: all IMAGE and WITCH scenarios, for want of
geothermal electricity. Phase 0F (D16) confirms the reconstruction scenario by
scenario: every one of the 901 deposited scenarios equals the AR6 values of
its counterpart in `data/derived/kept901_5feat+elec10.csv` on all sixteen
variables, raw carbon sequestration included.

## D10 — Unit inconsistency: deposit in Mt, Source Data in Gt. [RESOLVED 2026-09]
All 514 pre-harmonization fidelity failures were exact ×1000 ratios confined
to CarbonSequestration (244) and KyotoGases (270 = all); every EJ variable
passed at 2% rtol untouched. Deposit stores Mt(CO2/-eq), Fig. 3 source data
Gt. With the conversion built into `03_synthetic_fidelity.py` (UNIT_SCALE),
all 1,620 comparisons passed in the first run (results/phase0_synthetic_fidelity.json).
Benign, but goes in the documentation-hygiene list.

Re-run of 11 November 2026, with the corrected script on the analysis
machine. The first run allowed 2.1% of the reference (`np.isclose` with an
absolute term of 0.1% of the reference on top of the 2%) and wrote its
quantiles rounded to four decimals, which left two comparisons with references
near zero (C78 carbon sequestration, Q10 in 2080 and 2090, 0.0043 and 0.0023
Gt) undecided under the protocol's 2%. The corrected script applies the rule
as stated (2% of the reference plus 1e-9 in the units of the sheet, quantiles
kept to ten significant digits) and lists empty cells and series it does not
compare. All 1,620 comparisons pass, with no empty cell and no series left
out. The largest relative deviation is 1.0e-15 for the 810 synthetic
comparisons and 4.7e-15 for the 780 real ones whose reference is not near
zero (the other 30 differ by at most 3e-23 in absolute terms): the Source Data
quantiles are those of the deposited files up to rounding.
Curio noted in passing: Real_C78 CarbonSequestration medians of exactly
0.0001 Mt (100 tCO2) in early decades look like an imputation floor —
inspect when the imputed CS file is examined.

## D11 — Deposited generation not tied to the shipped weights. [ESTABLISHED 2026-09, Phase 0B; scenario-level part corrected and re-run 2026-11-11]
As distributions, the ensemble regenerated from the shipped decoder weights
under the documented seed 3 matches the deposit to 1.8% of spread in the
median (p95 10.3%), but sits about 4.4 times above the Monte Carlo floor of
two independent 10,000-draw ensembles through the same decoder, with the
excess in tails and tight-spread cells (CS 2020). Scaler-bounds diagnostic:
0/48 feature-category flags, so the Real_*.csv are consistent with the
scaler-fit data. Leading explanation: the shipped h5 checkpoint is not the one
that generated the deposit (the README describes multiple training sessions
with "comparable" results). Consequence: even the nominally deterministic half
of the published pipeline cannot be tied to its own archived outputs. Extends
D1 from training to generation. These figures do not depend on the order of
the scenarios.

Correction of 10 November 2026. The scenario-by-scenario comparison of the
first run (19 September 2026) was void. `Secondary-data-generate.ipynb`
(cell 17) labels the i-th generated scenario `Scenario:i` and sorts the table
by that label as text before writing it, so the deposited files are in the
order Scenario:1, Scenario:10, Scenario:100, ... The first version of
`phase0/05_regeneration_check.py` took the scenarios in file order and
therefore compared unrelated scenarios: its "median elementwise relative
deviation 0.33–0.45" under three latent-stream readings, cited in the protocol
up to v0.5 as showing "entirely different draws", is what unrelated draws
give and said nothing about reproduction. An independent review of the Phase 0
scripts found the error. The corrected script aligns scenarios by the integer
in the label, reports the correlation between regenerated and deposited
scenarios (which separates "same latent draws through other weights" from
"other draws"), reproduces the figures of the first run under file order for
the record, and carries a positive control that the first lacked: the
regenerated arrays, written by a transcription of the notebook's saving
routine and read back, must pass the scenario-level test (they come back to
within about 1e-8). It decides each category on its own, since the notebook
saves the three files separately (cell 18 writes only C1234), so a deposit
may combine categories from different executions, and it stops on empty
values or missing decades. A second review of the corrected scripts (11
November 2026) led to these two additions. Before the script was run on the
deposit, it was tested on mock deposits made with randomly initialised
decoders, without the shipped weights or the deposited synthetic files
(`docs/checks/mock_deposit_for_phase0b.py`). The mock decoders carry a gain on
their last layer, since freshly initialised ones are nearly flat and two
independent draws through them differ by only 0.05%. The script reports exact
reproduction of a mock deposit generated with the same seed and weights, which
the first version of the script reported as not reproduced, and also through
weights perturbed by 1e-5 of their value, more than a hundred times the
float32 rounding unit. It separates a deposit drawn with another seed
(correlation near zero, distributions within the Monte Carlo floor) from one
drawn with the same seed through weights perturbed by 5% (correlation high,
distributions beyond the floor), names the reading of each category when the
categories come from different executions, reports a deposit as partly
reproduced when one category was drawn with another seed, and stops on an
empty value.

Re-run of 11 November 2026 (corrected script on the analysis machine:
Python 3.10.21, TensorFlow 2.13.0, tsgm 0.0.7, macOS arm64; report
results/phase0b_regeneration.json). Both controls hold: the positive control
recovers the regenerated arrays to 1.1e-8, and the regeneration is repeatable
within one process. No reading reproduces any category: median elementwise
relative deviations of 0.28 to 0.45, against a tolerance of 1e-4. Under the
documented global seed, however, each regenerated scenario is correlated with
the deposited scenario of the same label: the median over years and features
of the correlation across the 10,000 scenarios is 0.08 in C1234, 0.05 in C56
and 0.13 in C78. The other two readings, and every reading with the labels
shifted by one, give at most 0.01 in absolute value, the sampling error of a
correlation over 10,000 pairs. The deposit is therefore consistent with the
latent draws of the documented seed decoded by weights other than the shipped
ones. This supports the leading explanation above and narrows it: the seed
appears to be the documented one, the checkpoint does not. The difference is
unlikely to be small: in the mock test, weights perturbed by 5% still give a
correlation of 0.96. The distributional figures of the first run are
reproduced (excess over the Monte Carlo floor 4.4 times in the median and 4.7
times in the 95th percentile, pooled; 3.8, 4.8 and 5.0 times in the median for
C1234, C56 and C78), and the scaler-bounds diagnostic again flags no feature.
The reports of the first runs are superseded and no longer archived; the
corrected script reproduces their scenario-level figures under the key
`first_run_file_order`.

## D12 — The model documented in SI S3 is not the model behind the figures. [RESOLVED for X4 2026-10, Phase 0C; documentation discrepancy stands]
SI S3.1–S3.2 document generators trained on 1,160 scenarios with five
features on a 10-step grid (VAE tensors "(680, 10, 5)"; CGAN tensor
"(1160, 10, 5)"). The Methods instead describe generation of the key
variables together with all electricity fuel-level variables, and every
published result corresponds to that extended configuration: Fig. 3 and ED
Fig. 2 match the deposited 16-variable, 9-step generation trained on the
901-set (D9; Phase 0 items 3 and 4; Phase 0B). Consequence: the paper's own
configuration, hence the paper value of factor G1, is the 901-rule, not the
1,160-rule (corrected in protocol v0.2).

The open question (which configuration the GAN baselines of Table 1 used) is
answered by Phase 0C in the paper's favour. Each generative notebook runs its
own label-transfer test: the Top6 notebooks test on 1,160 real scenarios
(680/308/172), the Secondary notebooks on 901 (554/237/110). ED Table 2
reports 554/237/110 for all three generators, so the published VAE, CGAN and
RCGAN all come from the Secondary configuration, and the published comparison
was like-for-like in population and variables. What stands is a documentation
discrepancy: the SI documents the Top6 family, which underlies no published
result. Label-transfer details from the Secondary notebooks, now in the
protocol's X4 rule: random forest (random_state 42) tuned by 3-fold grid search
(Experiment I grid: n_estimators 10/100/200/500/1000, max_depth 6-16 by 2,
min_samples_split 3-6); 1,000 synthetic scenarios per category drawn
separately from the 10,000 of the deposit; inputs are the trapezoid-cumulated
2020-2100 values of 15 variables, Kyoto Gases excluded.

## D13 — The electricity sum-check is not in the code deposit, and its AR6 reference does not reproduce. [ESTABLISHED 2026-10, Phase 0C]
No notebook in either version of the deposit computes the electricity
sum-check behind Fig. 5a, the "1.2% average error in the AR6 Scenarios
Database", or the count of 258 synthetic scenarios below it. Recomputed on
the 901-set from the deposited Real CSVs (`phase0/07_sumcheck_reference.py`,
results/phase0c_sumcheck_reference.json), the AR6 average error is 1.43%
when each scenario's error is averaged over the nine decades, 1.77% on
cumulative 2020-2100 generation and 2.79% on each scenario's worst decade.
None of the six aggregations fixed before the computation rounds to 1.2%, so,
by the rule stated in the script beforehand, X3 keeps the mean over decades
and the paper's stated 1.2% threshold, with the ambiguity recorded. Post hoc
observation, not adopted: the decade mean for 2050 alone is 1.22%, and the
mean over 2020-2080 is 1.16%. The errors are highly skewed. Half of all
scenario-decades have errors below 0.011%, and in C56 more than half of the
scenarios balance exactly in every decade (median of scenario means 2e-15),
so the average the paper uses as benchmark is driven by a minority of
scenarios. The per-decade mean rises from 0.39% (2020) to 2.50% (2100).

## D14 — Unreported variants with 7 to 9 variables. [ESTABLISHED 2026-10, Phase 0C]
The v1.0.0 deposit contains Top7, Top8 and Top9 variants of all three
generators, each with its own label-transfer code ("Top-n" counts Kyoto
Gases, so 6 to 8 key features, against 5 in the reported Top6 set). The variables are added in the order of the
eight-category importance ranking of SI Fig. S3b (Primary Energy, then
Secondary Energy|Gases, then Final Energy|Solids), not of the aggregated
ranking behind Fig. 2a and SI Fig. S3a. The paper mentions only the six-variable
set (Fig. 5b timings) and the extended configuration. None of the Top7-Top9
notebooks carries saved outputs, so their results cannot be recovered from
the deposit. Factor G3 (4 to 9 key features) spans the authors' own
exploration.

## D15 — The 901-set contains no IMAGE or WITCH scenario. [ESTABLISHED 2026-11, Phase 0E]
SI S2.3 merges model versions into frameworks following Dekker et al. (2023),
Nature 624, 309–316 (SI ref. 13), and keeps the first nine rows of SI Table S3
(IMAGE, TIAM-ECN, GCAM, POLES, AIM, MESSAGE, REMIND, WITCH, COFFEE) as the
model feature of its variable ranking. The main text motivates synthetic
generation by biases from "a model's idiosyncratic structures" (ref. 32,
Dekker et al. 2023, Nat. Energy 8, 1395–1404, model fingerprints).
`phase0/09_model_groups.py` (results/phase0e_model_groups.json) maps the 44 AR6
model names of the 1,202 vetted scenarios to these groups and counts them per
population, reading identifiers and, from the World CSV, only whether each of
the ten electricity variables of the D9 rule is reported in each decade. Of the
259 scenarios the D9 rule removes from the 1,160-set, 258 do not report
`Secondary Energy|Electricity|Geothermal` at all: all 142 IMAGE scenarios, all
115 WITCH scenarios and the single MERGE-ETL scenario (one IMAGE scenario also
lacks biomass electricity). The remaining one, a MESSAGE scenario (C1234), does
not report total electricity. No removed scenario has a variable reported with
a gap: the removals are whole variables missing. The requirement of geothermal
electricity, a minor fuel, thus removes two complete frameworks of the paper's
nine from the data the generators learn from, and the 901-set contains seven
of the nine groups plus GEM-E3 (Table S3 row 12, outside the nine, 41
scenarios). IMAGE and WITCH also account for 62 of the 83 C78 scenarios lost
between the 1,202 and the 901-set (IMAGE 36, WITCH 26; then MESSAGE 9, AIM 5,
GCAM 3, C-ROADS and EPPA 3, REMIND 1), three quarters of the loss of the
smallest category across D2 and D9 (193 → 110, 43%). This bears on the paper's positioning of synthetic
generation as mitigating model-determined biases, since the ensemble the
generators reproduce already lacks two frameworks. Consequences for the
protocol: X5 uses the eight groups present in the 901-set (protocol Appendix
A), with folds fixed from identifiers in `data/derived/x5_folds_901.csv`; under G1 levels 1160 and 1202 the training populations include IMAGE and
WITCH, their geothermal electricity filled by G4's imputation (or the
scenarios dropped again under G4's level none), while the references of X5
stay those of the 901-set. Question for the authors: was the exclusion of
IMAGE and WITCH intended?

## D16 — The deposit's Kyoto Gases are an AR6 climate diagnostic, not the native variable. [ESTABLISHED 2026-11, Phase 0F]
The deposited `Real_*.csv` carry anonymous identifiers (`Scenario:1`, ...), no
model and no AR6 scenario name, and the paper does not say which AR6 variable
its "Kyoto Gases" are; the notebooks read a pre-extracted `Kyoto Gases.csv`
that the code deposit does not explain. `phase0/10_deposit_crosswalk.py`
(results/phase0f_deposit_crosswalk.json, real data only) matches the deposit to
AR6 by value. Within each category, `Scenario:k` is the k-th scenario of the D9
reconstruction in ascending order of (Model, Scenario); under this rule all
901 deposited scenarios equal the AR6 World values on all sixteen variables and
nine decades (largest deviation 3.1e-9 of a variable's largest value, the
deposit's rounding). Fifteen variables are the native ones of the D9 rule. The
sixteenth is not `Emissions|Kyoto Gases`, which equals the deposit for none of
the 828 scenarios that report it (deviations up to a quarter of the variable's
largest value), but `AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases
(AR6-GWP100)`, which equals it for all 901; the three other AR6 Kyoto
diagnostics (infilled AR5-GWP100, native-with-infilled under either GWP) match
no scenario. Since every vetted scenario has this diagnostic in every decade
from 2020 to 2100 (it starts in 2015, so it has no 2010 value), Kyoto Gases are
never missing on the grid of the D2 and D9 rules, which is why those rules
found them "exempt". Consequences for
the protocol: (i) the crosswalk `data/derived/crosswalk_901.csv` attaches AR6
identifiers, hence model groups and X5 folds, to the deposited rows; (ii)
training data for every G1 level are built from AR6 with this variable
mapping (`config/paper_values.yaml`, `fixed.evaluation_set_E.ar6_variables`);
(iii) G1's level 828 is defined by native Kyoto reporting and restricts the
population only; (iv) under G4's level "none" the complete cases on E are the
901-set, not the 828-set as release candidates up to v0.5 stated. Question for
the authors: the choice of the infilled AR6-GWP100 diagnostic is nowhere
declared.

## D17 — The real 901-set contains duplicated scenarios. [ESTABLISHED 2026-11, Phases 0E and 0F; DESIGN NOTE]
66 of the 901 scenarios, in 32 groups of two or three, duplicate one another:
their AR6 values on the fifteen native variables of the D9 rule coincide in
every decade 2020–2100 (C1234: 7 groups, 14 scenarios; C56: 17 and 34; C78: 8
and 18). Coinciding means that every value agrees to within 1e-6 of the
variable's largest absolute value. The tolerance only absorbs floating-point
representation: duplicates agree to 1e-9 in the AR6 World CSV (two REMIND
pairs differ in the last bits of a few values) and exactly in the deposited
`Real_*.csv`, while the closest pair of distinct scenarios lies 2.3e-5 apart.
`phase0/09_model_groups.py` finds the groups in the AR6 values and
`phase0/10_deposit_crosswalk.py` finds the same groups in the deposited values.
Every group lies within one model version and one category: POLES 24
scenarios, REMIND 24, COFFEE 6, AIM 4, GEM-E3 4, MESSAGE 4. The infilled Kyoto
Gases coincide as well in 29 groups: identically in 28 (58 scenarios) and to
1.2e-7 of the variable's largest value in one. In the remaining three (COFFEE
1.1) they differ by 0.1 to 0.6%.
They are scenario variants that differ only outside the energy variables used
(for instance a study's pairs with and without the suffix "f", or the EMF30
short-lived-forcer variants). The paper does not mention them. They weigh
twice in training and in the real test population of the label-transfer
benchmark, and under any cross-validation of the real set a scenario can be
predicted by a classifier that has seen its duplicate: dealing the scenarios
singly, as release candidate v0.5 did, splits 29 of the 32 groups across
folds. Consequence for the protocol: the X5 folds
(`data/derived/x5_folds_901.csv`, column `duplicate_group`) treat each group
as one unit, in the outer folds and in the grid search's inner folds. Beyond
the duplicates there is a continuum of near-identical scenarios, which stay
separate units: 40 pairs of distinct scenarios differ by less than 1% of each
variable's largest value on the fifteen variables, 18 of them by less than
0.1%, all within one model group and one category, and the folds separate 35
and 16 of these pairs. This is the stated limitation of X5 (scenarios of the
same model and study in different folds).
