CREATE TYPE degree_type AS ENUM ('Bachelor''s Degree', 'Master''s Degree', 'First-Level Specializing Master', 'Single-Cycle Degree','Doctorate');
CREATE TYPE degree_field AS ENUM ('Enginering', 'Economics', 'Medicine', 'Science', 'Agriculture');

CREATE TABLE IF NOT EXISTS degree (
    id VARCHAR(5) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type degree_type NOT NULL,
    category degree_field NOT NULL
);

CREATE TABLE IF NOT EXISTS course (
    id SERIAL PRIMARY KEY,
    degree_id VARCHAR(5) REFERENCES degree(id),
    name VARCHAR(255) NOT NULL,
    is_mandatory BOOLEAN NOT NULL
);