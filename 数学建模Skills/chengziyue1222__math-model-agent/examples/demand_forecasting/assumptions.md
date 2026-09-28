# Assumptions

- Monthly demand has a stable additive trend and month-of-year effect.
- The first 24 observations are training data and the final 12 are an untouched holdout.
- Calendar features are known at forecast time; holdout demand is never used to fit coefficients.
- A seasonal-naive forecast using the previous year's same month is the minimum baseline.
