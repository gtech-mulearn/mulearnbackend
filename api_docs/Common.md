# Common API Reference

## Learning Circle

### Details
**Endpoint:** `/api/v1/common/lc/<str:circle_id>/`
**Method:** `GET`
**Brief:** Get details of a specific learning circle.

### List
**Endpoint:** `/api/v1/common/lc/`
**Method:** `GET`
**Brief:** List all learning circles.
**Query Params:** `ig`, `org`, `district`

### Dashboard
**Endpoint:** `/api/v1/common/lc/dashboard/`
**Method:** `GET`
**Brief:** Get dashboard stats for learning circles.
**Query Params:** `date`

### Report
**Endpoint:** `/api/v1/common/lc/report/`
**Method:** `GET`
**Brief:** Get report of student enrollment in learning circles.
**Query Params:** `date`

### Report Download
**Endpoint:** `/api/v1/common/lc/report/download/`
**Method:** `GET`
**Brief:** Download LC report as CSV.

### College Wise Report
**Endpoint:** `/api/v1/common/lc/college/`
**Method:** `GET`
**Brief:** Get college-wise learning circle stats.
**Query Params:** `date`

### College Wise Report CSV
**Endpoint:** `/api/v1/common/lc/college/csv/`
**Method:** `GET`
**Brief:** Download college-wise LC report as CSV.

### Enrollment
**Endpoint:** `/api/v1/common/lc/enrollment/`
**Method:** `GET`
**Brief:** Get enrollment details for learning circles.

### Enrollment CSV
**Endpoint:** `/api/v1/common/lc/enrollment/csv/`
**Method:** `GET`
**Brief:** Download enrollment details as CSV.

## Analytics & Counts

### Global Counts
**Endpoint:** `/api/v1/common/global-count/`
**Method:** `GET`
**Brief:** Get global counts of members, orgs, interest groups, etc.

### GTA Sandshore
**Endpoint:** `/api/v1/common/gta-sandshore/`
**Method:** `GET`
**Brief:** Get GTA Sandshore rank data from Devfolio.

### User Profile Pic
**Endpoint:** `/api/v1/common/profile-pic/<str:muid>/`
**Method:** `GET`
**Brief:** Get profile picture of a user by MUID.

## Lists

### List Interest Groups
**Endpoint:** `/api/v1/common/list/ig/`
**Method:** `GET`
**Brief:** List all interest groups.

### List Top IG Users
**Endpoint:** `/api/v1/common/list/top-ig-users/`
**Method:** `GET`
**Brief:** Get top 100 users for specific IGs.
**Query Params:** `ig_name` (list)

### List All Level Info
**Endpoint:** `/api/v1/common/list-all-level-info/`
**Method:** `GET`
**Brief:** List all levels and their tasks.

### Beken Leaderboard
**Endpoint:** `/api/v1/common/hero/`
**Method:** `GET`
**Brief:** Get top 100 users leaderboard (excluding mentors/enablers).

## Location Lists

### List Colleges
**Endpoint:** `/api/v1/common/lc/college/list/`
**Method:** `GET`
**Brief:** List colleges in a district.
**Query Params:** `district_id`

### List Districts
**Endpoint:** `/api/v1/common/lc/district/list/`
**Method:** `GET`
**Brief:** List districts in a state.
**Query Params:** `state_id`

### List States
**Endpoint:** `/api/v1/common/lc/state/list/`
**Method:** `GET`
**Brief:** List states in a country.
**Query Params:** `country_id`

### List Countries
**Endpoint:** `/api/v1/common/lc/country/list/`
**Method:** `GET`
**Brief:** List all countries.
