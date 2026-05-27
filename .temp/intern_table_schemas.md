# Intern Dashboard — Table Schemas 

All tables use `managed = False` in Django ORM. Create manually via SQL DDL.

---

## 1. `intern_enrollment`

Tracks intern enrollment, team assignment, and status lifecycle.

```sql
CREATE TABLE `intern_enrollment` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `team` varchar(75) NOT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'ACTIVE',
  `enrolled_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_enrollment_user` (`user_id`),
  KEY `idx_enrollment_status` (`status`),
  KEY `idx_enrollment_team` (`team`),
  CONSTRAINT `fk_enroll_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_enroll_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_enroll_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Status values:** `ACTIVE`, `AT_RISK`, `ON_LEAVE`, `INACTIVE`
**Team values:** `Frontend Guild`, `Backend Guild`, `Design Guild`, `Mobile Guild`

---

## 2. `intern_daily_timesheet`

Stores one daily timesheet entry per user per day.

```sql
CREATE TABLE `intern_daily_timesheet` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `entry_date` date NOT NULL,
  `task_id` varchar(36) DEFAULT NULL,
  `category` varchar(50) NOT NULL,
  `description` text NOT NULL,
  `hours` decimal(4,2) NOT NULL,
  `blockers` text,
  `task_status` varchar(20) NOT NULL DEFAULT 'NOT_STARTED',
  `remark` text,
  `end_of_day_note` text,
  `edit_reason` varchar(300) DEFAULT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'submitted',
  `karma_awarded` int NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_timesheet_user_date` (`user_id`, `entry_date`),
  KEY `idx_timesheet_task` (`task_id`),
  CONSTRAINT `fk_ts_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ts_task` FOREIGN KEY (`task_id`) REFERENCES `intern_task` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_ts_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ts_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Duplicate prevention:** `UNIQUE(user_id, entry_date)`
**Note:** `hours` = `decimal(4,2)` — max 99.99. Safe for daily entries.
**New columns:** `task_id`, `task_status`, `remark`, `end_of_day_note`, `edit_reason`

---

## 3. `intern_weekly_review`

Stores one weekly review per user per ISO week.

```sql
CREATE TABLE `intern_weekly_review` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `iso_year` smallint NOT NULL,
  `iso_week` tinyint NOT NULL,
  `week_start_date` date NOT NULL,
  `week_end_date` date NOT NULL,
  `team` varchar(75) NOT NULL,
  `is_on_leave` tinyint(1) NOT NULL DEFAULT '0',
  `tasks_assigned` text NOT NULL,
  `tasks_completed` text NOT NULL,
  `weekly_review` text NOT NULL,
  `task_remarks` json DEFAULT NULL,
  `hours_committed` varchar(20) NOT NULL,
  `blockers` text,
  `leave_days` text,
  `suggestions` text,
  `is_late` tinyint(1) NOT NULL DEFAULT '0',
  `status` varchar(15) NOT NULL DEFAULT 'submitted',
  `karma_awarded` int NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_review_user_week` (`user_id`, `iso_year`, `iso_week`),
  CONSTRAINT `fk_wr_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_wr_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_wr_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Duplicate prevention:** `UNIQUE(user_id, iso_year, iso_week)`
**New columns:** `week_start_date`, `week_end_date`, `weekly_review` (replaces `works_done`), `task_remarks`, `suggestions`, `is_late`

---

## 4. `intern_task`

Admin-assigned work items with complexity weights, deadlines, and status tracking.

```sql
CREATE TABLE `intern_task` (
  `id` varchar(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text NOT NULL,
  `assigned_to` varchar(36) NOT NULL,
  `team` varchar(75) NOT NULL,
  `category` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'NOT_STARTED',
  `complexity` varchar(10) NOT NULL DEFAULT 'LOW',
  `deadline` date NOT NULL,
  `iso_week` tinyint NOT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_task_assigned` (`assigned_to`, `status`),
  KEY `idx_task_team_week` (`team`, `iso_week`),
  CONSTRAINT `fk_task_assigned` FOREIGN KEY (`assigned_to`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Status values:** `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `WAITING_FOR_REVIEW`
**Complexity values + weights:** `LOW`=1, `MEDIUM`=2, `HIGH`=3, `CRITICAL`=5

---

## 5. `intern_leave_request`

Leave requests with type, date range, approval workflow, and quota enforcement.

```sql
CREATE TABLE `intern_leave_request` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `leave_type` varchar(20) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `duration_days` smallint NOT NULL,
  `reason` text NOT NULL,
  `status` varchar(15) NOT NULL DEFAULT 'PENDING',
  `reviewed_by` varchar(36) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `review_note` varchar(300) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_leave_user_status` (`user_id`, `status`),
  KEY `idx_leave_dates` (`start_date`, `end_date`),
  CONSTRAINT `fk_leave_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_leave_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

**Status values:** `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`
**Leave types + caps:** `SICK`=2/mo, `CASUAL`=1/mo, `EMERGENCY`=no cap, `WFH`=2/week

---

## Seed Data — TaskList Entries

Required `task_list` rows for the intern karma pipeline:

```sql
INSERT INTO `task_list` (`id`, `hashtag`, `title`, `karma`, `active`, `type_id`, `updated_by`, `created_by`)
VALUES
  (UUID(), '#intern-daily-log',     'Intern Daily Log Submission',   10,  1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>'),
  (UUID(), '#intern-weekly-review', 'Intern Weekly Review',          50,  1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>'),
  (UUID(), '#intern-streak-7',      'Intern 7-Day Streak Bonus',     20,  1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>'),
  (UUID(), '#intern-streak-14',     'Intern 14-Day Streak Bonus',    50,  1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>'),
  (UUID(), '#intern-streak-30',     'Intern 30-Day Streak Bonus',    100, 1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>'),
  (UUID(), '#intern-streak-60',     'Intern 60-Day Streak Bonus',    200, 1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>'),
  (UUID(), '#intern-streak-90',     'Intern 90-Day Streak Bonus',    500, 1, '<task_type_id>', '<admin_user_id>', '<admin_user_id>');
```

> Replace `<task_type_id>` and `<admin_user_id>` with actual values from the database before running.

---

## Table Creation Order

Due to FK dependencies, create tables in this order:
1. `intern_enrollment` (no cross-table FK)
2. `intern_task` (no cross-table FK)
3. `intern_daily_timesheet` (FK → `intern_task`)
4. `intern_weekly_review` (no cross-table FK)
5. `intern_leave_request` (no cross-table FK)
6. `task_list` seed data (INSERT)
