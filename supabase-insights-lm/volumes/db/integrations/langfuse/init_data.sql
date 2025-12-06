\set pguser `echo "$POSTGRES_USER"`
\set pgpass `echo "$POSTGRES_PASSWORD"`

\echo '--------------- Initializing Langfuse database ---------------';
CREATE DATABASE _langfuse WITH OWNER :pguser;
GRANT ALL PRIVILEGES ON DATABASE _langfuse TO supabase_admin;

\c _langfuse
GRANT ALL PRIVILEGES ON SCHEMA public TO supabase_admin;
\c postgres

\echo '--------------- Langfuse database initialized  ---------------';