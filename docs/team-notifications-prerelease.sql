-- Run on production by someone with access before deploying; verify real team members first.
-- Read-only. Lists holders of Admins, Fellow or Associate whose link would be refused by the new gate (verified = 0 or is_active = 0).
SELECT u.muid,
       u.full_name,
       r.title AS role_title,
       url.verified,
       url.is_active,
       url.created_at
FROM user_role_link AS url
JOIN `user` AS u ON u.id = url.user_id
JOIN role AS r ON r.id = url.role_id
WHERE BINARY r.title IN ('Admins', 'Fellow', 'Associate')
  AND (url.verified = 0 OR url.is_active = 0)
ORDER BY r.title, u.full_name;
