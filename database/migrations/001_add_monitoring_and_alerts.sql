-- Migration 001: Support optional initial coordinates, location update timestamps,
-- child base monitoring status tracking, and alerts without dropping existing data.
-- Safe to run multiple times (idempotent).

BEGIN;

-- Allow newly registered guardians and newly created children to start without coordinates
-- until their first automatic location report arrives, while preserving existing rows.
ALTER TABLE guardian
    ALTER COLUMN longitude DROP NOT NULL,
    ALTER COLUMN latitude DROP NOT NULL;

ALTER TABLE guardian
    ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP;

ALTER TABLE child
    ALTER COLUMN longitude DROP NOT NULL,
    ALTER COLUMN latitude DROP NOT NULL;

ALTER TABLE child
    ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP;

ALTER TABLE bases
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'bases_radius_check'
          AND conrelid = 'bases'::regclass
    ) THEN
        ALTER TABLE bases
            ADD CONSTRAINT bases_radius_check
            CHECK (warning_radius > 0 AND danger_radius > warning_radius);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS child_base_status (
    child_id UUID NOT NULL REFERENCES child(user_id) ON DELETE CASCADE,
    base_id UUID NOT NULL REFERENCES bases(base_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('normal', 'warning', 'danger')),
    distance_meters DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (child_id, base_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guardian_id UUID NOT NULL REFERENCES guardian(user_id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES child(user_id) ON DELETE CASCADE,
    base_id UUID NOT NULL REFERENCES bases(base_id) ON DELETE CASCADE,
    alert_type VARCHAR(20) NOT NULL CHECK (alert_type IN ('warning', 'danger')),
    distance_meters DOUBLE PRECISION NOT NULL,
    message TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_guardian_active
    ON alerts (guardian_id, is_active, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_child_log_child_created
    ON child_log (child_id, created_at DESC);

COMMIT;
