"""
Migration script to add IG-based level tables
Creates:
- user_ig_lvl_link: Tracks current IG level for each user-IG combination
- user_ig_lvl_log: Audit log for IG level-ups
"""

from connection import execute


def create_user_ig_lvl_link_table():
    """Create user_ig_lvl_link table"""
    query = """
    CREATE TABLE IF NOT EXISTS user_ig_lvl_link (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        ig_id VARCHAR(36) NOT NULL,
        level_id VARCHAR(36) NOT NULL,
        updated_by VARCHAR(36) NOT NULL,
        updated_at DATETIME NOT NULL,
        created_by VARCHAR(36) NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY unique_user_ig (user_id, ig_id),
        CONSTRAINT fk_user_ig_lvl_link_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        CONSTRAINT fk_user_ig_lvl_link_ig FOREIGN KEY (ig_id) REFERENCES interest_group(id) ON DELETE CASCADE,
        CONSTRAINT fk_user_ig_lvl_link_level FOREIGN KEY (level_id) REFERENCES level(id) ON DELETE CASCADE,
        CONSTRAINT fk_user_ig_lvl_link_created_by FOREIGN KEY (created_by) REFERENCES user(id) ON DELETE CASCADE,
        CONSTRAINT fk_user_ig_lvl_link_updated_by FOREIGN KEY (updated_by) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """
    execute(query)
    print("✓ Created user_ig_lvl_link table")


def create_user_ig_lvl_log_table():
    """Create user_ig_lvl_log table"""
    query = """
    CREATE TABLE IF NOT EXISTS user_ig_lvl_log (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        ig_id VARCHAR(36) NOT NULL,
        level_id VARCHAR(36) NOT NULL,
        created_at DATETIME NOT NULL,
        CONSTRAINT fk_user_ig_lvl_log_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        CONSTRAINT fk_user_ig_lvl_log_ig FOREIGN KEY (ig_id) REFERENCES interest_group(id) ON DELETE CASCADE,
        CONSTRAINT fk_user_ig_lvl_log_level FOREIGN KEY (level_id) REFERENCES level(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """
    execute(query)
    print("✓ Created user_ig_lvl_log table")


def main():
    """Run migration"""
    print("Starting IG-based levels migration...")
    create_user_ig_lvl_link_table()
    create_user_ig_lvl_log_table()
    print("✓ Migration completed successfully!")


if __name__ == "__main__":
    main()

