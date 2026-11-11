"""Seconds per tree of scikit-learn 1.3.2 random forests at the depths of G8's paper-level grid,
on random blobs shaped like X4's training folds (2,000 x 15, three classes), single core; and the
parameter counts of the three generator architectures. No real or synthetic data is read."""
import os, time, json
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from sklearn.datasets import make_blobs
from sklearn.ensemble import RandomForestClassifier

X, y = make_blobs(n_samples=2000, n_features=15, centers=3, cluster_std=4.0, random_state=0)
per_tree = {}
for d in [6, 8, 10, 12, 14, 16]:
    rf = RandomForestClassifier(n_estimators=100, max_depth=d, min_samples_split=3, random_state=42)
    t0 = time.perf_counter(); rf.fit(X, y); per_tree[d] = (time.perf_counter() - t0) / 100
n_est = [10, 100, 200, 500, 1000]
grid_one_fold = sum(n * per_tree[d] for n in n_est for d in per_tree) * 4      # four min_samples_split values
grid_total = 3 * grid_one_fold + 1.5 * 500 * per_tree[16]                     # three folds and a refit on 3,000
out = {"rf_s_per_tree_by_depth": {d: round(v, 5) for d, v in per_tree.items()},
       "rf_codegrid_one_search_s": round(grid_total, 1)}

import tsgm
nft = 16
vae = tsgm.models.zoo["vae_conv5"](9, nft, 10)
cg = tsgm.models.architectures.zoo["cgan_base_c4_l1"](seq_len=9, feat_dim=nft, latent_dim=38, output_dim=3)
rc = tsgm.models.architectures.cGAN_LSTMnArchitecture(seq_len=9, feat_dim=nft, latent_dim=36, output_dim=3)
out["params"] = {"vae_encoder": vae.encoder.count_params(), "vae_decoder": vae.decoder.count_params(),
                 "cgan_generator": cg.generator.count_params(), "cgan_discriminator": cg.discriminator.count_params(),
                 "rcgan_generator": rc._generator.count_params(), "rcgan_discriminator": rc._discriminator.count_params()}
print(json.dumps(out))
