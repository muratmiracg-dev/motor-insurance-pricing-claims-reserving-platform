# Data Dictionary

## `customers`

| Field | Meaning |
| --- | --- |
| `customer_id` | Synthetic stable customer key |
| `driver_age` | Driver age at generation |
| `license_years` | Completed driving-license years |
| `region` | Broad Turkish geographical region |
| `customer_tenure_years` | Synthetic insurer relationship tenure |

## `vehicles`

| Field | Meaning |
| --- | --- |
| `vehicle_id` | Synthetic vehicle key |
| `vehicle_segment` | A, B, C, D, SUV, or light-commercial segment |
| `vehicle_age` | Vehicle age in completed years |
| `vehicle_value` | Synthetic insured vehicle value in TRY |
| `fuel_type` | Petrol, diesel, hybrid, or electric |
| `annual_km` | Expected annual distance |

## `policies`

| Field | Meaning |
| --- | --- |
| `policy_id` | Synthetic policy key |
| `customer_id`, `vehicle_id` | Foreign keys |
| `policy_start`, `policy_end` | Contract dates |
| `observation_end` | Exposure cutoff at contract end or valuation |
| `underwriting_year` | Policy inception year |
| `usage_type` | Private, commercial, or fleet use |
| `sales_channel` | Agency, bank, direct, or broker |
| `coverage_package` | Standard, extended, or premium cover |
| `deductible` | Synthetic deductible amount in TRY |
| `no_claim_years` | Prior no-claim duration |
| `exposure_years` | Observed policy duration in years |
| `annual_written_premium` | Annualized written premium |
| `earned_premium` | Premium earned through observation end |
| `commission_ratio` | Channel-level synthetic commission ratio |
| `expected_*_seed` | Generator controls; excluded from fitted models |

## `claims`

| Field | Meaning |
| --- | --- |
| `claim_id` | Synthetic claim key |
| `policy_id`, `customer_id`, `vehicle_id`, `garage_id` | Relationship keys |
| `claim_date`, `report_date`, `closure_date` | Claim lifecycle dates |
| `claim_type` | Collision, glass, theft, weather, or vandalism |
| `claim_status` | Open or closed at valuation |
| `policy_tenure_days` | Days from policy inception to loss |
| `report_delay_days` | Days from loss to notification |
| `loss_hour` | Synthetic hour of loss |
| `paid_to_date` | Cumulative paid indemnity at valuation |
| `case_reserve` | Synthetic case reserve at valuation |
| `incurred_amount` | Paid plus case reserve |
| `ultimate_incurred_synthetic_truth` | Hidden generator truth for backtesting only |
| `fraud_synthetic_truth` | Strict boolean synthetic evaluation label only; non-boolean values are rejected |

## `claim_payments`

| Field | Meaning |
| --- | --- |
| `payment_id` | Synthetic payment key |
| `claim_id` | Parent claim |
| `payment_no` | Within-claim payment sequence |
| `payment_date` | Payment date through valuation |
| `payment_amount` | Paid indemnity in TRY |
| `payment_type` | Current version uses indemnity payments |

### Reserving input controls

Before a paid-loss triangle is built, every payment must reference exactly one
unique claim, payment dates must be valid and no earlier than the related claim
date, and payment amounts must be finite and non-negative. Claims dated after the
valuation date are rejected. These controls fail fast so malformed records cannot
silently distort development factors or reserve indications.

## Derived analytical outputs

| Dataset | Grain | Purpose |
| --- | --- | --- |
| `policy_modeling_frame` | Policy | Exposure, claims, features, and targets |
| `policy_pricing_scores` | Policy | Frequency, severity, pure premium, indication |
| `reserve_by_accident_quarter` | Accident quarter | Paid, ultimate, IBNR, and backtest |
| `claim_triage_scores` | Claim | Review score, priority, and reason codes |
| `segment_performance` | Dimension member | Premium, loss, frequency, severity, loss ratio |
