# Leaderboard Speed-Up Plan

**Code:** `mulearnbackend/api/leaderboard/leaderboard_view.py`
**Frontend:** `mulearn-dashboard/src/features/leaderboard` (no change needed)
**Date:** 30 Sep 2026

A plan to make the four leaderboard endpoints behind `/dashboard/leaderboard` fast and cheap, using what we already have: Redis, Celery beat, and the cached karma columns on `organization`. It also fixes a few bugs found while reading the code.

---

## In short

| | |
|---|---|
| **Main cost today** | Every request runs a big GROUP BY over all students (and all karma logs for monthly) |
| **Main fix** | A cron rebuilds the boards twice a day into Redis; endpoints only read Redis |
| **Response shape** | Unchanged. Monthly college only gains a `title` field |
| **DB change** | One new index on `karma_activity_log` (optional, through db-scripts) |

---

## Where each endpoint stands

| Endpoint | What it does per request | Cache today | Cost |
|---|---|---|---|
| `students/` | Joins users, roles, org links; DISTINCT; sorts all students by wallet karma; returns 20 | None | Medium |
| `students-monthly/` | Joins users, roles, org links and *every* karma log row; SUM per user; sorts; plus 20 disk checks for profile pics | None | High |
| `college/` | Joins every college → every member → role → wallet; SUM + COUNT per college; sorts | None | High |
| `college-monthly/` | Joins every college → members → karma logs in range; SUM per college; sorts | `cache_page` 5 min | High, but cached |

Why these are slow: `karma_activity_log` has no index on `created_at`, so the monthly queries read the whole table. The all-time queries use `DISTINCT` or `GROUP BY` before `ORDER BY … LIMIT 20`, so MySQL must build and sort the full result before it can keep 20 rows. All four are public (no auth, no throttle), so repeated hits go straight to MySQL. Cost labels are from reading the queries; confirm them with `EXPLAIN ANALYZE` on a prod-sized copy before and after.

---

## Bugs found along the way

1. **[Bug] Monthly leaderboards will be empty in December.**
   `DateTimeUtils.get_start_and_end_of_previous_month()` computes the end date with `month % 12 + 1` but never moves the year. In December the end date becomes 31 Dec of the *previous* year, so the range is empty.

2. **[Bug] Monthly range drops karma at both ends.**
   The helper keeps the current time of day. At 3 PM, the range is "1st at 3 PM → last day at 3 PM", so karma from the morning of the 1st and the evening of the last day is missed. The name also says "previous month" but it returns the current month.
   **Fix for both:** replace it with `DateTimeUtils.get_current_month_range()` returning `(1st 00:00, next 1st 00:00)` with year rollover, and filter with `__gte` / `__lt`. Only these two views use the old helper.

3. **[Bug] Monthly college tab shows codes, not names.**
   `CollegeMonthlyLeaderboard` annotates `institution` but leaves `title` out of `.values()`. The frontend falls back to `item.code`.

4. **[Bug] A student with two college links can appear twice in monthly.**
   `institution` is part of the grouped values, so each college link makes its own row. The frontend already removes duplicates by `muid`, which hides this but can leave the list with fewer than 20 names.

5. **[Mismatch] Students and colleges count karma differently.**
   Student monthly counts all karma logs. College monthly counts only `appraiser_approved=True`. So a student's monthly karma can be higher than their college's share of it.

6. **[Mismatch] Profile pictures come from two sources.**
   All-time reads `user.profile_pic`. Monthly checks `user/profile/{id}.png` on local disk with `FileSystemStorage`, 20 times per request. If pictures are stored anywhere other than local disk, that check finds nothing.

---

## Changes per endpoint

### `GET /api/v1/leaderboard/college/` — biggest easy win

- **Today:** live SUM of wallet karma for every student of every college.
- **After:** read `cached_total_karma` / `cached_member_count`. The `refresh_org_aggregates` cron already keeps these fresh every 15 min, and `idx_organization_org_type_karma` already covers this exact sort.

```python
Organization.objects
    .filter(org_type=OrganizationType.COLLEGE.value)
    .order_by("-cached_total_karma")
    .values("id", "code", "title",
            total_students=F("cached_member_count"),
            total_karma=F("cached_total_karma"))[:20]
```

This reads 20 rows from an index. The numbers change a little: the cron counts all *verified* members, while today's query counts students in the Discord guild. See decision 1.

### `GET /api/v1/leaderboard/students/` — query rewrite

- **Today:** JOIN + DISTINCT, then sort all students by karma.
- **After:** walk `wallet` by karma (uses the existing `idx_wallet_karma`) and check role and college with `EXISTS`. No DISTINCT, so MySQL can stop after the first 20 matches.

```python
is_student = UserRoleLink.objects.filter(user_id=OuterRef("pk"), role__title=RoleType.STUDENT.value)
in_college = UserOrganizationLink.objects.filter(user_id=OuterRef("pk"), org__org_type=OrganizationType.COLLEGE.value)

User.objects
    .filter(exist_in_guild=True)
    .filter(Exists(is_student), Exists(in_college))
    .select_related("wallet_user")
    .order_by("-wallet_user__karma")[:20]   # + existing college Prefetch
```

### `GET /api/v1/leaderboard/students-monthly/` — rewrite + index + cache

- **Today:** joins students to all karma logs, then filters by date inside the SUM.
- **After:**
  - Sum karma logs *first*, only inside the month range, grouped by `user_id`; then keep the students.
  - Pick the college name in the prefetch (same as all-time), not in the GROUP BY.
  - Use `user.profile_pic` instead of 20 disk checks.

```python
KarmaActivityLog.objects
    .filter(created_at__gte=start, created_at__lt=next_month_start,
            user__exist_in_guild=True)
    .filter(Exists(is_student_for("user_id")), Exists(in_college_for("user_id")))
    .values("user_id")
    .annotate(total_karma=Sum("karma"))
    .order_by("-total_karma")[:20]
# then one query to load those 20 users + their college
```

### `GET /api/v1/leaderboard/college-monthly/` — rewrite + index + cache

- **Today:** org → members → karma logs join, SUM per college, `cache_page` 5 min.
- **After:**
  - Start from karma logs in range and group by the member's `org_id`.
  - Add `title` to the output (fixes the name bug).
  - Replace `cache_page` with the shared Redis cache below, so all four behave the same.

---

## Caching and cron

A new cron, `mu_celery/leaderboard_cron.py`, rebuilds the leaderboards **twice a day**: at 00:00 and 12:00 UTC (5:30 AM and 5:30 PM IST). It writes the results to Redis, and the endpoints only read from Redis.

```python
# mulearnbackend/settings.py → CELERY_BEAT_SCHEDULE
'refresh-leaderboards-cron': {
    'task': 'mu_celery.leaderboard_cron.refresh_leaderboards',
    'schedule': crontab(hour='0,12', minute=0),
},
```

| Redis key | TTL | Filled by |
|---|---|---|
| `leaderboard:students:all` | 13 h | Cron at 00:00 and 12:00 UTC |
| `leaderboard:students:month:2026-09` | 13 h | Cron at 00:00 and 12:00 UTC |
| `leaderboard:college:month:2026-09` | 13 h | Cron at 00:00 and 12:00 UTC |
| `leaderboard:college:all` | 15 min | View on miss. Reads the cached org columns, which the existing cron refreshes every 15 min, so it needs no new cron |

- **TTL is 13 h, one hour longer than the gap between runs.** The key is always replaced before it expires. If one cron run fails, the key expires an hour later and the next request rebuilds it live, so the board never goes empty.
- **Fallback on miss.** If a key is missing (first deploy, Redis restart, failed run), the view runs the query once and saves the result. The `cache.add` lock from `org_aggregates_cron.py` guards the cron against overlapping runs.
- **New month.** The 00:00 UTC run on the 1st fills the new month's key right away. Old month keys expire on their own after 13 h.
- **Data can be up to 12 hours old.** A student who earns karma sees their rank change after the next run, not right away. See decision 4.
- **Bounded keys.** Only four keys are live at a time, and nothing depends on user input, so Redis cannot grow without limit.
- **Abuse.** These endpoints are public with no throttle. After this change a flood of requests only reads Redis.

---

## Database index

```sql
-- db-scripts/alter/alter-1.99.sql
ALTER TABLE karma_activity_log
  ADD KEY idx_kal_created_user (created_at, user_id, karma, appraiser_approved),
  ALGORITHM=INPLACE, LOCK=NONE;
```

A covering index for the monthly range: MySQL reads only this month's rows and never goes to the table. With the cron running only twice a day this is less urgent, but it keeps each run short and makes the live fallback on a cache miss fast as the table grows. Models are `managed = False`, so this lands in db-scripts and `latest.sql`, not in Django `Meta`. Run it off-peak, since the table is large.

---

## Decisions needed

### 1. Which members count for the college all-time board?
Today it counts students in the Discord guild. The cached columns count all verified members.
**Recommend:** use the cached columns as they are. The organisation list already sorts on them, so the numbers will agree across pages. If product wants "students only", change the cron once and every page follows.

### 2. Should student monthly count only appraiser-approved karma?
**Recommend:** yes, the same as college monthly, so the two boards add up.

### 3. Which timezone marks the start of a month?
Today it is UTC, so the board resets at 5:30 AM IST on the 1st.
**Recommend:** keep UTC unless someone has asked for IST. It matches the rest of `DateTimeUtils`.

### 4. Is up to 12 hours old OK for the leaderboard?
Running the cron twice a day keeps DB load lowest, but a rank change can take up to 12 hours to show. Students often check the board right after finishing a task.
**Recommend:** start with twice a day. If people complain about slow updates, move the cron to every hour. It is a one-line change to the schedule and the TTL.

---

## Files touched

| File | Change |
|---|---|
| `api/leaderboard/leaderboard_view.py` | Query rewrites, cache helper, remove `cache_page` |
| `utils/utils.py` | New month-range helper, remove the old one |
| `mu_celery/leaderboard_cron.py` | New task that rebuilds the three boards into Redis |
| `mulearnbackend/settings.py` | Beat entry: 00:00 and 12:00 UTC |
| `db-scripts/alter/alter-1.99.sql`, `latest.sql` | New index |
| `mulearn-dashboard` | None. Response shapes stay the same |

**Tests:** add `api/leaderboard/tests/` using the same conftest pattern as `api/dashboard/projects/tests/`. Cover the month range (including December), the top-20 order, the no-duplicate rule, and the cache hit path.
