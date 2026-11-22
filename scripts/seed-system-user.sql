-- Local development only, applied by scripts/local-db-init.sh. No real data.
-- The backend refuses to start without a user whose id is SYSTEM_ADMIN_ID (db/apps.py);
-- this id must match SYSTEM_ADMIN_ID in .env.local.example.
INSERT IGNORE INTO user (id, muid, full_name, email, created_at)
VALUES ('00000000-0000-4000-8000-000000000001', 'system@mulearn.local', 'System', 'system@mulearn.local', NOW());
