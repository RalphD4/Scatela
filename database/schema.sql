CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(20) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guardian (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    location_updated_at TIMESTAMP
);

CREATE TABLE child (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    location_updated_at TIMESTAMP
);

CREATE TABLE bases (
    base_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES guardian(user_id),
    base_name TEXT NOT NULL,

    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,

    warning_radius INTEGER NOT NULL,
    danger_radius INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bases_radius_check CHECK (warning_radius > 0 AND danger_radius > warning_radius)
);


CREATE TABLE emergency_contact (
    contact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_name VARCHAR(20) NOT NULL,
    phone_number TEXT NOT NULL
);

CREATE TABLE child_emergency_contact (
    child_id UUID NOT NULL REFERENCES child(user_id),
    contact_id UUID NOT NULL REFERENCES emergency_contact(contact_id),
    PRIMARY KEY (child_id, contact_id)
);


CREATE TABLE child_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id UUID NOT NULL REFERENCES child(user_id),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guardian_child (
    guardian_id UUID NOT NULL REFERENCES guardian(user_id),
    child_id UUID NOT NULL REFERENCES child(user_id),

    PRIMARY KEY (guardian_id, child_id)
);

CREATE TABLE child_base_status (
    child_id UUID NOT NULL REFERENCES child(user_id) ON DELETE CASCADE,
    base_id UUID NOT NULL REFERENCES bases(base_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('normal', 'warning', 'danger')),
    distance_meters DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (child_id, base_id)
);

CREATE TABLE alerts (
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

CREATE INDEX idx_alerts_guardian_active ON alerts (guardian_id, is_active, created_at DESC);
CREATE INDEX idx_child_log_child_created ON child_log (child_id, created_at DESC);
