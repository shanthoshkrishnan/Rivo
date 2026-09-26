-- RIVO DB Initialisation Script
-- Runs automatically when the PostGIS Docker container first starts.
-- Creates required PostgreSQL extensions.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- for address similarity queries

-- Ensure UTF-8 encoding
SET client_encoding TO 'UTF8';
