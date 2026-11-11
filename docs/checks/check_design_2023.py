"""Structural check of the 2023 design stored in final_results.rds: only the design matrix `mat`,
`params`, `N` and the number of result entries are inspected. No claim value is read or used.
Checks that rows 1-4,096 and 4,097-8,192 are the base matrices A and B, i.e. that every later block
of 4,096 rows equals A with column i taken from B (sensobol's AB_i).

Usage: python -I check_design_2023.py data/external/gsa2023/final_results.rds   (needs numpy and rdata)
Result on 5 November 2026: blocks 3-14 equal A with one column from B; A and B share one point,
the centre of the cube (row 1 of A and row 4,097).
"""
import sys
import numpy as np
import rdata

obj = rdata.read_rds(sys.argv[1])
params = [str(p) for p in np.asarray(obj["params"]).ravel()]
N = int(np.asarray(obj["N"]).ravel()[0])
mat = np.asarray(obj["mat"], dtype=float)
n_results = len(obj["results"])
k = len(params)
print("params:", params)
print("N:", N, "| k:", k, "| mat:", mat.shape, "| result entries:", n_results)
assert mat.shape == (N * (k + 2), k) and n_results == mat.shape[0]
A, B = mat[:N], mat[N:2 * N]
for i in range(k):
    AB = mat[(2 + i) * N:(3 + i) * N]
    expected = A.copy()
    expected[:, i] = B[:, i]
    assert np.array_equal(AB, expected), f"block {i + 3} is not AB_{params[i]}"
print(f"blocks 3-{k + 2} equal A with one column from B, in the order of params: "
      f"rows 1-{N} = A, {N + 1}-{2 * N} = B")
shared = np.argwhere((A[:, None, :] == B[None, :, :]).all(axis=2))
print("design points shared by A and B (row of A, row of B):", [(int(i) + 1, int(j) + N + 1) for i, j in shared])
print("range of design points:", float(mat.min()), float(mat.max()))
