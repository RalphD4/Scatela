CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guardian (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION
);

CREATE TABLE child (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION
);

CREATE TABLE bases (
    base_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES guardian(user_id),
    base_name TEXT NOT NULL,

    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,

    warning_radius INTEGER NOT NULL,
    danger_radius INTEGER NOT NULL
);


CREATE TABLE emergency_contact (
    contact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id UUID NOT NULL REFERENCES child(user_id),
    contact_name VARCHAR(100) NOT NULL,
    phone_number TEXT NOT NULL
);


CREATE TABLE child_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id UUID NOT NULL REFERENCES child(user_id),
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE parent_child (
    guardian_id UUID NOT NULL REFERENCES guardian(user_id),
    child_id UUID NOT NULL REFERENCES child(user_id),

    PRIMARY KEY (guardian_id, child_id)
);


