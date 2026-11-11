"""Peak memory of one training process: the CGAN of the Deep-IAM "Secondary" notebooks fitted for
three epochs on random arrays (901 x 9 x 16), then 30,000 scenarios generated in batches of 1,000.
No AR6, Deep-IAM or synthetic data is read and no claim rule is evaluated.

Usage: python bench_memory.py   (Linux or macOS; the resource module does not exist on Windows)
"""
import os, resource, sys
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np, tensorflow as tf
from tensorflow import keras
tf.config.threading.set_intra_op_parallelism_threads(1); tf.config.threading.set_inter_op_parallelism_threads(1)
import tsgm
rng = np.random.default_rng(0); n, nft = 901, 16
X = rng.random((n, 9, nft)).astype("float32"); Y = keras.utils.to_categorical(rng.integers(0, 3, n), 3).astype("float32")
ds = tf.data.Dataset.from_tensor_slices((X, Y)).shuffle(1024).batch(100)
a = tsgm.models.architectures.zoo["cgan_base_c4_l1"](seq_len=9, feat_dim=nft, latent_dim=38, output_dim=3)
g = tsgm.models.cgan.ConditionalGAN(discriminator=a.discriminator, generator=a.generator, latent_dim=38)
g.compile(d_optimizer=keras.optimizers.Adam(1e-4), g_optimizer=keras.optimizers.Adam(1e-4), loss_fn=keras.losses.BinaryCrossentropy())
g.fit(ds, epochs=3, verbose=0)
z = np.concatenate([rng.standard_normal((30000, 38)), keras.utils.to_categorical(rng.integers(0, 3, 30000), 3)], axis=1)
_ = np.concatenate([a.generator(z[i:i+1000].astype("float32")).numpy() for i in range(0, 30000, 1000)])
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss          # kilobytes on Linux, bytes on macOS
print("max RSS MB", peak / (1024 ** 2 if sys.platform == "darwin" else 1024))
