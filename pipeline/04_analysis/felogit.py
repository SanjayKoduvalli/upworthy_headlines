"""Logistic regression with one intercept per test (test fixed effects) for grouped click data, using numpy/scipy only.

Why written here: statsmodels can't be installed in this environment (NOTES §5.2, §8.2); Sanjay approved writing the fit
with installed tools and checking it against statsmodels on his Mac (scripts/checks/statsmodels_check.py, R19).

Model: clicks_i ~ Binomial(impressions_i, p_i), logit(p_i) = alpha_test(i) + x_i' beta.
Method: the per-test intercepts are "profiled out": for any beta, each alpha_t has a one-dimensional solution (expected
clicks in the test = observed clicks), found by Newton steps for all tests at once. Beta is then fitted by Newton steps
on the profiled likelihood, whose curvature is X'WX minus, for each test, (X_t'w_t)(w_t'X_t) / sum(w_t) (the Schur
complement of the intercept block). This gives exactly the same beta and standard errors as fitting thousands of
dummy columns, without building them.
Quasi-binomial (AA6, R18): variances are multiplied by phi. The fit also reports phi estimated from its own residuals
(Pearson chi-square / residual degrees of freedom) as the cross-check M1-phi.
"""
import numpy as np
from scipy import special, stats


def _alpha_for(beta, X, y, n, g, n_groups, alpha):
    """Solve each test's intercept so that expected clicks equal observed clicks (vectorized 1-D Newton)."""
    eta0 = X @ beta
    ysum = np.bincount(g, weights=y, minlength=n_groups)
    for _ in range(100):
        mu = special.expit(alpha[g] + eta0)
        f = np.bincount(g, weights=n * mu, minlength=n_groups) - ysum
        d = np.bincount(g, weights=n * mu * (1 - mu), minlength=n_groups)
        step = f / d
        alpha = alpha - np.clip(step, -5, 5)
        if np.max(np.abs(step)) < 1e-12:
            break
    return alpha


def fit(X, clicks, impressions, groups, names, phi=1.0, tol=1e-10, max_iter=100):
    """Fit the fixed-effects logit. X: (rows, k) array; groups: test ids. Returns a dict with beta, standard errors
    (unscaled and scaled by phi), z, p, Pearson phi, and fit details. Groups with zero clicks are dropped (their
    intercept would be minus infinity and they carry no information about beta)."""
    X = np.asarray(X, float); y = np.asarray(clicks, float); n = np.asarray(impressions, float)
    codes, g = np.unique(np.asarray(groups), return_inverse=True)
    keep_group = np.bincount(g, weights=y) > 0
    keep = keep_group[g]
    X, y, n = X[keep], y[keep], n[keep]
    _, g = np.unique(g[keep], return_inverse=True)
    G, k = g.max() + 1, X.shape[1]

    # columns with no within-test variation are not identified: refuse rather than return nonsense
    size = np.bincount(g, minlength=G)
    means = np.column_stack([np.bincount(g, weights=X[:, j], minlength=G) / size for j in range(k)])
    dev = X - means[g]
    if np.any(np.abs(dev).sum(axis=0) == 0):
        bad = [names[j] for j in np.where(np.abs(dev).sum(axis=0) == 0)[0]]
        raise ValueError(f"no within-test variation in: {bad}")

    beta = np.zeros(k)
    pooled = y.sum() / n.sum()
    alpha = np.full(G, np.log(pooled / (1 - pooled)))
    for it in range(max_iter):
        alpha = _alpha_for(beta, X, y, n, g, G, alpha)
        mu = special.expit(alpha[g] + X @ beta)
        w = n * mu * (1 - mu)
        score = X.T @ (y - n * mu)
        wx = np.column_stack([np.bincount(g, weights=w * X[:, j], minlength=G) for j in range(k)])   # G x k
        wsum = np.bincount(g, weights=w, minlength=G)
        info = (X * w[:, None]).T @ X - (wx / wsum[:, None]).T @ wx
        step = np.linalg.solve(info, score)
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    alpha = _alpha_for(beta, X, y, n, g, G, alpha)
    mu = special.expit(alpha[g] + X @ beta)
    w = n * mu * (1 - mu)
    wx = np.column_stack([np.bincount(g, weights=w * X[:, j], minlength=G) for j in range(k)])
    wsum = np.bincount(g, weights=w, minlength=G)
    info = (X * w[:, None]).T @ X - (wx / wsum[:, None]).T @ wx
    cov = np.linalg.inv(info)
    resid_df = len(y) - G - k
    pearson = float(((y - n * mu) ** 2 / w).sum())
    se_raw = np.sqrt(np.diag(cov)); se = se_raw * np.sqrt(phi)
    z = beta / se
    return {"names": list(names), "beta": beta, "se_raw": se_raw, "se": se, "z": z, "z_raw": beta / se_raw,
            "p": 2 * stats.norm.sf(np.abs(z)), "cov": cov * phi, "cov_raw": cov, "phi_used": phi,
            "phi_pearson": pearson / resid_df, "n_rows": len(y), "n_groups": int(G), "resid_df": resid_df,
            "iterations": it + 1, "dropped_zero_click_groups": int((~keep_group).sum())}


def contrast(res, a, b):
    """Difference of two coefficients (a - b) with its scaled standard error."""
    i, j = res["names"].index(a), res["names"].index(b)
    d = res["beta"][i] - res["beta"][j]
    se = np.sqrt(res["cov"][i, i] + res["cov"][j, j] - 2 * res["cov"][i, j])
    return d, se, 2 * stats.norm.sf(abs(d / se))


def pct_change(b):
    """Coefficient on the log-odds scale -> % change in click odds (~ % change in click rate at ~1.5% rates)."""
    return 100 * (np.exp(b) - 1)
