-- Motor Insurance Technical Pricing, Claims & Reserving Analytics Platform
-- PostgreSQL reference model. All records used by the portfolio project are synthetic.

CREATE SCHEMA IF NOT EXISTS motor_insurance;

CREATE TABLE IF NOT EXISTS motor_insurance.dim_customer (
    customer_id VARCHAR(20) PRIMARY KEY,
    driver_age SMALLINT NOT NULL CHECK (driver_age BETWEEN 18 AND 100),
    license_years SMALLINT NOT NULL CHECK (license_years >= 0),
    region VARCHAR(40) NOT NULL,
    customer_tenure_years NUMERIC(6,2) NOT NULL CHECK (customer_tenure_years >= 0)
);

CREATE TABLE IF NOT EXISTS motor_insurance.dim_vehicle (
    vehicle_id VARCHAR(20) PRIMARY KEY,
    vehicle_segment VARCHAR(30) NOT NULL,
    vehicle_age SMALLINT NOT NULL CHECK (vehicle_age >= 0),
    vehicle_value NUMERIC(18,2) NOT NULL CHECK (vehicle_value > 0),
    fuel_type VARCHAR(20) NOT NULL,
    annual_km INTEGER NOT NULL CHECK (annual_km > 0)
);

CREATE TABLE IF NOT EXISTS motor_insurance.dim_garage (
    garage_id VARCHAR(20) PRIMARY KEY,
    garage_region VARCHAR(40) NOT NULL,
    network_watchlist_signal BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS motor_insurance.fact_policy (
    policy_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES motor_insurance.dim_customer(customer_id),
    vehicle_id VARCHAR(20) NOT NULL REFERENCES motor_insurance.dim_vehicle(vehicle_id),
    policy_start DATE NOT NULL,
    policy_end DATE NOT NULL,
    observation_end DATE NOT NULL,
    underwriting_year SMALLINT NOT NULL,
    usage_type VARCHAR(20) NOT NULL,
    sales_channel VARCHAR(20) NOT NULL,
    coverage_package VARCHAR(20) NOT NULL,
    deductible NUMERIC(18,2) NOT NULL CHECK (deductible >= 0),
    no_claim_years SMALLINT NOT NULL CHECK (no_claim_years >= 0),
    exposure_years NUMERIC(12,6) NOT NULL CHECK (exposure_years > 0),
    annual_written_premium NUMERIC(18,2) NOT NULL CHECK (annual_written_premium > 0),
    earned_premium NUMERIC(18,2) NOT NULL CHECK (earned_premium >= 0),
    commission_ratio NUMERIC(9,6) NOT NULL CHECK (commission_ratio BETWEEN 0 AND 1),
    CHECK (policy_end >= policy_start),
    CHECK (observation_end BETWEEN policy_start AND policy_end)
);

CREATE TABLE IF NOT EXISTS motor_insurance.fact_claim (
    claim_id VARCHAR(20) PRIMARY KEY,
    policy_id VARCHAR(20) NOT NULL REFERENCES motor_insurance.fact_policy(policy_id),
    customer_id VARCHAR(20) NOT NULL REFERENCES motor_insurance.dim_customer(customer_id),
    vehicle_id VARCHAR(20) NOT NULL REFERENCES motor_insurance.dim_vehicle(vehicle_id),
    garage_id VARCHAR(20) REFERENCES motor_insurance.dim_garage(garage_id),
    claim_date DATE NOT NULL,
    report_date DATE NOT NULL,
    closure_date DATE,
    claim_type VARCHAR(30) NOT NULL,
    claim_status VARCHAR(12) NOT NULL CHECK (claim_status IN ('Open', 'Closed')),
    policy_tenure_days INTEGER NOT NULL CHECK (policy_tenure_days >= 0),
    report_delay_days INTEGER NOT NULL CHECK (report_delay_days >= 0),
    loss_hour SMALLINT NOT NULL CHECK (loss_hour BETWEEN 0 AND 23),
    paid_to_date NUMERIC(18,2) NOT NULL CHECK (paid_to_date >= 0),
    case_reserve NUMERIC(18,2) NOT NULL CHECK (case_reserve >= 0),
    incurred_amount NUMERIC(18,2) NOT NULL CHECK (incurred_amount >= 0),
    ultimate_incurred_synthetic_truth NUMERIC(18,2) NOT NULL CHECK (ultimate_incurred_synthetic_truth >= 0),
    fraud_synthetic_truth BOOLEAN NOT NULL,
    CHECK (report_date >= claim_date)
);

CREATE TABLE IF NOT EXISTS motor_insurance.fact_claim_payment (
    payment_id VARCHAR(24) PRIMARY KEY,
    claim_id VARCHAR(20) NOT NULL REFERENCES motor_insurance.fact_claim(claim_id),
    payment_no SMALLINT NOT NULL CHECK (payment_no > 0),
    payment_date DATE NOT NULL,
    payment_amount NUMERIC(18,2) NOT NULL CHECK (payment_amount >= 0),
    payment_type VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS motor_insurance.fact_pricing_score (
    policy_id VARCHAR(20) PRIMARY KEY REFERENCES motor_insurance.fact_policy(policy_id),
    dataset_split VARCHAR(20) NOT NULL,
    predicted_annual_frequency NUMERIC(18,8) NOT NULL CHECK (predicted_annual_frequency > 0),
    predicted_average_severity NUMERIC(18,2) NOT NULL CHECK (predicted_average_severity > 0),
    predicted_pure_premium NUMERIC(18,2) NOT NULL CHECK (predicted_pure_premium > 0),
    indicated_technical_premium NUMERIC(18,2) NOT NULL CHECK (indicated_technical_premium > 0),
    pricing_adequacy_index NUMERIC(18,8) NOT NULL CHECK (pricing_adequacy_index > 0),
    pricing_action VARCHAR(40) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policy_start ON motor_insurance.fact_policy(policy_start);
CREATE INDEX IF NOT EXISTS idx_claim_date ON motor_insurance.fact_claim(claim_date);
CREATE INDEX IF NOT EXISTS idx_claim_policy ON motor_insurance.fact_claim(policy_id);
CREATE INDEX IF NOT EXISTS idx_payment_claim ON motor_insurance.fact_claim_payment(claim_id);

CREATE OR REPLACE VIEW motor_insurance.vw_technical_performance AS
SELECT
    p.underwriting_year,
    c.region,
    v.vehicle_segment,
    p.usage_type,
    p.sales_channel,
    COUNT(DISTINCT p.policy_id) AS policy_count,
    SUM(p.exposure_years) AS exposure_years,
    SUM(p.earned_premium) AS earned_premium,
    COUNT(cl.claim_id) AS claim_count,
    COALESCE(SUM(cl.incurred_amount), 0) AS incurred_claims,
    COUNT(cl.claim_id) / NULLIF(SUM(p.exposure_years), 0) AS claim_frequency,
    COALESCE(SUM(cl.incurred_amount), 0) / NULLIF(COUNT(cl.claim_id), 0) AS average_severity,
    COALESCE(SUM(cl.incurred_amount), 0) / NULLIF(SUM(p.earned_premium), 0) AS loss_ratio
FROM motor_insurance.fact_policy p
JOIN motor_insurance.dim_customer c ON c.customer_id = p.customer_id
JOIN motor_insurance.dim_vehicle v ON v.vehicle_id = p.vehicle_id
LEFT JOIN motor_insurance.fact_claim cl ON cl.policy_id = p.policy_id
GROUP BY p.underwriting_year, c.region, v.vehicle_segment, p.usage_type, p.sales_channel;

