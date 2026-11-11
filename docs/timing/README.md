# Timing benchmark of 5 November 2026 (protocol section 6, item "Timing")

These scripts sized the compute budget. They fit the three generator architectures of
the Deep-IAM "Secondary" notebooks and run the grid search of G8's paper level on random
arrays shaped like the study's data. No AR6, Deep-IAM or synthetic data is read and no
claim rule is evaluated, so they are not runs in the protocol's sense.

Environment: Python 3.11, tensorflow-cpu 2.13.0 (TensorFlow 2.13.1), keras 2.13.1,
tsgm 0.0.7, tensorflow-probability 0.21.0, scikit-learn 1.3.2, numpy 1.24.3,
scipy 1.10.1. Hardware: one core of an Intel Xeon at 2.1 GHz (2 vCPU, 7 GB RAM).

| Script | What it times | Result on 5 November 2026 |
|---|---|---|
| `bench_generators.py THREADS NFT` | seconds per optimisation step of the VAE (tsgm `vae_conv5`, one per category, paper batch sizes), the CGAN (`cgan_base_c4_l1`, batch 100) and the RCGAN (`cGAN_LSTMnArchitecture`, batch 100) | one thread, NFT = 16: VAE about 0.59 s per epoch over the three categories (0.49 h for 3,000 epochs), CGAN 0.65 s per step (2.73 h for 1,500 epochs), RCGAN 0.063 s per step (0.31 h for 1,800 epochs); two threads bring the CGAN only to 0.47 s per step |
| `bench_rf_and_sizes.py` | seconds per tree of the random forest at the depths of G8's paper-level grid (2,000 x 15, three classes), and parameter counts | one grid search (360 fits and a refit) about 10 minutes |
| `bench_memory.py` | peak memory of a training process with batched generation of 30,000 scenarios | about 1.5 GB; generating 30,000 CGAN scenarios in one call, as the notebooks do, exceeded 7 GB |

Totals derived in protocol section 6: about 3.5 core-hours per training at paper values,
about 3.4 averaged over the design (epochs multiplier, population sizes), about 2,350
core-hours for the full design (512 trainings, 20 noise-floor replicates, the X4 grid
searches in a quarter of the 4,096 evaluations) and about 1,220 if the stopping rule ends
it at 256 trainings.
