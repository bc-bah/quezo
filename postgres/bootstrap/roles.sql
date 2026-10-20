\set ON_ERROR_STOP on
\getenv migration_password QUEZO_MIGRATION_PASSWORD
\getenv runtime_password QUEZO_RUNTIME_PASSWORD
SELECT length(:'migration_password') > 0
   AND length(:'runtime_password') > 0
   AND :'migration_password' <> :'runtime_password' AS passwords_valid \gset
\if :passwords_valid
\else
  \echo 'Distinct nonempty migration and runtime passwords are required.'
  \quit 1
\endif

BEGIN;
CREATE ROLE quezo_migrator LOGIN PASSWORD :'migration_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE quezo_runtime LOGIN PASSWORD :'runtime_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
SELECT current_database() AS database_name \gset
ALTER DATABASE :"database_name" OWNER TO quezo_migrator;
REVOKE ALL ON DATABASE :"database_name" FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
COMMIT;
