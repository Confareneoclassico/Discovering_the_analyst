#Scenario Discovery analysis - GSA
# Loads data_scenario_wide_v2.rds produced by paper_replicate_analysis.R
# Contains: helper functions, run_pipeline_once() wrapper, Sobol' design, overnight run.
#
# Notes on the implementation:
#   1. C1a, C1b and C4 check the SIGNED coefficient (largest positive), not the absolute
#      value. A large negative coefficient for FinElc, ElcSol or PriBio would mean that the
#      metric works against reaching the target, the opposite of what the claim states, and
#      it must not count as the claim holding.
#   2. run_pipeline_once() takes a run_seed argument tied to the row index i of the main
#      loop and applied to both randomForest() and fit_logit_glmnet(). This makes the full
#      run reproducible run by run, whether or not it is interrupted and resumed.

rm(list = ls())

library(dplyr)
library(tidyverse)
library(randomForest)
library(glmnet)
library(sensobol)

# setwd("<folder containing the input files>")  # set this to the folder with the data (personal path removed for the deposit)

# ==============================================================================
# 0. LOAD REPLICATED DATASET (from paper_replicate_analysis.R)
# ==============================================================================

data_scenario_wide_v2 <- readRDS("data_scenario_wide_v2.rds")
dim(data_scenario_wide_v2)
# expect: ~366 rows, 123 columns

# ==============================================================================
# 1. HELPER FUNCTIONS
# ==============================================================================

# --- Stage 1: correlation-based screening, with F2 tie-break support ---
screen_by_correlation <- function(df, metric_cols, corr_threshold = 0.85,
                                   tie_break = "first") {
  cor_mat <- cor(df[, metric_cols], use = "pairwise.complete.obs")
  to_drop <- character(0)
  for (i in seq_along(metric_cols)) {
    for (j in seq_along(metric_cols)) {
      if (i >= j) next
      mi <- metric_cols[i]; mj <- metric_cols[j]
      if (mi %in% to_drop || mj %in% to_drop) next
      if (abs(cor_mat[mi, mj]) > corr_threshold) {
        if (tie_break == "first") {
          to_drop <- c(to_drop, mj)  # keep mi (first in column order), drop mj
        } else if (tie_break == "max_variance") {
          vi <- var(df[[mi]], na.rm = TRUE); vj <- var(df[[mj]], na.rm = TRUE)
          to_drop <- c(to_drop, if (vi >= vj) mj else mi)
        }
      }
    }
  }
  setdiff(metric_cols, unique(to_drop))
}

# --- Stage 3: Ridge-regularized logistic regression (glmnet, alpha=0) ---
# Very likely a faithful replication of Li et al.'s actual software behavior
# (scikit-learn LogisticRegression regularizes by default), not a deviation
# from their stated method. See July 23 log.
fit_logit_glmnet <- function(df, predictors, target_col, alpha = 0,
                              train_frac = 0.8, n_repeats = 10, seed = 42) {
  set.seed(seed)
  X <- as.matrix(df[, predictors])
  y <- as.numeric(df[[target_col]])
  coefs_list <- list()
  accs <- numeric(n_repeats)

  for (r in seq_len(n_repeats)) {
    train_idx <- sample(seq_len(nrow(df)), size = floor(train_frac * nrow(df)))
    cv_fit <- cv.glmnet(X[train_idx, ], y[train_idx], family = "binomial", alpha = alpha)
    coefs_list[[r]] <- as.numeric(coef(cv_fit, s = "lambda.min"))[-1]  # drop intercept

    pred_prob <- predict(cv_fit, newx = X[-train_idx, ], s = "lambda.min", type = "response")
    accs[r] <- mean((pred_prob > 0.5) == y[-train_idx])
  }

  avg_coefs <- Reduce(`+`, coefs_list) / length(coefs_list)
  names(avg_coefs) <- predictors
  list(avg_coefficients = sort(avg_coefs, decreasing = TRUE), mean_accuracy = mean(accs))
}

# --- Stage 4: manual PRIM (peeling trajectory) ---
# R packages sdtoolkit/prim did not behave as documented (July 22 log, Stage 4).
peel_step <- function(x, y, in_box_idx, alpha = 0.05) {
  n_in_box <- sum(in_box_idx)
  n_remove <- max(1, floor(alpha * n_in_box))
  best <- NULL

  for (col in names(x)) {
    vals <- x[[col]][in_box_idx]
    ord <- order(vals)
    full_idx <- which(in_box_idx)

    for (direction in c("bottom", "top")) {
      to_remove <- if (direction == "bottom") ord[1:n_remove] else ord[(n_in_box - n_remove + 1):n_in_box]
      new_in_box <- in_box_idx
      new_in_box[full_idx[to_remove]] <- FALSE
      new_mean <- mean(y[new_in_box])

      if (is.null(best) || new_mean > best$new_mean) {
        best <- list(col = col, direction = direction, new_in_box = new_in_box, new_mean = new_mean)
      }
    }
  }
  best
}

run_prim_manual <- function(x, y, peel_alpha = 0.05, mass_min = 0.05) {
  n <- nrow(x)
  in_box <- rep(TRUE, n)
  trajectory <- list()
  step <- 0

  repeat {
    mass <- sum(in_box) / n
    precision <- mean(y[in_box])
    recall <- sum(y[in_box]) / sum(y)
    box_limits <- sapply(x[in_box, , drop = FALSE], range)

    trajectory[[length(trajectory) + 1]] <- list(
      step = step, mass = mass, precision = precision, recall = recall, box = box_limits
    )

    if (mass <= mass_min || sum(in_box) <= 2) break

    peel <- peel_step(x, y, in_box, peel_alpha)
    if (is.null(peel)) break
    in_box <- peel$new_in_box
    step <- step + 1
  }

  trajectory
}

# ==============================================================================
# 2. FULL PIPELINE WRAPPER
# ==============================================================================

run_pipeline_once <- function(data_scenario_wide, factors, run_seed = NULL) {
  # factors: named list with F1, F2, F3, F4, F5, F6, F7, F9.1, F9.2, F10, F11, F12
  # run_seed: integer tied to the Sobol' matrix row index, for full reproducibility
  #           of both the Random Forest and the Ridge logistic regression stages.

  metric_cols <- setdiff(names(data_scenario_wide), c("Model", "Scenario", "temp_category"))

  # --- Stage 1: correlation screening (F1, F2) ---
  selected_corr <- screen_by_correlation(data_scenario_wide, metric_cols,
                                          corr_threshold = factors$F1,
                                          tie_break = factors$F2)
  selected_structure_i <- selected_corr[!grepl("AnRate", selected_corr)]

  df_rf <- data_scenario_wide %>%
    select(Model, Scenario, temp_category, all_of(selected_structure_i)) %>%
    mutate(temp_category = factor(temp_category, levels = c("Above2C", "2C", "1.5C"))) %>%
    na.omit()

  if (nrow(df_rf) < 30) return(NULL)  # safety: too few scenarios survived

  # --- Stage 2: Random Forest (F3=ntree, F4=nodesize proxy, F5=max_samples) ---
  if (!is.null(run_seed)) set.seed(run_seed)

  rf_fit <- randomForest(
    temp_category ~ ., data = df_rf %>% select(-Model, -Scenario),
    ntree = factors$F3,
    nodesize = factors$F4,
    mtry = min(8, length(selected_structure_i)),
    sampsize = floor(factors$F5 * nrow(df_rf)),
    importance = TRUE
  )

  imp_type <- if (factors$F6 == "gini") 2 else 1
  imp <- importance(rf_fit, type = imp_type)
  imp_sorted <- sort(imp[, 1] / sum(abs(imp[, 1])), decreasing = TRUE)
  cum_imp <- cumsum(imp_sorted)
  important_metrics <- names(imp_sorted)[cum_imp <= factors$F7]
  if (length(important_metrics) < 2) important_metrics <- names(imp_sorted)[1:2]

  # hard cap: avoids near-separation in the Ridge stage regardless of how flat
  # the importance distribution is for a given factor combination
  max_features <- 30  # matches Fig. 6's ~28-30 bars
  if (length(important_metrics) > max_features) {
    important_metrics <- names(imp_sorted)[1:max_features]
  }

  # --- Stage 3: Ridge classification, BOTH targets (F9.1=train_frac, F9.2=n_repeats) ---
  df_logit <- df_rf %>%
    mutate(
      below2C   = as.numeric(temp_category %in% c("2C", "1.5C")),
      below1_5C = as.numeric(temp_category == "1.5C")
    )
  
  logit_seed <- if (!is.null(run_seed)) run_seed + 1 else 42
  
  logit_2C   <- fit_logit_glmnet(df_logit, important_metrics, "below2C",
                                 train_frac = factors$F9.1, n_repeats = factors$F9.2,
                                 seed = logit_seed)
  logit_1_5C <- fit_logit_glmnet(df_logit, important_metrics, "below1_5C",
                                 train_frac = factors$F9.1, n_repeats = factors$F9.2,
                                 seed = logit_seed)
  
  # --- Stage 4: manual PRIM (below1.5C only, as before) ---
  n_prim_metrics <- min(factors$F10, length(important_metrics))
  prim_metrics <- names(sort(abs(logit_1_5C$avg_coefficients), decreasing = TRUE))[1:n_prim_metrics]
  
  x_prim <- as.data.frame(df_logit[, prim_metrics])
  y_prim <- df_logit$below1_5C
  
  traj <- tryCatch(run_prim_manual(x_prim, y_prim, peel_alpha = 0.05, mass_min = 0.05),
                   error = function(e) NULL)
  
  prim_box_1_5C <- NULL
  if (!is.null(traj)) {
    traj_df <- do.call(rbind, lapply(traj, function(s) {
      data.frame(step = s$step, mass = s$mass, precision = s$precision, recall = s$recall)
    })) %>% mutate(f1 = 2 * precision * recall / (precision + recall))
    
    candidates <- traj_df %>% filter((recall > factors$F11 | precision > factors$F11) & f1 > factors$F12)
    if (nrow(candidates) > 0) {
      chosen_step <- candidates$step[1]  # F14 fixed = "first"
      prim_box_1_5C <- traj[[chosen_step + 1]]
    }
  }
  
  # --- Claims: below-1.5C (unchanged) + below-2C (NEW, computed safely inline) ---
  coefs_1_5C <- logit_1_5C$avg_coefficients
  coefs_2C   <- logit_2C$avg_coefficients
  
  top3_pos_1_5C <- names(sort(coefs_1_5C, decreasing = TRUE))[1:min(3, length(coefs_1_5C))]
  top3_neg_1_5C <- names(sort(coefs_1_5C))[1:min(3, length(coefs_1_5C))]
  C1a <- any(grepl("FinElc", top3_pos_1_5C))
  C1b <- any(grepl("ElcSol|ElcWnd|ElcNuc", top3_pos_1_5C))
  
  top3_pos_2C <- names(sort(coefs_2C, decreasing = TRUE))[1:min(3, length(coefs_2C))]
  top3_neg_2C <- names(sort(coefs_2C))[1:min(3, length(coefs_2C))]
  C1a_2C <- any(grepl("FinElc", top3_pos_2C))
  C1b_2C <- any(grepl("ElcSol|ElcWnd|ElcNuc", top3_pos_2C))
  
  claims <- list(
    # below-1.5C (unchanged from validated version)
    C1a = C1a, C1b = C1b, C1 = C1a && C1b,
    C2 = any(grepl("ElcGas|PriGas", top3_neg_1_5C)),
    C3 = any(grepl("EngInt", top3_neg_1_5C)),
    C4 = {
      lam_coefs <- coefs_1_5C[grepl("_R5LAM$", names(coefs_1_5C))]
      length(lam_coefs) > 0 && grepl("PriBio", names(which.max(lam_coefs)))
    },
    C5 = !is.null(prim_box_1_5C) && prim_box_1_5C$precision > 0.45 && prim_box_1_5C$recall > 0.85,
    
    # below-2C (NEW; C5_2C intentionally omitted - would require duplicating Stage 4)
    C1a_2C = C1a_2C, C1b_2C = C1b_2C, C1_2C = C1a_2C && C1b_2C,
    C2_2C = any(grepl("ElcGas|PriGas", top3_neg_2C)),
    C3_2C = any(grepl("EngInt", top3_neg_2C)),
    C4_2C = {
      lam_coefs_2C <- coefs_2C[grepl("_R5LAM$", names(coefs_2C))]
      length(lam_coefs_2C) > 0 && grepl("PriBio", names(which.max(lam_coefs_2C)))
    }
  )
  
  list(
    claims = claims,
    n_scenarios = nrow(df_rf),
    n_features_selected = length(important_metrics),
    rf_oob_accuracy = 1 - rf_fit$err.rate[nrow(rf_fit$err.rate), "OOB"],
    coefficients_1_5C = coefs_1_5C,
    coefficients_2C = coefs_2C,
    important_metrics = important_metrics
  )
}

# ==============================================================================
# 3. QUICK VALIDATION RUN (single call)
# ==============================================================================

baseline_factors <- list(F1 = 0.85, F2 = "first", F3 = 500, F4 = 10, F5 = 0.9,
                          F6 = "gini", F7 = 0.5, F9.1 = 0.8, F9.2 = 10,
                          F10 = 3, F11 = 0.9, F12 = 0.7)

baseline_run <- run_pipeline_once(data_scenario_wide_v2, baseline_factors, run_seed = 10001)

baseline_run$claims
baseline_run$n_scenarios
baseline_run$rf_oob_accuracy
sort(baseline_run$coefficients_1_5C, decreasing = TRUE)


# --- NEW checks: verify the below-2C additions work correctly ---
sort(baseline_run$coefficients_2C, decreasing = TRUE)  # sanity check the new coefficients exist and look sensible

# Confirm claims now has 13 elements (7 original + 6 new), not 7
length(baseline_run$claims)
names(baseline_run$claims)

# ==============================================================================
# 4. SOBOL' DESIGN: 12 FACTORS
# ==============================================================================

params_all <- c("F1","F2","F3","F4","F5","F6","F7","F9.1","F9.2","F10","F11","F12")

# discrete grids matching the paper's tested values (or agreed proxies)
grid_F3  <- seq(50, 1000, by = 50)
grid_F4  <- c(50, 30, 20, 15, 10, 7, 5, 3, 2, 1)  # inverse-order proxy for their max_depth 1..19
grid_F5  <- c(0.5, 0.6, 0.7, 0.8, 0.9)
grid_F7  <- c(0.5, 0.6, 0.7, 0.8, 0.9)
grid_F91 <- c(0.5, 0.7, 0.8)
grid_F92 <- c(10, 20, 30)
grid_F10 <- c(2, 3, 4, 5)
grid_F11 <- c(0.7, 0.8, 0.9)
grid_F12 <- c(0.6, 0.7, 0.8, 0.9)

pick_from_grid <- function(u, grid) grid[max(1, ceiling(u * length(grid)))]

map_factors_all <- function(row) {
  list(
    F1  = 0.5 + row["F1"] * 0.4,
    F2  = if (row["F2"] < 0.5) "first" else "max_variance",
    F3  = pick_from_grid(row["F3"], grid_F3),
    F4  = pick_from_grid(row["F4"], grid_F4),
    F5  = pick_from_grid(row["F5"], grid_F5),
    F6  = if (row["F6"] < 0.5) "gini" else "permutation",
    F7  = pick_from_grid(row["F7"], grid_F7),
    F9.1 = pick_from_grid(row["F9.1"], grid_F91),
    F9.2 = pick_from_grid(row["F9.2"], grid_F92),
    F10 = pick_from_grid(row["F10"], grid_F10),
    F11 = pick_from_grid(row["F11"], grid_F11),
    F12 = pick_from_grid(row["F12"], grid_F12)
  )
}
# ==============================================================================
# 5. FULL RUN (below-1.5C + below-2C together), checkpointed, reproducible
# ==============================================================================

N_overnight <- 4096
mat_overnight <- sobol_matrices(N = N_overnight, params = params_all)
n_runs_overnight <- nrow(mat_overnight)

cat("=== GSA RUN (below-1.5C + below-2C) ===\n")
cat("Total runs:", n_runs_overnight, "\n")
cat("Estimated time (at ~4s/run):", round(n_runs_overnight * 4 / 3600, 1), "hours\n")
cat("Started at:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n\n")

results_overnight <- vector("list", n_runs_overnight)

checkpoint_dir <- "gsa_checkpoints_with2C"   # NEW folder, separate from the old below-1.5-only run
if (!dir.exists(checkpoint_dir)) dir.create(checkpoint_dir)

start_time <- Sys.time()

for (i in seq_len(n_runs_overnight)) {   # start from i=1, NOT resuming
  factors_i <- map_factors_all(mat_overnight[i, ])
  results_overnight[[i]] <- tryCatch(
    run_pipeline_once(data_scenario_wide_v2, factors_i, run_seed = 10000 + i),
    error = function(e) NULL
  )
  
  if (i %% 50 == 0) {
    saveRDS(list(results = results_overnight[1:i], mat = mat_overnight,
                 last_completed = i, params = params_all, N = N_overnight),
            file = file.path(checkpoint_dir, paste0("checkpoint_", i, ".rds")))
  }
  
  if (i %% 20 == 0) {
    elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
    eta <- Sys.time() + (elapsed / i * (n_runs_overnight - i))
    cat(sprintf("[%s] %d/%d done | ETA: %s\n",
                format(Sys.time(), "%H:%M:%S"), i, n_runs_overnight, format(eta, "%H:%M:%S")))
  }
}

saveRDS(list(results = results_overnight, mat = mat_overnight, params = params_all,
             N = N_overnight),
        file = file.path(checkpoint_dir, "final_results.rds"))

cat("\n=== FINISHED ===\n")
cat("Finished at:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
cat("Total failed:", sum(sapply(results_overnight, is.null)), "/", n_runs_overnight, "\n\n")
# ==============================================================================
# 6. CLAIM SUMMARY (uncertainty analysis - fraction of runs where each claim holds)
# ==============================================================================

claims_matrix_overnight <- do.call(rbind, lapply(results_overnight, function(r) {
  if (is.null(r)) return(rep(NA, 13))   # 13, not 7
  unlist(r$claims)
}))
colnames(claims_matrix_overnight) <- c("C1a","C1b","C1","C2","C3","C4","C5",
                                       "C1a_2C","C1b_2C","C1_2C","C2_2C","C3_2C","C4_2C")

cat("Claim holding fractions:\n")
print(colMeans(claims_matrix_overnight, na.rm = TRUE))

# ==============================================================================
# 7. SOBOL' INDICES (sensitivity analysis - which factor drives instability)
# ==============================================================================

Y_C1a <- as.numeric(claims_matrix_overnight[, "C1a"])
Y_C1b <- as.numeric(claims_matrix_overnight[, "C1b"])
Y_C1  <- as.numeric(claims_matrix_overnight[, "C1"])
Y_C2  <- as.numeric(claims_matrix_overnight[, "C2"])
Y_C3  <- as.numeric(claims_matrix_overnight[, "C3"])
Y_C4  <- as.numeric(claims_matrix_overnight[, "C4"])
Y_C5  <- as.numeric(claims_matrix_overnight[, "C5"])

# NEW: below-2C outcome vectors
Y_C1a_2C <- as.numeric(claims_matrix_overnight[, "C1a_2C"])
Y_C1b_2C <- as.numeric(claims_matrix_overnight[, "C1b_2C"])
Y_C1_2C  <- as.numeric(claims_matrix_overnight[, "C1_2C"])
Y_C2_2C  <- as.numeric(claims_matrix_overnight[, "C2_2C"])
Y_C3_2C  <- as.numeric(claims_matrix_overnight[, "C3_2C"])
Y_C4_2C  <- as.numeric(claims_matrix_overnight[, "C4_2C"])

# sanity check: no NA allowed in Y for sobol_indices
sapply(list(Y_C1a, Y_C1b, Y_C1, Y_C2, Y_C3, Y_C4, Y_C5,
            Y_C1a_2C, Y_C1b_2C, Y_C1_2C, Y_C2_2C, Y_C3_2C, Y_C4_2C),
       function(y) sum(is.na(y)))

ind_C1a <- sobol_indices(Y = Y_C1a, N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C1b <- sobol_indices(Y = Y_C1b, N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C1  <- sobol_indices(Y = Y_C1,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C2  <- sobol_indices(Y = Y_C2,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C3  <- sobol_indices(Y = Y_C3,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C4  <- sobol_indices(Y = Y_C4,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C5  <- sobol_indices(Y = Y_C5,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)

# NEW: below-2C Sobol' indices
ind_C1a_2C <- sobol_indices(Y = Y_C1a_2C, N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C1b_2C <- sobol_indices(Y = Y_C1b_2C, N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C1_2C  <- sobol_indices(Y = Y_C1_2C,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C2_2C  <- sobol_indices(Y = Y_C2_2C,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C3_2C  <- sobol_indices(Y = Y_C3_2C,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)
ind_C4_2C  <- sobol_indices(Y = Y_C4_2C,  N = N_overnight, params = params_all, first = "saltelli", boot = TRUE, R = 1000)

cat("=== C1a (electrification alone) ===\n"); print(ind_C1a$results)
cat("\n=== C1b (renewable generation alone) ===\n"); print(ind_C1b$results)
cat("\n=== C1 (joint electrification+renewables) ===\n"); print(ind_C1$results)
cat("\n=== C2 (gas phase-out) ===\n"); print(ind_C2$results)
cat("\n=== C3 (energy efficiency) ===\n"); print(ind_C3$results)
cat("\n=== C4 (LAM bioenergy) ===\n"); print(ind_C4$results)
cat("\n=== C5 (PRIM box) ===\n"); print(ind_C5$results)

cat("\n\n=== C1a_2C ===\n"); print(ind_C1a_2C$results)
cat("\n=== C1b_2C ===\n"); print(ind_C1b_2C$results)
cat("\n=== C1_2C ===\n"); print(ind_C1_2C$results)
cat("\n=== C2_2C ===\n"); print(ind_C2_2C$results)
cat("\n=== C3_2C ===\n"); print(ind_C3_2C$results)
cat("\n=== C4_2C ===\n"); print(ind_C4_2C$results)

library(ggplot2)
library(xtable)

# --- Build one combined dataframe from all 13 ind_* objects ---
all_indices <- list(
  C1=ind_C1, C1a=ind_C1a, C1b=ind_C1b, C2=ind_C2, C3=ind_C3, C4=ind_C4, C5=ind_C5,
  C1_2C=ind_C1_2C, C1a_2C=ind_C1a_2C, C1b_2C=ind_C1b_2C,
  C2_2C=ind_C2_2C, C3_2C=ind_C3_2C, C4_2C=ind_C4_2C
)

plot_df <- do.call(rbind, lapply(names(all_indices), function(claim_name) {
  df <- all_indices[[claim_name]]$results
  df$claim <- claim_name
  df
}))
plot_df$parameters <- factor(plot_df$parameters, levels = params_all)

# --- One faceted figure, all 13 claims (7 below-1.5C + 6 below-2C), 4 columns to fit better ---
p <- ggplot(plot_df, aes(x = parameters, y = original, fill = sensitivity)) +
  geom_col(position = position_dodge(width = 0.8), width = 0.7) +
  geom_errorbar(aes(ymin = low.ci, ymax = high.ci),
                position = position_dodge(width = 0.8), width = 0.2, linewidth = 0.3) +
  facet_wrap(~claim, ncol = 3, scales = "free_y") +
  scale_fill_manual(values = c("Si" = "#D55E00", "Ti" = "#0072B2"),
                    labels = c("Si" = expression(S[i]), "Ti" = expression(T[i]))) +
  labs(x = "Factor", y = "Sobol' index", fill = "") +
  theme_bw(base_size = 10) +
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1),
        legend.position = "top")

ggsave("sobol_indices_all_claims_with2C.pdf", p, width = 13, height = 14)

# --- Claim-holding-fraction bar chart: all 13 claims, grouped visually by target ---
fractions_df <- data.frame(
  claim = factor(colnames(claims_matrix_overnight), levels = colnames(claims_matrix_overnight)),
  fraction = colMeans(claims_matrix_overnight, na.rm = TRUE),
  target = ifelse(grepl("_2C$", colnames(claims_matrix_overnight)), "below 2C", "below 1.5C")
)

p2 <- ggplot(fractions_df, aes(x = claim, y = fraction, fill = target)) +
  geom_col(width = 0.6) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "grey40") +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
  scale_fill_manual(values = c("below 1.5C" = "#0072B2", "below 2C" = "#D55E00")) +
  labs(x = "Claim", y = "Fraction of runs where claim holds", fill = "Target") +
  theme_bw(base_size = 12) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

ggsave("claim_fractions_with2C.pdf", p2, width = 9, height = 5)

# --- One table per claim (unchanged logic, now runs over all 13) ---
for (claim_name in names(all_indices)) {
  df <- as.data.frame(all_indices[[claim_name]]$results)
  
  si_df <- df[df$sensitivity == "Si", c("parameters", "original", "low.ci", "high.ci")]
  ti_df <- df[df$sensitivity == "Ti", c("parameters", "original", "low.ci", "high.ci")]
  
  names(si_df) <- c("Factor", "Si", "Si_low", "Si_high")
  names(ti_df) <- c("Factor", "Ti", "Ti_low", "Ti_high")
  
  merged <- merge(si_df, ti_df, by = "Factor")
  merged <- merged[match(params_all, merged$Factor), ]
  merged <- as.data.frame(merged)
  
  num_cols <- c("Si", "Si_low", "Si_high", "Ti", "Ti_low", "Ti_high")
  merged[num_cols] <- lapply(merged[num_cols], round, digits = 3)
  
  display_df <- data.frame(
    Factor = merged$Factor,
    Si = sprintf("%.3f (%.3f, %.3f)", merged$Si, merged$Si_low, merged$Si_high),
    Ti = sprintf("%.3f (%.3f, %.3f)", merged$Ti, merged$Ti_low, merged$Ti_high)
  )
  
  out_file <- paste0("sobol_table_", claim_name, ".tex")
  print(xtable(display_df,
               caption = paste0("Sobol' indices for claim ", claim_name,
                                " ($N=4096$, Saltelli estimator for $S_i$, Jansen for $T_i$, 95\\% bootstrap CI in parentheses)."),
               label = paste0("tab:sobol_", claim_name)),
        include.rownames = FALSE,
        file = out_file,
        caption.placement = "top")
  
  cat("Saved:", out_file, "\n")
}

