# ==============================================================================
# Sobol' indices, tables and figures from the saved results of the 57,344 runs.
# Loads final_results.rds, computes the Sobol' indices of the 13 claims (Saltelli
# estimator for S_i, Jansen estimator for T_i, 1,000 bootstrap replicates) and
# writes the 13 tables and the two figures.
# ==============================================================================

library(dplyr)
library(sensobol)
library(ggplot2)
library(xtable)

# setwd("<working folder>")  # folder containing gsa_checkpoints_with2C/ and results/

# --- 1. Load saved results ---
final <- readRDS("gsa_checkpoints_with2C/final_results.rds")
results_overnight <- final$results
mat_overnight <- final$mat
params_all <- final$params
N_overnight <- final$N

cat("Loaded:", length(results_overnight), "runs | N =", N_overnight, "\n")
cat("Failed:", sum(sapply(results_overnight, is.null)), "\n\n")

# --- 2. Claim summary ---
claims_matrix_overnight <- do.call(rbind, lapply(results_overnight, function(r) {
  if (is.null(r)) return(rep(NA, 13))
  unlist(r$claims)
}))
colnames(claims_matrix_overnight) <- c("C1a","C1b","C1","C2","C3","C4","C5",
                                       "C1a_2C","C1b_2C","C1_2C","C2_2C","C3_2C","C4_2C")

cat("=== Claim holding fractions ===\n")
print(round(colMeans(claims_matrix_overnight, na.rm = TRUE), 4))

# --- 3. Sobol' indices of the 13 claims (Saltelli for S_i, Jansen for T_i) ---
claim_names <- colnames(claims_matrix_overnight)
Y_list <- setNames(lapply(claim_names, function(cn) as.numeric(claims_matrix_overnight[, cn])),
                   claim_names)

cat("\n=== NA check (should all be 0) ===\n")
print(sapply(Y_list, function(y) sum(is.na(y))))

all_indices <- lapply(Y_list, function(y) {
  sobol_indices(Y = y, N = N_overnight, params = params_all,
                first = "saltelli", total = "jansen", boot = TRUE, R = 1000)
})
names(all_indices) <- claim_names

cat("\n=== sum(Si) and sum(Ti) by claim (sanity check) ===\n")
summary_sums <- do.call(rbind, lapply(claim_names, function(cn) {
  df <- as.data.frame(all_indices[[cn]]$results)
  data.frame(claim = cn,
             sum_Si = round(sum(df$original[df$sensitivity == "Si"]), 4),
             sum_Ti = round(sum(df$original[df$sensitivity == "Ti"]), 4))
}))
print(summary_sums, row.names = FALSE)

# --- 4. Dominant factors table ---
dominant_factors <- do.call(rbind, lapply(claim_names, function(cn) {
  df <- as.data.frame(all_indices[[cn]]$results)
  ti_df <- df[df$sensitivity == "Ti", c("parameters", "original")]
  ti_df <- ti_df[order(-ti_df$original), ]
  data.frame(claim = cn,
             factor_1 = ti_df$parameters[1], Ti_1 = round(ti_df$original[1], 3),
             factor_2 = ti_df$parameters[2], Ti_2 = round(ti_df$original[2], 3))
}))
cat("\n=== Dominant factors (top-2 by Ti) ===\n")
print(dominant_factors, row.names = FALSE)

# ==============================================================================
# 5. PLOTS (saved to results/N4096)
# ==============================================================================

out_dir <- "results/N4096"

plot_df <- do.call(rbind, lapply(names(all_indices), function(claim_name) {
  df <- all_indices[[claim_name]]$results
  df$claim <- claim_name
  df
}))
plot_df$parameters <- factor(plot_df$parameters, levels = params_all)
plot_df$claim <- factor(plot_df$claim, levels = claim_names)

p <- ggplot(plot_df, aes(x = parameters, y = original, fill = sensitivity)) +
  geom_col(position = position_dodge(width = 0.8), width = 0.7) +
  geom_errorbar(aes(ymin = low.ci, ymax = high.ci),
                position = position_dodge(width = 0.8), width = 0.2, linewidth = 0.3) +
  facet_wrap(~claim, ncol = 4, scales = "free_y") +
  scale_fill_manual(values = c("Si" = "#D55E00", "Ti" = "#0072B2"),
                    labels = c("Si" = expression(S[i]), "Ti" = expression(T[i]))) +
  labs(x = "Factor", y = "Sobol' index", fill = "") +
  theme_bw(base_size = 12) +
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1),
        legend.position = "top",
        strip.text = element_text(size = 11, face = "bold"))

ggsave(file.path(out_dir, "sobol_indices_all_claims_with2C.pdf"), p, width = 18, height = 12)
cat("\nSaved:", file.path(out_dir, "sobol_indices_all_claims_with2C.pdf"), "\n")

fractions_df <- data.frame(
  claim = factor(claim_names, levels = claim_names),
  fraction = colMeans(claims_matrix_overnight, na.rm = TRUE),
  target = ifelse(grepl("_2C$", claim_names), "below 2C", "below 1.5C")
)

p2 <- ggplot(fractions_df, aes(x = claim, y = fraction, fill = target)) +
  geom_col(width = 0.6) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "grey40") +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
  scale_fill_manual(values = c("below 1.5C" = "#0072B2", "below 2C" = "#D55E00")) +
  labs(x = "Claim", y = "Fraction of runs where claim holds", fill = "Target") +
  theme_bw(base_size = 14) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

ggsave(file.path(out_dir, "claim_fractions_with2C.pdf"), p2, width = 12, height = 6.5)
cat("Saved:", file.path(out_dir, "claim_fractions_with2C.pdf"), "\n")

# ==============================================================================
# 6. TABLES (.tex), saved to results/N4096
# ==============================================================================

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
  
  out_file <- file.path(out_dir, paste0("sobol_table_", claim_name, ".tex"))
  print(xtable(display_df,
               caption = paste0("Sobol' indices for claim ", claim_name,
                                " ($N=4096$, Saltelli estimator for $S_i$, Jansen for $T_i$, 95\\% bootstrap CI in parentheses)."),
               label = paste0("tab:sobol_", claim_name)),
        include.rownames = FALSE,
        file = out_file,
        caption.placement = "top")
  
  cat("Saved:", out_file, "\n")
}

cat("\n=== REGENERATION COMPLETE ===\n")

