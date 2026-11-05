# 2023 GSA of the Li et al. (2023) scenario-discovery pipeline (Jansen design)

Prior analysis by G. Vannucci of the pipeline of Li P.-H., Pye S., Keppo I., et al. (2023),
"Revealing effective regional decarbonisation measures to limit global temperature increase in
uncertain transition scenarios with machine learning techniques", Climatic Change 176(7):80.
It is deposited here as an external reference for the audit of Li et al. (2025): the audit
re-uses the rows of the A and B base matrices (see "Use in the audit").

## Files

| File | Content |
|---|---|
| `gsa_1.R` | Full R script: helper functions, `run_pipeline_once()`, Sobol' design, run loop, claim summary, Sobol' indices |
| `final_results.rds` | Output of the 57,344 runs (list with `results`, `mat`, `params`, `N`) |
| `paper_replicate_analysis.R` | Data preparation: replicates the data preparation of Li et al. (2023) and writes `data_scenario_wide_v2.rds` |
| (not included) `data_scenario_wide_v2.rds` | Input data of the pipeline (366 scenarios x 123 columns); rebuilt from the public database with `paper_replicate_analysis.R` (see "Input data") |
| `jansen_indices_2023.csv` | Sobol' indices of the 2023 analysis (S_i and T_i with 95% intervals) |
| `outputs/` | Tables (`sobol_table_*.tex`) and figures (`*.pdf`) produced by `gsa_1.R` |
| `sha256.txt` | SHA-256 of every file in this folder except this README and `sha256.txt` |

Order of use: `paper_replicate_analysis.R` (builds the input data), then `gsa_1.R` (runs the design).

SHA-256 of each file: see `sha256.txt`. The two scripts differ from the versions used to produce
the results in four respects only, none of which affects the results: the personal `setwd()` path
is replaced by a comment (set the working directory before running); `first = "jansen"` is
`first = "saltelli"` in the calls to `sobol_indices()` (this reproduces the tabulated indices, see
below); the caption of the tables written by `gsa_1.R` now reads "Saltelli estimator for S_i,
Jansen for T_i"; and the header comment of `gsa_1.R` is reworded. The results file is unchanged.

## Design (sampler, seed, rows)

- Package: `sensobol` (R). Call: `sobol_matrices(N = 4096, params = params_all)`, with 12 factors.
- Sampler: Sobol' quasi-random sequence (the package default). Points are in the unit hypercube
  [0,1]^12 and are stored in `final_results.rds$mat`, so the design does not need to be regenerated.
- Size: N = 4,096, k = 12, N(k+2) = 57,344 runs, stored in 14 consecutive blocks of 4,096 rows:
  - rows 1 to 4,096: base matrix A;
  - rows 4,097 to 8,192: base matrix B;
  - rows 8,193 to 57,344: the 12 matrices AB_i, one per factor in the order of `params`
    (in each, column i of A is replaced by column i of B).
- Seed: run i (row i of `mat`) uses `set.seed(10000 + i)` for the Random Forest and
  `10000 + i + 1` for the ridge stage. The random forest and the ridge regressions are therefore
  reproducible run by run, independently of interruptions.
- Failed runs: none (all 57,344 results are present and non-null).

## Factors and mapping of the unit cube to values

Column names of `mat` and entries of `params`: `F1, F2, F3, F4, F5, F6, F7, F9.1, F9.2, F10, F11, F12`.
Factors F8, F13 and F14 of the full list are held fixed. The factor values are obtained from the
unit-cube coordinate u by `map_factors_all()` in `gsa_1.R`:

| Factor | Meaning | Paper's value | Values in the design | Mapping from u |
|---|---|---|---|---|
| F1 | Correlation threshold of the pre-screening | 0.85 | continuous, 0.5 to 0.9 | 0.5 + 0.4 u |
| F2 | Tie-break rule inside a group of highly correlated metrics | unspecified | `first` / `max_variance` | u < 0.5: `first` |
| F3 | Random Forest `ntree` | grid 50 to 1000 | 50, 100, ..., 1000 (20 levels) | equal-width bins of u |
| F4 | Random Forest `nodesize` (inverse-order proxy of `max_depth`) | `max_depth` selected from 1 to 19 | 50, 30, 20, 15, 10, 7, 5, 3, 2, 1 (10 levels) | equal-width bins of u |
| F5 | Random Forest `sampsize` as a fraction of the scenarios | grid 0.5 to 0.9 | 0.5, 0.6, 0.7, 0.8, 0.9 | equal-width bins of u |
| F6 | Importance metric | Gini | `gini` / `permutation` | u < 0.5: `gini` |
| F7 | Cumulative importance threshold for retaining metrics | 0.8 | 0.5, 0.6, 0.7, 0.8, 0.9 | equal-width bins of u |
| F9.1 | Train fraction of the ridge classification | 0.8 | 0.5, 0.7, 0.8 | equal-width bins of u |
| F9.2 | Number of repeats of the random train/test split | 10 | 10, 20, 30 | equal-width bins of u |
| F10 | Number of metrics per PRIM box | 3 | 2, 3, 4, 5 | equal-width bins of u |
| F11 | PRIM recall/precision threshold | 0.9 | 0.7, 0.8, 0.9 | equal-width bins of u |
| F12 | PRIM F1 threshold | 0.7 | 0.6, 0.7, 0.8, 0.9 | equal-width bins of u |

"Equal-width bins of u" means `grid[max(1, ceiling(u * length(grid)))]`. The ranges stated in the
draft paper (Table 1) are wider for F9.1 (0.5 to 0.85) and F11/F12 than the grids actually used in
the script; the table above reports what the script does.

## Results file (`final_results.rds`)

An R list with:

- `results`: list of 57,344 entries, in the row order of `mat`; each entry is a list with
  - `claims`: named list of 13 logical values (see below);
  - `n_scenarios`: number of scenarios kept after screening and `na.omit`;
  - `n_features_selected`: number of metrics retained by the cumulative-importance rule (at most 30);
  - `rf_oob_accuracy`: out-of-bag accuracy of the Random Forest (3-class temperature category);
  - `coefficients_1_5C`, `coefficients_2C`: average ridge coefficients, named by metric, for the
    below-1.5C and below-2C targets;
  - `important_metrics`: names of the retained metrics;
- `mat`: 57,344 x 12 matrix of unit-cube design points, columns as `params`;
- `params`: the 12 factor names;
- `N`: 4096.

Metric names have the form `<variable>[_<region>]`, with regions R5ASIA, R5LAM, R5MAF, R5OECD90.EU, R5REF.

## Claims

All claims are computed from the signed ridge coefficients of the below-1.5C target (no suffix) or
of the below-2C target (suffix `_2C`). "Top 3" refers to the three largest positive (or most
negative) coefficients.

| Claim | Quoted claim of Li et al. (2023) | Operational rule |
|---|---|---|
| C1a | electrification (FinElc) most influential in limiting temperature increase | FinElc (any region) is among the top 3 positive coefficients |
| C1b | solar power generation (ElcSol) most influential | at least one of ElcSol, ElcWnd, ElcNuc is among the top 3 positive coefficients |
| C1 | solar power and sectoral electrification most effective measures | C1a and C1b hold jointly in the same run |
| C2 | unabated gas usage has high negative coefficients; decommission unabated gas | ElcGas or PriGas (any region) is among the top 3 negative coefficients |
| C3 | energy intensity (EngInt.Ratio) more influential than most supply-side measures | EngInt.Ratio is among the top 3 negative coefficients |
| C4 | bioenergy supply in LAM is particularly influential | among LAM metrics, PriBio has the largest positive coefficient |
| C5 | PRIM box for 1.5C (ElcGas < 5.2%, EngInt.Ratio < 56%, FinElc > 36%) | the box selected along the peeling trajectory has precision > 0.45 and recall > 0.85 |
| C1a_2C, C1b_2C, C1_2C, C2_2C, C3_2C, C4_2C | same as above | same rules on the below-2C coefficients (C5_2C not computed) |

Fractions of runs in which each claim holds (all 57,344 runs): C1a 67.7%, C1b 25.0%, C1 7.8%,
C2 25.4%, C3 65.2%, C4 40.3%, C5 15.0%, C1a_2C 62.9%, C1b_2C 12.7%, C1_2C 4.3%, C2_2C 42.6%,
C3_2C 83.0%, C4_2C 74.7%.

## Input data (`data_scenario_wide_v2.rds`)

- Data frame with 366 scenarios (rows) and 123 columns: `Model`, `Scenario`, `temp_category`
  (1.5C: 79, 2C: 127, Above2C: 160) and 120 metrics.
- Metrics: 24 variables (primary-energy and final-energy shares, electricity shares, annual growth
  rates, energy-intensity ratio) for each of the 5 R5 regions.
- Models: 18 model versions (largest: REMIND-MAgPIE 1.7-3.0 with 51 scenarios, AIM/CGE 2.0 with 47,
  IMAGE 3.0.1 with 45).
- Source: the IAMC 1.5C Scenario Explorer and Data hosted by IIASA (IPCC SR1.5 scenario data,
  release 2.0), files `iamc15_scenario_data_all_regions_r2.0.xlsx` (sheet `data`) and
  `sr15_metadata_indicators_r2.0.xlsx` (sheet `meta`). Reference: Huppmann D., Kriegler E.,
  Krey V., Riahi K., Rogelj J., Calvin K., et al. (2019), IAMC 1.5C Scenario Explorer and Data
  hosted by IIASA, release 2.0, DOI 10.5281/zenodo.3363345 (SR15 version:
  DOI 10.22022/SR15/08-2018.15429); see also Huppmann D., Rogelj J., Kriegler E., Krey V., Riahi K.
  (2018), "A new scenario resource for integrated 1.5 C research", Nature Climate Change 8,
  1027-1030, DOI 10.1038/s41558-018-0317-4. The database terms restrict the redistribution of
  substantial parts of the data, so neither the original files nor the derived input
  `data_scenario_wide_v2.rds` are deposited here. To rebuild it, download the two files from
  the Scenario Explorer, set the working directory and run `paper_replicate_analysis.R`.
  The files were downloaded on 21 July 2026.
- Construction (`paper_replicate_analysis.R`):
  1. Metadata: scenarios with `exclude == FALSE` and a climate assessment (categories
     `no-climate-assessment` and `reference` dropped) give 411 scenarios, as stated by Li et al.
     (2023): 1.5C 90, 2C 132, Above2C 189. Temperature category: `Below 1.5C`, `1.5C low overshoot`
     and `1.5C high overshoot` form `1.5C`; `Lower 2C` and `Higher 2C` form `2C`; `Above 2C`
     forms `Above2C`.
  2. Variables: 20 IAMC variables (primary energy, final energy, electricity generation by
     source, GDP|PPP) for the five R5 regions (ASIA, LAM, MAF, OECD90+EU, REF), years 2010 and 2050.
  3. Metrics (24 per region): 16 shares of 2050 values (for example `PriBio_share` =
     primary energy from biomass over total primary energy), `EngInt.Ratio` (final energy over GDP,
     2050 over 2010) and 7 annual growth rates of shares between 2010 and 2050,
     CAGR = (share_2050 / share_2010)^(1/40) - 1, set to missing when share_2010 = 0.
  4. Completeness filter: a scenario is kept if at least 80% of its region-by-metric values are
     non-missing. This step takes the 411 scenarios to the 366 of the file (1.5C 79, 2C 127,
     Above2C 160).
  5. One row per scenario, one column per metric and region (`<metric>_<region>`, with `+` in
     `R5OECD90+EU` replaced by `.`).

## Mapping to the coordinates of the audit

The 2023 factors belong to the pipeline of Li P.-H. et al. (2023) (random forest, ridge, PRIM); the
audit concerns the pipeline of Li P. et al. (2025) (scenario generation). The two pipelines differ,
so the correspondence is weak. Proposed mapping, one row per 2023 factor, against the
coordinates of Table 1 of the protocol:

| 2023 factor | Closest coordinate of the audit | Correspondence |
|---|---|---|
| F7 cumulative importance threshold | G3, number of key features | partial: both set how many ranked variables are retained |
| F1 correlation threshold | G3, pool completeness threshold | weak: both define the candidate pool, with different criteria (redundancy versus missing data) |
| F6 importance metric | none | G3 does not vary the importance metric |
| F3 ntree, F4 nodesize, F5 sampsize | none | the random forest of 2023 ranks the variables; G8 varies the transfer classifier, a different model with a different role (only the learner type is shared) |
| F2, F9.1, F9.2, F10, F11, F12 | none | no counterpart |

## Use in the audit

Only the rows of A and B (the first 8,192 rows of `mat` and `results`), pooled, are used, with
the 13 claim indicators as outputs and the binned given-data estimator of the protocol (section 7).
Dummy columns are generated after the fact, with the seed and call stated in the protocol. The
original Jansen-based indices (N = 4,096, 57,344 runs) are reported in the draft paper
(Tables 4 to 16; first-order and total-order, 95% bootstrap intervals, R = 1,000).

Estimators of the saved indices: S_i with the Saltelli estimator and T_i with the Jansen estimator
(as in the captions of the tables and in the draft paper). This was checked by recomputing the
point estimates of F1 from `final_results.rds` for claims C1a, C1_2C, C5, C4 and C2: the Saltelli
estimator reproduces the tabulated S_i in all five cases, whereas the Jansen first-order estimator
does not (for example C1_2C: 0.037 tabulated, 0.037 Saltelli, -0.092 Jansen). An earlier
version of `gsa_1.R` called `sobol_indices(..., first = "jansen", ...)`; the version in this folder
uses `first = "saltelli"`, which reproduces the tables.

The indices of all 13 claims and 12 factors are in `jansen_indices_2023.csv` (columns: claim,
factor, Si, Si_lo, Si_hi, Ti, Ti_lo, Ti_hi; 95% bootstrap intervals, R = 1,000).
