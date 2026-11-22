#!/bin/bash
# Local development only. The mysql service in docker-compose.local.yml runs this once, on its
# first start (an empty data volume), from /docker-entrypoint-initdb.d. It loads the vendored
# schema into `mulearn` and `test_mulearn`, then seeds the system user the backend checks for at
# startup (db/apps.py). It connects only through the container's own socket.
set -euo pipefail

if [ "${MULEARN_LOCAL_DB_INIT:-}" != "1" ] || [ ! -d /docker-entrypoint-initdb.d ]; then
    echo "local-db-init.sh only runs inside the mysql service of docker-compose.local.yml." >&2
    exit 1
fi

INIT_DIR=/docker-entrypoint-initdb.d
local_mysql() {
    mysql --protocol=socket -uroot -p"${MYSQL_ROOT_PASSWORD}" "$@"
}

for db in mulearn test_mulearn; do
    echo "local-db-init: building ${db} from schema/latest.sql"
    local_mysql -e "CREATE DATABASE IF NOT EXISTS \`${db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    # The schema adds a column with DEFAULT (UUID()), refused while binary logging is on.
    local_mysql --init-command="SET SESSION sql_log_bin=0" "${db}" < "${INIT_DIR}/schema/latest.sql"
    local_mysql "${db}" < "${INIT_DIR}/seed/seed-system-user.sql"
done
echo "local-db-init: done"
