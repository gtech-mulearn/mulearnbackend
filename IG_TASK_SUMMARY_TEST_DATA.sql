-- IG Task Summary API Test Data

-- Step 1: Create test users
-- Note: Adjust the UUIDs and values as needed for your database

INSERT INTO user (id, discord_id, muid, full_name, email, password, mobile, admin, exist_in_guild, created_at) VALUES
('user-001', 'discord-001', 'alicejohnson@mulearn', 'Alice Johnson', 'alice@example.com', 'hashed_pwd', '+919876543210', 0, 1, NOW()),
('user-002', 'discord-002', 'bobsmith@mulearn', 'Bob Smith', 'bob@example.com', 'hashed_pwd', '+919876543211', 0, 1, NOW()),
('user-003', 'discord-003', 'carolwhite@mulearn', 'Carol White', 'carol@example.com', 'hashed_pwd', '+919876543212', 0, 1, NOW()),
('user-004', 'discord-004', 'davidbrown@mulearn', 'David Brown', 'david@example.com', 'hashed_pwd', '+919876543213', 0, 1, NOW()),
('user-005', 'discord-005', 'evajones@mulearn', 'Eva Jones', 'eva@example.com', 'hashed_pwd', '+919876543214', 0, 1, NOW()),
('admin-001', 'discord-admin', 'admin@mulearn', 'Admin User', 'admin@example.com', 'hashed_pwd', '+919876543200', 1, 1, NOW());

-- Step 2: Create a test Interest Group
INSERT INTO interest_group (id, name, code, icon, category, status, about, created_by, updated_by, created_at, updated_at) VALUES
('ig-test-001', 'Web Development', 'WEB', '🌐', 'coder', 'active', 'Learn web development technologies', 'admin-001', 'admin-001', NOW(), NOW());

-- Step 3: Create test TaskTypes
INSERT INTO task_type (id, title, created_by, updated_by, created_at, updated_at) VALUES
('task-type-001', 'Task', 'admin-001', 'admin-001', NOW(), NOW()),
('task-type-002', 'Assignment', 'admin-001', 'admin-001', NOW(), NOW());

-- Step 4: Create test Channels
INSERT INTO channel (id, name, discord_id, created_by, updated_by, created_at, updated_at) VALUES
('channel-001', 'web-dev-tasks', 'discord-channel-001', 'admin-001', 'admin-001', NOW(), NOW());

-- Step 5: Create test Tasks (associated with the IG)
INSERT INTO task_list (id, hashtag, title, karma, channel_id, type_id, ig_id, active, usage_count, created_by, updated_by, created_at, updated_at) VALUES
('task-001', 'html-basics', 'Learn HTML Basics', 100, 'channel-001', 'task-type-001', 'ig-test-001', 1, 1, 'admin-001', 'admin-001', '2025-01-15 10:00:00', '2025-01-15 10:00:00'),
('task-002', 'css-styling', 'Master CSS Styling', 120, 'channel-001', 'task-type-001', 'ig-test-001', 1, 1, 'admin-001', 'admin-001', '2025-01-20 10:00:00', '2025-01-20 10:00:00'),
('task-003', 'javascript-basics', 'JavaScript Fundamentals', 150, 'channel-001', 'task-type-001', 'ig-test-001', 1, 1, 'admin-001', 'admin-001', '2025-02-01 10:00:00', '2025-02-01 10:00:00'),
('task-004', 'react-intro', 'Introduction to React', 200, 'channel-001', 'task-type-002', 'ig-test-001', 1, 1, 'admin-001', 'admin-001', '2025-02-10 10:00:00', '2025-02-10 10:00:00'),
('task-005', 'api-design', 'RESTful API Design', 180, 'channel-001', 'task-type-001', 'ig-test-001', 1, 1, 'admin-001', 'admin-001', '2025-02-20 10:00:00', '2025-02-20 10:00:00');

-- Step 6: Create Karma Activity Logs (task completions)
-- Alice Johnson: 540 karma (top contributor)
INSERT INTO karma_activity_log (id, karma, task_id, user_id, peer_approved, appraiser_approved, created_by, updated_by, created_at, updated_at) VALUES
('kal-001', 100, 'task-001', 'user-001', 1, 1, 'user-001', 'user-001', '2025-01-16 10:30:00', '2025-01-16 10:30:00'),
('kal-002', 120, 'task-002', 'user-001', 1, 1, 'user-001', 'user-001', '2025-01-21 14:15:00', '2025-01-21 14:15:00'),
('kal-003', 150, 'task-003', 'user-001', 1, 1, 'user-001', 'user-001', '2025-02-02 09:00:00', '2025-02-02 09:00:00'),
('kal-004', 170, 'task-004', 'user-001', 1, 1, 'user-001', 'user-001', '2025-02-11 11:30:00', '2025-02-11 11:30:00'),

-- Bob Smith: 480 karma (2nd top contributor)
('kal-005', 100, 'task-001', 'user-002', 1, 1, 'user-002', 'user-002', '2025-01-17 11:45:00', '2025-01-17 11:45:00'),
('kal-006', 120, 'task-002', 'user-002', 1, 1, 'user-002', 'user-002', '2025-01-22 15:20:00', '2025-01-22 15:20:00'),
('kal-007', 150, 'task-003', 'user-002', 1, 1, 'user-002', 'user-002', '2025-02-03 10:10:00', '2025-02-03 10:10:00'),
('kal-008', 110, 'task-004', 'user-002', 1, 1, 'user-002', 'user-002', '2025-02-12 13:45:00', '2025-02-12 13:45:00'),

-- Carol White: 420 karma (3rd top contributor)
('kal-009', 100, 'task-001', 'user-003', 1, 1, 'user-003', 'user-003', '2025-01-18 12:00:00', '2025-01-18 12:00:00'),
('kal-010', 120, 'task-002', 'user-003', 1, 1, 'user-003', 'user-003', '2025-01-23 16:30:00', '2025-01-23 16:30:00'),
('kal-011', 200, 'task-004', 'user-003', 1, 1, 'user-003', 'user-003', '2025-02-13 14:00:00', '2025-02-13 14:00:00'),

-- David Brown: 350 karma (4th top contributor)
('kal-012', 150, 'task-003', 'user-004', 1, 1, 'user-004', 'user-004', '2025-02-04 11:20:00', '2025-02-04 11:20:00'),
('kal-013', 200, 'task-004', 'user-004', 1, 1, 'user-004', 'user-004', '2025-02-14 15:10:00', '2025-02-14 15:10:00'),

-- Eva Jones: 280 karma (5th top contributor)
('kal-014', 100, 'task-001', 'user-005', 1, 1, 'user-005', 'user-005', '2025-01-19 13:15:00', '2025-01-19 13:15:00'),
('kal-015', 180, 'task-005', 'user-005', 1, 1, 'user-005', 'user-005', '2025-02-21 10:00:00', '2025-02-21 10:00:00');

-- Summary:
-- Total tasks completed: 15
-- Total karma awarded: 3,720
-- Unique contributors: 5
-- Top 5 contributors:
--   1. Alice Johnson: 540 karma
--   2. Bob Smith: 480 karma
--   3. Carol White: 420 karma
--   4. David Brown: 350 karma
--   5. Eva Jones: 280 karma
