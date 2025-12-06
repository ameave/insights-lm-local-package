\set pguser `echo "$POSTGRES_USER"`
\set pgpass `echo "$POSTGRES_PASSWORD"`

\echo '--------------- Initializing n8n database ---------------';
CREATE DATABASE _n8n WITH OWNER :pguser;
GRANT ALL PRIVILEGES ON DATABASE _n8n TO supabase_admin;

\c _n8n
GRANT ALL PRIVILEGES ON SCHEMA public TO supabase_admin;
\c postgres

\echo '--------------- n8n database initialized  ---------------';

