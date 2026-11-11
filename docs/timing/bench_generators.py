"""Timing benchmark of the three generator architectures of the Deep-IAM "Secondary" notebooks
(tsgm 0.0.7, TensorFlow 2.13), on random arrays of the same shape. No AR6, Deep-IAM or synthetic
data is read, and no claim rule is evaluated: this measures seconds per optimisation step only.

Usage: python bench_generators.py THREADS NFT
"""
import os, sys, time, math, json
threads, nft = int(sys.argv[1]), int(sys.argv[2])
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np
import tensorflow as tf
from tensorflow import keras
tf.config.threading.set_intra_op_parallelism_threads(threads)
tf.config.threading.set_inter_op_parallelism_threads(threads)
import tsgm

rng = np.random.default_rng(0)
out = {"threads": threads, "nft": nft}


def timed_fit(fit, n_steps_per_epoch, warm=2, epochs=20):
    fit(warm)                                   # tracing and graph building excluded
    t0 = time.perf_counter()
    fit(epochs)
    dt = time.perf_counter() - t0
    return dt / (epochs * n_steps_per_epoch)


# VAE, one per category, paper batch sizes (C1234 554/50, C56 237/30, C78 110/25)
for cat, n, batch in [("C1234", 554, 50), ("C56", 237, 30), ("C78", 110, 25)]:
    X = rng.random((n, 9, nft)).astype("float32")
    arch = tsgm.models.zoo["vae_conv5"](9, nft, 10)
    vae = tsgm.models.cvae.BetaVAE(arch.encoder, arch.decoder)
    vae.compile(optimizer=keras.optimizers.Adam(keras.optimizers.schedules.ExponentialDecay(1e-3, 500, 0.98)))
    s = timed_fit(lambda e: vae.fit(X, epochs=e, batch_size=batch, verbose=0), math.ceil(n / batch))
    out[f"vae_{cat}_s_per_step"] = s

# conditional GANs on the pooled 901 scenarios, batch 100
n = 901
X = rng.random((n, 9, nft)).astype("float32")
Y = keras.utils.to_categorical(rng.integers(0, 3, n), 3).astype("float32")
ds = tf.data.Dataset.from_tensor_slices((X, Y)).shuffle(1024).batch(100)
for name, build, latent in [
        ("cgan", lambda: tsgm.models.architectures.zoo["cgan_base_c4_l1"](seq_len=9, feat_dim=nft, latent_dim=38, output_dim=3), 38),
        ("rcgan", lambda: tsgm.models.architectures.cGAN_LSTMnArchitecture(seq_len=9, feat_dim=nft, latent_dim=36, output_dim=3), 36)]:
    arch = build()
    d = getattr(arch, "discriminator", None) or arch._discriminator
    g = getattr(arch, "generator", None) or arch._generator
    gan = tsgm.models.cgan.ConditionalGAN(discriminator=d, generator=g, latent_dim=latent)
    sched = keras.optimizers.schedules.ExponentialDecay(1e-4, 200, 0.95)
    gan.compile(d_optimizer=keras.optimizers.Adam(sched), g_optimizer=keras.optimizers.Adam(sched),
                loss_fn=keras.losses.BinaryCrossentropy())
    s = timed_fit(lambda e: gan.fit(ds, epochs=e, verbose=0), math.ceil(n / 100), epochs=10)
    out[f"{name}_s_per_step"] = s

print(json.dumps(out))
