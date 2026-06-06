-- Zero Day Warranty · medallion + audit ledger on the shared Postgres flexible server.
--
--   Server : pg-zdw-agentic<uniq>.postgres.database.azure.com  (project-owned)
--   DB     : zdw  (project database in the Agentic-Automotives RG)
--   Apply  : psql "$DATABASE_URL" -f infra/scripts/postgres-schemas.sql
--
-- The Postgres medallion is the RnD substrate; the production target is
-- Microsoft Fabric OneLake. Schema names and the per-VIN Gold contract carry over.

-- ---------------------------------------------------------------------------
-- Medallion schemas
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS zdw_bronze;
CREATE SCHEMA IF NOT EXISTS zdw_silver;
CREATE SCHEMA IF NOT EXISTS zdw_gold;

-- ---------------------------------------------------------------------------
-- Silver · canonical, VIN-conformed (mirrors zero_day_warranty.domains)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zdw_silver.build_records (
    vin            text PRIMARY KEY,
    plant          text NOT NULL,
    line           text NOT NULL,
    station        text NOT NULL,
    tool_id        text NOT NULL,
    shift          text NOT NULL,
    operator_id    text NOT NULL,
    supplier_lot   text NOT NULL,
    part_number    text NOT NULL,
    build_date     date NOT NULL,
    build_week     int  NOT NULL
);

CREATE TABLE IF NOT EXISTS zdw_silver.warranty_claims (
    claim_id              text PRIMARY KEY,
    vin                   text NOT NULL,
    part_number           text NOT NULL,
    failure_mode          text NOT NULL,
    fault_code            text,
    severity              text NOT NULL DEFAULT 'medium',
    dealer_code           text,
    claim_date            date NOT NULL,
    build_to_claim_months numeric NOT NULL,
    claim_cost_usd        numeric NOT NULL
);

CREATE TABLE IF NOT EXISTS zdw_silver.quality_events (
    event_id     text PRIMARY KEY,
    vin          text NOT NULL,
    station      text NOT NULL,
    measurement  text NOT NULL,
    value        numeric,
    spec_lower   numeric,
    spec_upper   numeric,
    result       text NOT NULL DEFAULT 'pass',
    confidence   numeric NOT NULL DEFAULT 1.0,
    captured_at  timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS zdw_silver.assembly_telemetry (
    trace_id              text PRIMARY KEY,
    vin                   text NOT NULL,
    station               text NOT NULL,
    tool_id               text NOT NULL,
    torque_nm             numeric,
    angle_deg             numeric,
    calibration_drift_pct numeric NOT NULL DEFAULT 0.0,
    cycle_time_s          numeric,
    humidity_pct          numeric,
    temperature_c         numeric,
    captured_at           timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_claims_vin     ON zdw_silver.warranty_claims (vin);
CREATE INDEX IF NOT EXISTS ix_quality_vin    ON zdw_silver.quality_events (vin);
CREATE INDEX IF NOT EXISTS ix_telemetry_vin  ON zdw_silver.assembly_telemetry (vin);
CREATE INDEX IF NOT EXISTS ix_build_lot      ON zdw_silver.build_records (supplier_lot);
CREATE INDEX IF NOT EXISTS ix_build_week     ON zdw_silver.build_records (build_week);

-- ---------------------------------------------------------------------------
-- Gold · per-VIN joinable view across the four domains
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW zdw_gold.g_vehicle_root_cause AS
SELECT
    b.vin,
    b.plant, b.line, b.station, b.tool_id, b.shift, b.supplier_lot, b.build_week,
    COALESCE(c.claim_count, 0)                AS claim_count,
    COALESCE(c.total_claim_cost, 0)           AS total_claim_cost,
    COALESCE(q.spc_anomaly_count, 0)          AS spc_anomaly_count,
    COALESCE(t.max_calibration_drift_pct, 0)  AS max_calibration_drift_pct
FROM zdw_silver.build_records b
LEFT JOIN (
    SELECT vin, COUNT(*) AS claim_count, SUM(claim_cost_usd) AS total_claim_cost
    FROM zdw_silver.warranty_claims GROUP BY vin
) c ON c.vin = b.vin
LEFT JOIN (
    SELECT vin, COUNT(*) FILTER (
        WHERE result = 'fail'
           OR (spec_upper IS NOT NULL AND value > spec_upper)
           OR (spec_lower IS NOT NULL AND value < spec_lower)
    ) AS spc_anomaly_count
    FROM zdw_silver.quality_events GROUP BY vin
) q ON q.vin = b.vin
LEFT JOIN (
    SELECT vin, MAX(calibration_drift_pct) AS max_calibration_drift_pct
    FROM zdw_silver.assembly_telemetry GROUP BY vin
) t ON t.vin = b.vin;

-- ---------------------------------------------------------------------------
-- Gold · append-only, hash-chained audit ledger (14-field decision row)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zdw_gold.audit_ledger (
    decision_id                    text PRIMARY KEY,
    trace_id                       text NOT NULL,
    agent_id                       text NOT NULL,
    invoking_identity              text NOT NULL,
    manifest_version               text NOT NULL,
    policy_version                 text NOT NULL,
    model_version                  text NOT NULL,
    prompt_version                 text NOT NULL,
    inputs_ref                     text NOT NULL,
    tools_called                   jsonb NOT NULL DEFAULT '[]'::jsonb,
    reasoning_trace_ref            text NOT NULL,
    decision_output                jsonb NOT NULL,
    hitl_status                    text NOT NULL DEFAULT 'none',
    downstream_effect_ref          text,
    cost_attribution               jsonb,
    sensitivity_label_propagation  jsonb NOT NULL DEFAULT '[]'::jsonb,
    confidence_score               numeric,
    prev_link                      text NOT NULL,
    signature                      text NOT NULL,
    sealed_at                      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_trace ON zdw_gold.audit_ledger (trace_id);

-- Enforce append-only (WORM-style): block UPDATE / DELETE / TRUNCATE.
CREATE OR REPLACE FUNCTION zdw_gold.audit_no_mutate() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'zdw_gold.audit_ledger is append-only; % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_append_only ON zdw_gold.audit_ledger;
CREATE TRIGGER trg_audit_append_only
    BEFORE UPDATE OR DELETE ON zdw_gold.audit_ledger
    FOR EACH ROW EXECUTE FUNCTION zdw_gold.audit_no_mutate();
