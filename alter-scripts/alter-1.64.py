import os
import sys
from pathlib import Path
from decouple import config
import django

from connection import execute

BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(BASE_DIR)
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mulearnbackend.settings')
django.setup()

DB_NAME = config('DATABASE_NAME')


def table_exists(table_name):
    query = f"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{DB_NAME}' AND TABLE_NAME = '{table_name}';"
    result = execute(query)
    return result and result[0][0] > 0


if __name__ == '__main__':
    # μCoin integration: transactional outbox for domain events delivered to
    # mucoin-service (see mu_events app; contract in
    # gtech-mulearn/mucoin-service INTEGRATION.md).
    if not table_exists('event_outbox'):
        execute("""
            CREATE TABLE `event_outbox` (
                `id`            CHAR(36)     NOT NULL PRIMARY KEY,
                `event_type`    VARCHAR(64)  NOT NULL,
                `muid`          VARCHAR(100) NOT NULL,
                `payload`       JSON         NOT NULL,
                `created_at`    DATETIME(6)  NOT NULL,
                `dispatched_at` DATETIME(6)  NULL,
                `attempts`      INT          NOT NULL DEFAULT 0,
                `next_retry_at` DATETIME(6)  NULL,
                KEY `idx_outbox_undispatched` (`dispatched_at`, `next_retry_at`)
            );
        """)
        print('created table event_outbox')
    else:
        print('table event_outbox already exists, skipping')
