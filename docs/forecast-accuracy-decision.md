# Forecast Accuracy Decision Record

**Phase 9 — Operational Domain Design | Scope Decision**

---

# Decision

Forecast accuracy is intentionally deferred to Version 2.

---

# Context

Early architecture drafts considered adding `fact_forecast_accuracy` and related forecast-versus-actual comparison models.

During Phase 9 it was determined that forecast accuracy is outside the scope of Version 1 because it requires historical data sources and comparison logic that are not necessary to answer the approved operational business questions.

---

# Reasoning

Forecast accuracy requires comparing a forecast issued at time **T** against the weather that actually occurred at time **T+n**.

A complete implementation requires:

- Archived forecast snapshots rather than only the latest forecast.
- Historical observed-weather data.
- Forecast issue timestamps.
- Forecast target timestamps.
- Forecast horizon tracking.
- Comparison logic by location and timestamp.
- Error metrics such as Mean Absolute Error (MAE), bias, and other forecast-quality measures.

Open-Meteo's live forecast endpoint provides current forecast data but does not retain historical forecast snapshots required for retrospective forecast evaluation.

Version 1 does not include this supporting infrastructure.

---

# Scope Impact

Version 1 focuses on operational decision support.

The platform answers questions such as:

- Should work continue?
- Which crews should be rescheduled?
- Which projects are at risk?
- Which equipment should be relocated?
- Which regions require attention?

None of the seven approved dashboard pages require forecast accuracy calculations.

Accordingly:

- Version 1 does **not** implement `fact_forecast_accuracy`.
- Forecast data is used for operational decision-making only.
- Forecasts are evaluated as they exist when ingested rather than compared with future observations.

This decision does not block any approved Version 1 functionality.

---

# Version 2 Requirements

A future implementation should include:

- Archive every forecast run rather than overwriting previous forecasts.
- Add a historical observed-weather source.
- Design `fact_forecast_accuracy` with grain:

  - Location
  - Forecast issue timestamp
  - Forecast target timestamp
  - Forecast horizon

- Define forecast quality metrics including:

  - Mean Absolute Error (MAE)
  - Forecast Bias
  - Additional accuracy metrics as appropriate

- Define a retention policy for archived forecasts and observed-weather history.

- Add Forecast Reliability reporting to the analytics platform.

---

# Status

**Approved for Version 1.**

Forecast accuracy is intentionally deferred because it requires historical forecast archives and observed-weather data that are outside the scope of the Version 1 operational decision-support platform.

This decision is considered closed unless Version 1 business requirements change.