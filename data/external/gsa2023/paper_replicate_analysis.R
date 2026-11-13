# Scenario Discovery analysis - PAPER REPLICATION
# This file ONLY replicates Li et al. (2023)'s data preparation pipeline.
# Output: data_scenario_wide_v2, saved to disk for use by gsa_1.R
rm(list=ls())

# Load packages
library(readxl)
library(dplyr)
library(tidyverse)

# Working directory
# setwd("<working folder>")  # folder containing the input files

# ==============================================================================
# 1. LOAD DATA
# ==============================================================================

# File 1: Regional data
path_data <- "iamc15_scenario_data_all_regions_r2.0.xlsx"
excel_sheets(path_data)  #sheet= data

data_raw <- read_excel(path_data, sheet = "data")
dim(data_raw)
names(data_raw)

# File 2: Metadata
path_meta <- "sr15_metadata_indicators_r2.0.xlsx"
excel_sheets(path_meta) #sheet=meta

meta_raw <- read_excel(path_meta, sheet = "meta")
dim(meta_raw)
names(meta_raw)

# Unique values of column category
unique(meta_raw$category)
#[1] "1.5C low overshoot"    "Higher 2C"             "Lower 2C"              "Above 2C"
#[5] "1.5C high overshoot"   "Below 1.5C"            "no-climate-assessment" "reference"

# ==============================================================================
# 2. METADATA: filtering and temperature category reclassification
# ==============================================================================

meta_clean <- meta_raw %>%
  filter(exclude == FALSE) %>%                          # remove excluded/non-vetted scenarios (exclude flag)
  filter(!category %in% c("no-climate-assessment", "reference")) %>%  # remove scenarios with no climate assessment or reference scenarios (not relevant to Li et al.)
  mutate(
    temp_category = case_when(
      # grouping into 3 macro-categories as per Li et al. 2023, Sec. 3.2.1
      category %in% c("Below 1.5C", "1.5C low overshoot", "1.5C high overshoot") ~ "1.5C",
      category %in% c("Lower 2C", "Higher 2C") ~ "2C",
      category == "Above 2C" ~ "Above2C",
      TRUE ~ NA_character_
    )
  ) %>%
  select(model, scenario, temp_category)                # keep only join keys + target category

# check: scenario distribution by category: expected total 411 (number stated in the paper before regional data filtering)
table(meta_clean$temp_category, useNA = "always")
# result: 1.5C=90, 2C=132, Above2C=189, NA=0 -> total 411, matches the paper: OK.

# Exploring the structure of regional data (data_raw)
unique(data_raw$Region)
# result: the 5 R5 regions (ASIA, LAM, MAF, OECD90+EU, REF) + World + R5ROWO (to discard, not used by Li et al.)

length(unique(data_raw$Variable))
# result: 598 total variables in the IAMC file - to be filtered down to the metrics needed for Table 2/Appendix C

# ==============================================================================
# 3. METRIC MAPPING (IAMC Variable -> Li et al. short-code)
# ==============================================================================

# --- Full metric_map: structure/ratio metrics needed as raw IAMC variables ---
# (growth-rate metrics are DERIVED from these same shares, not separate IAMC variables)
# NOTE: 20 entries total (17 short-code metrics + PriTotal/FinTotal/ElcTotal/GDP as
# auxiliary denominators, not final features themselves)
metric_map <- c(
  "Primary Energy"                                = "PriTotal",
  "Primary Energy|Biomass"                        = "PriBio",
  "Primary Energy|Coal|w/ CCS"                    = "PriCoalCCS",
  "Primary Energy|Gas|w/o CCS"                    = "PriGas",
  "Primary Energy|Gas|w/ CCS"                     = "PriGasCCS",
  "Primary Energy|Nuclear"                        = "PriNuc",
  "Primary Energy|Oil"                            = "PriOil",
  "Final Energy"                                  = "FinTotal",
  "Final Energy|Electricity"                      = "FinElc",
  "Final Energy|Gases"                             = "FinGas",
  "Secondary Energy|Electricity"                  = "ElcTotal",
  "Secondary Energy|Electricity|Biomass|w/o CCS"  = "ElcBio",
  "Secondary Energy|Electricity|Biomass|w/ CCS"   = "ElcBioCCS",
  "Secondary Energy|Electricity|Coal|w/ CCS"      = "ElcCoalCCS",
  "Secondary Energy|Electricity|Gas|w/o CCS"      = "ElcGas",
  "Secondary Energy|Electricity|Gas|w/ CCS"       = "ElcGasCCS",
  "Secondary Energy|Electricity|Nuclear"          = "ElcNuc",
  "Secondary Energy|Electricity|Solar"            = "ElcSol",
  "Secondary Energy|Electricity|Wind"             = "ElcWnd",
  "GDP|PPP"                                       = "GDP"
)
# NOTE: ElcGasCF is excluded (28.9% missing values)

# verify all exist
sapply(names(metric_map), function(v) v %in% unique(data_raw$Variable))

# ==============================================================================
# 4. FILTER + PIVOT
# ==============================================================================

# --- Filter to needed variables and R5 regions, rename to short-code ---
data_filtered <- data_raw %>%
  filter(Variable %in% names(metric_map),
         Region %in% c("R5ASIA", "R5LAM", "R5MAF", "R5OECD90+EU", "R5REF")) %>%
  select(Model, Scenario, Region, Variable, `2010`, `2050`) %>%
  mutate(Variable = recode(Variable, !!!metric_map))

length(unique(data_filtered$Variable))  # should be 20 (matches length(metric_map))

# --- Pivot to wide: one row per Model+Scenario+Region+year ---
data_wide <- data_filtered %>%
  pivot_longer(cols = c(`2010`, `2050`), names_to = "year", values_to = "value") %>%
  pivot_wider(names_from = Variable, values_from = value)

dim(data_wide)
names(data_wide)

# ==============================================================================
# 5. COMPUTE SHARE METRICS (2050) AND GROWTH RATES
# ==============================================================================

# --- Compute share metrics for 2050 ---
data_shares <- data_wide %>%
  mutate(
    PriBio_share      = PriBio / PriTotal,
    PriCoalCCS_share  = PriCoalCCS / PriTotal,
    PriGas_share      = PriGas / PriTotal,
    PriGasCCS_share   = PriGasCCS / PriTotal,
    PriNuc_share      = PriNuc / PriTotal,
    PriOil_share      = PriOil / PriTotal,
    FinElc_share      = FinElc / FinTotal,
    FinGas_share      = FinGas / FinTotal,
    ElcBio_share      = ElcBio / ElcTotal,
    ElcBioCCS_share   = ElcBioCCS / ElcTotal,
    ElcCoalCCS_share  = ElcCoalCCS / ElcTotal,
    ElcGas_share      = ElcGas / ElcTotal,
    ElcGasCCS_share   = ElcGasCCS / ElcTotal,
    ElcNuc_share      = ElcNuc / ElcTotal,
    ElcSol_share      = ElcSol / ElcTotal,
    ElcWnd_share      = ElcWnd / ElcTotal
  )

# sanity check
summary(select(data_shares, ends_with("_share")))

# --- Compute the 7 annual growth-rate metrics ---
# Formula (Appendix C): compound annual growth rate of the share, 2010 -> 2050 (40 years)
# CAGR = (share_2050 / share_2010)^(1/40) - 1
# Where share_2010 == 0 the growth rate is set to NA, since a 0/0 or x/0 growth rate is
# not defined. Without this guard, Inf values turn the correlation matrix used in
# screen_by_correlation into NaN, which breaks the tie-break logic or throws
# "missing value where TRUE/FALSE needed".
compute_growth_rate <- function(df, share_var, year_var = "year") {
  df %>%
    select(Model, Scenario, Region, all_of(year_var), all_of(share_var)) %>%
    pivot_wider(names_from = all_of(year_var), values_from = all_of(share_var), names_prefix = "val_") %>%
    mutate(growth_rate = ifelse(val_2010 > 0, (val_2050 / val_2010)^(1/40) - 1, NA_real_)) %>%
    select(Model, Scenario, Region, growth_rate)
}

# Shares for both years (2010 and 2050), needed for the growth rates
data_shares_allyears <- data_wide %>%
  mutate(
    PriBio_share = PriBio / PriTotal,
    PriGas_share = PriGas / PriTotal,
    FinElc_share = FinElc / FinTotal,
    ElcGas_share = ElcGas / ElcTotal,
    ElcNuc_share = ElcNuc / ElcTotal,
    ElcSol_share = ElcSol / ElcTotal,
    ElcWnd_share = ElcWnd / ElcTotal
  )

growth_rates <- list(
  PriBioAnRate = compute_growth_rate(data_shares_allyears, "PriBio_share") %>% rename(PriBioAnRate = growth_rate),
  PriGasAnRate = compute_growth_rate(data_shares_allyears, "PriGas_share") %>% rename(PriGasAnRate = growth_rate),
  FinElcAnRate = compute_growth_rate(data_shares_allyears, "FinElc_share") %>% rename(FinElcAnRate = growth_rate),
  ElcGasAnRate = compute_growth_rate(data_shares_allyears, "ElcGas_share") %>% rename(ElcGasAnRate = growth_rate),
  ElcNucAnRate = compute_growth_rate(data_shares_allyears, "ElcNuc_share") %>% rename(ElcNucAnRate = growth_rate),
  ElcSolAnRate = compute_growth_rate(data_shares_allyears, "ElcSol_share") %>% rename(ElcSolAnRate = growth_rate),
  ElcWndAnRate = compute_growth_rate(data_shares_allyears, "ElcWnd_share") %>% rename(ElcWndAnRate = growth_rate)
)

# merge all 7 growth-rate tables into one
growth_rates_combined <- reduce(growth_rates, left_join, by = c("Model", "Scenario", "Region"))

dim(growth_rates_combined)
summary(select(growth_rates_combined, ends_with("AnRate")))
# no Inf values; NA where share_2010 == 0

# ==============================================================================
# 6. ASSEMBLE FINAL DATASET (structure/ratio 2050 + EngInt.Ratio + growth-rates)
# ==============================================================================

data_2050 <- data_shares %>%
  filter(year == "2050") %>%
  select(Model, Scenario, Region, ends_with("_share"))

dim(data_2050)
names(data_2050)

# --- EngInt.Ratio: energy intensity 2050/2010 ratio ---
eng_int <- data_wide %>%
  mutate(energy_intensity = FinTotal / GDP) %>%
  select(Model, Scenario, Region, year, energy_intensity) %>%
  pivot_wider(names_from = year, values_from = energy_intensity, names_prefix = "EngInt_") %>%
  mutate(EngInt.Ratio = EngInt_2050 / EngInt_2010) %>%
  select(Model, Scenario, Region, EngInt.Ratio)

data_2050 <- data_2050 %>%
  left_join(eng_int, by = c("Model", "Scenario", "Region"))

dim(data_2050)
names(data_2050)

# --- Full 7-metric growth-rate set (ElcSol and ElcWnd included, given the 80% completeness threshold) ---
growth_rates_full7 <- growth_rates_combined

data_full_7gr <- data_2050 %>%
  left_join(growth_rates_full7, by = c("Model", "Scenario", "Region")) %>%
  left_join(meta_clean, by = c("Model" = "model", "Scenario" = "scenario")) %>%
  filter(!is.na(temp_category))

dim(data_full_7gr)

all_metric_cols_7gr <- data_full_7gr %>%
  select(-Model, -Scenario, -Region, -temp_category) %>%
  names()

length(all_metric_cols_7gr)  # should be 24 (17 structure/ratio + 7 growth-rate)

# --- Completeness check: 80% threshold (not 100%) ---
completeness_7gr <- data_full_7gr %>%
  group_by(Model, Scenario) %>%
  summarise(pct_complete = mean(!is.na(across(all_of(all_metric_cols_7gr)))), .groups = "drop")

sapply(c(0.7, 0.75, 0.8, 0.85, 0.9, 1.0), function(th) {
  sum(completeness_7gr$pct_complete >= th)
})

# --- FINAL dataset: 24 metrics, 80% completeness threshold ---
complete_scenarios_80 <- completeness_7gr %>%
  filter(pct_complete >= 0.8) %>%
  select(Model, Scenario)

data_final <- data_full_7gr %>%
  semi_join(complete_scenarios_80, by = c("Model", "Scenario"))

dim(data_final)
table(data_final$Region)
table(data_final$temp_category)

# --- Pivot to one row per scenario, one column per metric-region combination ---
metric_cols_final_v2 <- data_final %>%
  select(-Model, -Scenario, -Region, -temp_category) %>%
  names()

data_scenario_wide_v2 <- data_final %>%
  pivot_longer(cols = all_of(metric_cols_final_v2), names_to = "metric", values_to = "value") %>%
  mutate(colname = paste0(metric, "_", Region)) %>%
  select(Model, Scenario, temp_category, colname, value) %>%
  distinct(Model, Scenario, temp_category, colname, .keep_all = TRUE) %>%
  pivot_wider(names_from = colname, values_from = value)

# sanitize column names (the "+" in R5OECD90+EU breaks formula parsing)
colnames(data_scenario_wide_v2) <- make.names(colnames(data_scenario_wide_v2))

dim(data_scenario_wide_v2)
# expect: ~366 rows, 3 + 24*5 = 123 columns

# ==============================================================================
# 7. SAVE FINAL DATASET FOR USE IN gsa_1.R
# ==============================================================================

saveRDS(data_scenario_wide_v2, "data_scenario_wide_v2.rds")
cat("Saved data_scenario_wide_v2.rds -", nrow(data_scenario_wide_v2), "scenarios,",
    ncol(data_scenario_wide_v2), "columns\n")
cat("Load it in gsa_1.R with: data_scenario_wide_v2 <- readRDS(\"data_scenario_wide_v2.rds\")\n")
