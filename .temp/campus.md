# Campus Dashboard Comprehensive API Spec

Base path: `/api/v1/dashboard/campus/`

Related enabler path: `/api/v1/dashboard/enabler/`

Authentication: JWT bearer token required. Campus endpoints are generally available to `Campus Lead` and `Lead Enabler` unless explicitly marked public or read-only.

Common success envelope:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": {}
}
```

Common failure envelope:

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Validation failed"],
    "error_code": "VALIDATION_ERROR"
  },
  "response": {}
}
```

## Endpoint Summary

| Endpoint | Method | Usage Scenario |
|---|---:|---|
| `/api/v1/dashboard/campus/home-summary/` | `GET` | Campus lead sees campus health, karma, active members, circles, and recent activity. |
| `/api/v1/dashboard/campus/showcase/` | `GET` | Campus lead views public college page content. |
| `/api/v1/dashboard/campus/showcase/` | `PATCH` | Campus lead updates public college page content. |
| `/api/v1/dashboard/campus/participation/ig/` | `GET` | Campus lead reviews Interest Group participation. |
| `/api/v1/dashboard/campus/participation/circles/` | `GET` | Campus lead reviews Learning Circle participation. |
| `/api/v1/dashboard/campus/participation/programs/` | `GET` | Campus lead reviews program participation. |
| `/api/v1/dashboard/campus/students/<muid>/activity/` | `GET` | Campus lead views one student's complete activity timeline. |
| `/api/v1/dashboard/campus/learning-initiatives/summary/` | `GET` | Campus lead views program-specific summary for Top100, Launchpad, In50Hrs, etc. |
| `/api/v1/dashboard/campus/events/analytics/` | `GET` | Campus lead reviews event reach, attendance, and impact. |
| `/api/v1/dashboard/campus/campus-details/` | `GET` | Campus lead views campus metadata, lead names, and campus stats. |
| `/api/v1/dashboard/campus/student-details/` | `GET` | Campus lead lists all students from the campus. |
| `/api/v1/dashboard/campus/<org_id>/leaderboard/` | `GET` | User views campus leaderboard with filters. |
| `/api/v1/dashboard/campus/<org_id>/karma-by-cluster/` | `GET` | User views campus karma grouped by IG category or cluster. |
| `/api/v1/dashboard/campus/ig-chapters/` | `GET` | Campus lead lists campus IG chapters. |
| `/api/v1/dashboard/campus/ig-chapters/` | `POST` | Campus lead creates a campus IG chapter. |
| `/api/v1/dashboard/campus/social-links/` | `PUT` | Campus lead upserts public social links. |
| `/api/v1/dashboard/campus/events/` | `GET` | Campus lead lists campus-scoped events. |
| `/api/v1/dashboard/enabler/home-summary/` | `GET` | Enabler sees assigned campus health and action priorities. |
| `/api/v1/dashboard/enabler/campuses/` | `GET` | Enabler lists assigned campuses. |
| `/api/v1/dashboard/enabler/campuses/<campus_id>/review/` | `GET` | Enabler reviews one assigned campus. |
| `/api/v1/dashboard/enabler/campuses/<campus_id>/notes/` | `POST` | Enabler adds review notes or follow-up items. |
| `/api/v1/dashboard/enabler/reports/` | `GET` | Enabler views or exports assigned-campus reports. |

## 1. Campus Home Summary

Endpoint: `GET /api/v1/dashboard/campus/home-summary/`

Usage: First screen for campus leads and lead enablers. Shows campus identity, stat cards, member funnel, circle health, and recent activity.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `7d`, `30d`, `60d`, `90d`; default `30d`. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus dashboard summary fetched successfully"]
  },
  "response": {
    "campus": {
      "org_id": "org-uuid",
      "college_name": "Example College of Engineering",
      "campus_code": "ECE001",
      "campus_zone": "South Zone"
    },
    "stat_cards": [
      {
        "key": "active_members",
        "label": "Active members",
        "value": 180,
        "delta": 18,
        "delta_type": "increase",
        "period": "30d"
      },
      {
        "key": "total_karma",
        "label": "Karma",
        "value": 45200,
        "delta": 4800,
        "delta_type": "increase",
        "period": "30d"
      }
    ],
    "member_funnel": {
      "max": 312,
      "stages": [
        {
          "key": "registered",
          "label": "Registered",
          "count": 312,
          "percentage": 100
        },
        {
          "key": "active",
          "label": "Active",
          "count": 180,
          "percentage": 57.69
        }
      ]
    },
    "circle_health": [
      {
        "circle_id": "circle-uuid",
        "circle_name": "Python Builders",
        "ig_name": "Python",
        "member_count": 24,
        "sessions_per_month": 3,
        "status": "active"
      }
    ],
    "recent_activity": [
      {
        "id": "activity-uuid",
        "type": "circle_created",
        "title": "Python Builders created",
        "created_at": "2026-05-25T10:00:00+05:30"
      }
    ]
  }
}
```

## 2. Campus Showcase

Endpoint: `GET /api/v1/dashboard/campus/showcase/`

Usage: Campus lead views public college page content: about, hero image, highlights, gallery, testimonials, social links, and contact details.

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus showcase fetched successfully"]
  },
  "response": {
    "org_id": "org-uuid",
    "college_name": "Example College of Engineering",
    "about": "A vibrant campus community building peer-led learning.",
    "hero_image": "https://cdn.example.com/campus-hero.jpg",
    "highlights": [
      {
        "title": "Top 10 Campus",
        "description": "Ranked in the monthly campus leaderboard."
      }
    ],
    "gallery": [
      "https://cdn.example.com/event-1.jpg"
    ],
    "testimonials": [
      {
        "name": "Arjun Menon",
        "role": "Campus Lead",
        "quote": "Learning circles helped us activate new learners."
      }
    ],
    "social_links": [
      {
        "platform": "instagram",
        "url": "https://instagram.com/example_campus"
      }
    ],
    "contact": {
      "email": "campuslead@example.edu",
      "phone": "+919999999999"
    },
    "updated_at": "2026-05-28T09:00:00+05:30"
  }
}
```

Endpoint: `PATCH /api/v1/dashboard/campus/showcase/`

Usage: Campus lead updates the public showcase page.

Request body:

```json
{
  "about": "A student-led technology community focused on learning by doing.",
  "hero_image": "https://cdn.example.com/new-campus-hero.jpg",
  "highlights": [
    {
      "title": "50000+ Karma",
      "description": "Generated by campus learners this year."
    }
  ],
  "gallery": [
    "https://cdn.example.com/hackathon.jpg",
    "https://cdn.example.com/meetup.jpg"
  ],
  "testimonials": [
    {
      "name": "Riya Sharma",
      "role": "Learner",
      "quote": "muLearn helped me build real projects."
    }
  ],
  "contact": {
    "email": "mulearn@example.edu",
    "phone": "+919999999999"
  }
}
```

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus showcase updated successfully"]
  },
  "response": {
    "org_id": "org-uuid",
    "updated_at": "2026-05-28T09:15:00+05:30"
  }
}
```

## 3. IG Participation

Endpoint: `GET /api/v1/dashboard/campus/participation/ig/`

Usage: Campus lead checks Interest Group participation, active learners, inactive learners, chapter health, and top IGs.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `30d`, `90d`, `all`; default `30d`. |
| `ig_id` | string | No | Filter by one IG. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["IG participation fetched successfully"]
  },
  "response": {
    "summary": {
      "total_igs": 12,
      "active_igs": 8,
      "students_with_ig": 220,
      "students_without_ig": 92
    },
    "data": [
      {
        "ig_id": "ig-uuid",
        "ig_name": "Web Development",
        "member_count": 74,
        "active_members": 35,
        "karma_generated": 12000,
        "tasks_completed": 180,
        "campus_chapter_status": "active",
        "lead": {
          "user_id": "user-uuid",
          "full_name": "Arun Dev",
          "muid": "arun-dev@mulearn"
        }
      }
    ]
  }
}
```

## 4. Learning Circle Participation

Endpoint: `GET /api/v1/dashboard/campus/participation/circles/`

Usage: Campus lead reviews Learning Circle health, meeting frequency, members, attendance, and report completion.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `30d`, `90d`, `all`; default `30d`. |
| `status` | string | No | `active`, `slow`, `inactive`. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Circle participation fetched successfully"]
  },
  "response": {
    "summary": {
      "total_circles": 18,
      "active_circles": 10,
      "inactive_circles": 4,
      "total_members": 210,
      "meetings_this_period": 42
    },
    "data": [
      {
        "circle_id": "circle-uuid",
        "circle_name": "Python Builders",
        "ig_name": "Python",
        "lead": {
          "full_name": "Anjana K",
          "muid": "anjana-k@mulearn"
        },
        "member_count": 24,
        "meetings_count": 5,
        "avg_attendance": 18,
        "report_submission_rate": 80,
        "status": "active"
      }
    ]
  }
}
```

## 5. Program Participation

Endpoint: `GET /api/v1/dashboard/campus/participation/programs/`

Usage: Campus lead reviews participation in programs such as Top100, Launchpad, In50Hrs, Mutate, Permute, and Amuse.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `program` | string | No | `top100`, `launchpad`, `in50hrs`, `mutate`, `permute`, `amuse`. |
| `period` | string | No | `30d`, `90d`, `all`. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Program participation fetched successfully"]
  },
  "response": {
    "summary": {
      "total_enrolled": 148,
      "active_participants": 96,
      "completed": 32,
      "completion_rate": 21.62
    },
    "programs": [
      {
        "program": "launchpad",
        "enrolled": 80,
        "active": 55,
        "completed": 20,
        "eligible": 14,
        "rank": 5
      },
      {
        "program": "top100",
        "enrolled": 68,
        "active": 41,
        "completed": 12,
        "rank": 8
      }
    ]
  }
}
```

## 6. Student Activity

Endpoint: `GET /api/v1/dashboard/campus/students/<muid>/activity/`

Usage: Campus lead opens one student profile and reviews complete campus-relevant activity: IGs, circles, events, programs, karma, badges, submissions, and timeline.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `30d`, `90d`, `all`; default `90d`. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Student activity fetched successfully"]
  },
  "response": {
    "student": {
      "id": "user-uuid",
      "full_name": "Riya Sharma",
      "muid": "riya-sharma@mulearn",
      "email": "riya@example.com",
      "department": "Computer Science",
      "graduation_year": "2026",
      "karma": 3200,
      "level": {
        "name": "Explorer",
        "level_order": 4
      }
    },
    "ig_activity": [
      {
        "ig_id": "ig-uuid",
        "ig_name": "Web Development",
        "tasks_completed": 24,
        "karma_generated": 1200
      }
    ],
    "learning_circles": [
      {
        "circle_id": "circle-uuid",
        "circle_name": "Python Builders",
        "role": "member",
        "meetings_attended": 6
      }
    ],
    "events": [
      {
        "event_id": "event-uuid",
        "title": "Backend Bootcamp",
        "status": "attended",
        "attended_at": "2026-05-18T09:30:00+05:30"
      }
    ],
    "programs": [
      {
        "program": "launchpad",
        "status": "active",
        "progress_percentage": 60
      }
    ],
    "badges": [
      {
        "id": "achievement-uuid",
        "title": "API Builder",
        "issued_at": "2026-05-20T12:00:00+05:30"
      }
    ],
    "karma_history": [
      {
        "date": "2026-05-20",
        "karma": 200,
        "source": "#django-api"
      }
    ]
  }
}
```

## 7. Learning Initiative Summary

Endpoint: `GET /api/v1/dashboard/campus/learning-initiatives/summary/`

Usage: Campus lead views a focused summary for one initiative. This should work for Top100, Launchpad, In50Hrs, Mutate, Permute, Amuse, and future programs.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `program` | string | Yes | `top100`, `launchpad`, `in50hrs`, `mutate`, `permute`, `amuse`. |
| `cohort_id` | string | No | Optional cohort/program batch. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Learning initiative summary fetched successfully"]
  },
  "response": {
    "program": "launchpad",
    "cohort_id": "cohort-uuid",
    "campus": {
      "org_id": "org-uuid",
      "college_name": "Example College of Engineering"
    },
    "summary": {
      "registered": 120,
      "active": 82,
      "completed_level_1": 60,
      "completed_level_2": 42,
      "completed_level_3": 24,
      "eligible_for_hiring": 14,
      "applications_submitted": 38,
      "hired": 3
    },
    "leaderboard": {
      "campus_rank": 5,
      "top_students": [
        {
          "muid": "riya-sharma@mulearn",
          "full_name": "Riya Sharma",
          "score": 920
        }
      ]
    }
  }
}
```

## 8. Campus Event Analytics

Endpoint: `GET /api/v1/dashboard/campus/events/analytics/`

Usage: Campus lead reviews event performance across campus events: registrations, attendance, interest, collaborations, and completion rate.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `30d`, `90d`, `all`; default `90d`. |
| `scope` | string | No | `campus`, `campus_ig`, `all`. |
| `event_id` | string | No | If provided, return analytics for one event. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus event analytics fetched successfully"]
  },
  "response": {
    "summary": {
      "total_events": 18,
      "published_events": 14,
      "completed_events": 10,
      "cancelled_events": 1,
      "total_interests": 860,
      "total_registrations": 640,
      "total_attendance": 420,
      "attendance_rate": 65.62
    },
    "by_event": [
      {
        "event_id": "event-uuid",
        "title": "Backend Bootcamp",
        "status": "completed",
        "interest_count": 120,
        "registrations": 90,
        "attendance": 72,
        "attendance_rate": 80,
        "collaborators": [
          {
            "type": "collab_ig",
            "name": "Web Development"
          }
        ]
      }
    ],
    "by_tag": [
      {
        "tag": "backend",
        "event_count": 4,
        "attendance": 180
      }
    ]
  }
}
```

## 9. Campus Details

Endpoint: `GET /api/v1/dashboard/campus/campus-details/`

Usage: Campus lead views campus metadata, lead names, rank, karma stats, member count, and public social links.

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": {
    "org_id": "org-uuid",
    "college_name": "Example College of Engineering",
    "campus_code": "ECE001",
    "campus_zone": "South Zone",
    "campus_level": 3,
    "total_karma": 45200,
    "total_members": 312,
    "active_members": 180,
    "rank": 5,
    "lead": {
      "campus_lead": "Arjun Menon",
      "enabler": "Priya Nair"
    },
    "karma_last_7_days": 1200,
    "karma_last_30_days": 4800,
    "active_ig_count": 7,
    "social_links": [
      {
        "id": "social-link-uuid",
        "platform": "instagram",
        "url": "https://instagram.com/example_campus"
      }
    ]
  }
}
```

## 10. Student Details

Endpoint: `GET /api/v1/dashboard/campus/student-details/`

Usage: Campus lead lists students in the campus with filters for alumni, department, level, karma, and search.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `is_alumni` | boolean | No | `true` or `false`. |
| `department_id` | string | No | Filter by department. |
| `level_order_min` | integer | No | Minimum level order. |
| `search` | string | No | Search name, email, muID. |
| `pageIndex` | integer | No | Page number. |
| `perPage` | integer | No | Items per page. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": {
    "data": [
      {
        "user_id": "user-uuid",
        "full_name": "Rahul Krishna",
        "muid": "rahul-krishna@mulearn",
        "email": "rahul@example.com",
        "mobile": "9876543210",
        "karma": 3400,
        "rank": 1,
        "level": "Pathfinder",
        "join_date": "2026-01-10T10:00:00+05:30",
        "last_karma_gained": "2026-05-20T14:30:00+05:30",
        "department": "Computer Science",
        "graduation_year": "2026",
        "is_alumni": false
      }
    ],
    "pagination": {
      "count": 312,
      "totalPages": 16,
      "isFirst": true,
      "isLast": false
    }
  }
}
```

## 11. Campus Leaderboard

Endpoint: `GET /api/v1/dashboard/campus/<org_id>/leaderboard/`

Usage: User views ranked campus students with optional filters by pass-out year, IG, category, and alumni status.

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": {
    "data": [
      {
        "user_id": "user-uuid",
        "full_name": "Rahul Krishna",
        "muid": "rahul-krishna@mulearn",
        "karma": 3400,
        "rank": 1,
        "level": "Pathfinder",
        "department": "Computer Science",
        "graduation_year": "2026",
        "is_alumni": false,
        "ig_count": 3
      }
    ],
    "pagination": {
      "count": 312,
      "totalPages": 16,
      "isFirst": true,
      "isLast": false
    }
  }
}
```

## 12. Campus Karma By Cluster

Endpoint: `GET /api/v1/dashboard/campus/<org_id>/karma-by-cluster/`

Usage: User views campus karma distribution by IG cluster/category.

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": {
    "technology": {
      "total_karma": 28400,
      "member_count": 145
    },
    "design": {
      "total_karma": 9200,
      "member_count": 62
    },
    "unclustered": {
      "total_karma": 7600,
      "member_count": 105
    }
  }
}
```

## 13. Campus IG Chapters

Endpoint: `GET /api/v1/dashboard/campus/ig-chapters/`

Usage: Campus lead lists active IG chapters for the campus.

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": [
    {
      "id": "chapter-uuid",
      "ig_id": "ig-uuid",
      "ig_name": "Python",
      "ig_code": "python",
      "lead_id": "user-uuid",
      "lead_name": "Arun Dev",
      "description": "Our campus Python chapter",
      "is_active": true,
      "campus_ig_member_count": 24
    }
  ]
}
```

Endpoint: `POST /api/v1/dashboard/campus/ig-chapters/`

Usage: Campus lead creates a new campus IG chapter and optionally assigns a lead.

Request body:

```json
{
  "ig": "ig-uuid",
  "description": "Our campus Python chapter",
  "lead": "user-uuid"
}
```

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["IG Chapter created successfully"]
  },
  "response": {
    "chapter_id": "chapter-uuid",
    "ig_id": "ig-uuid",
    "lead_id": "user-uuid"
  }
}
```

## 14. Campus Social Links

Endpoint: `PUT /api/v1/dashboard/campus/social-links/`

Usage: Campus lead creates or updates a public social media link for the campus.

Request body:

```json
{
  "platform": "instagram",
  "url": "https://instagram.com/example_campus"
}
```

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Social link saved successfully"]
  },
  "response": {
    "id": "social-link-uuid",
    "platform": "instagram",
    "url": "https://instagram.com/example_campus"
  }
}
```

## 15. Campus Events

Endpoint: `GET /api/v1/dashboard/campus/events/`

Usage: Campus lead lists campus-scoped and campus-IG-scoped events.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `status` | string | No | `published`, `ongoing`, `completed`, `cancelled`. |
| `scope` | string | No | `campus`, `campus_ig`. |
| `date_from` | date | No | Start date filter. |
| `date_to` | date | No | End date filter. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Success"]
  },
  "response": {
    "data": [
      {
        "id": "event-uuid",
        "title": "Python Bootcamp",
        "status": "published",
        "scope": "campus",
        "organiser_type": "campus",
        "start_datetime": "2026-06-01T09:00:00+05:30",
        "end_datetime": "2026-06-01T17:00:00+05:30",
        "venue_type": "physical",
        "venue_city": "Kochi",
        "interest_count": 45,
        "cover_image": "https://cdn.example.com/python-bootcamp.jpg",
        "tags": ["python", "bootcamp"]
      }
    ],
    "pagination": {
      "count": 12,
      "totalPages": 1,
      "isFirst": true,
      "isLast": true
    }
  }
}
```

## 16. Enabler Home Summary

Endpoint: `GET /api/v1/dashboard/enabler/home-summary/`

Usage: Enabler reviews assigned campuses, campus health, pending issues, inactive campuses, and follow-up priorities.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `30d`, `90d`; default `30d`. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Enabler dashboard summary fetched successfully"]
  },
  "response": {
    "enabler": {
      "id": "user-uuid",
      "full_name": "Priya Nair",
      "muid": "priya-nair@mulearn"
    },
    "summary": {
      "assigned_campuses": 12,
      "active_campuses": 8,
      "at_risk_campuses": 3,
      "pending_followups": 9,
      "new_students_this_period": 320
    },
    "alerts": [
      {
        "type": "inactive_campus",
        "campus_id": "org-uuid",
        "campus_name": "Example College",
        "message": "No learning circle meetings in 30 days."
      }
    ]
  }
}
```

## 17. Enabler Assigned Campuses

Endpoint: `GET /api/v1/dashboard/enabler/campuses/`

Usage: Enabler lists assigned campuses with health score, leads, participation, and last activity.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `health` | string | No | `healthy`, `watch`, `risk`. |
| `search` | string | No | Search campus name or code. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Assigned campuses fetched successfully"]
  },
  "response": {
    "data": [
      {
        "campus_id": "org-uuid",
        "campus_name": "Example College of Engineering",
        "campus_code": "ECE001",
        "health_score": 72,
        "health_status": "watch",
        "campus_lead": "Arjun Menon",
        "active_members": 180,
        "active_circles": 8,
        "last_activity_at": "2026-05-24T10:00:00+05:30",
        "pending_followups": 2
      }
    ],
    "pagination": {
      "count": 12,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false
    }
  }
}
```

## 18. Enabler Campus Review

Endpoint: `GET /api/v1/dashboard/enabler/campuses/<campus_id>/review/`

Usage: Enabler reviews one campus before intervention, visit, or reporting.

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus review fetched successfully"]
  },
  "response": {
    "campus": {
      "id": "org-uuid",
      "name": "Example College of Engineering",
      "code": "ECE001",
      "health_score": 72,
      "health_status": "watch"
    },
    "metrics": {
      "total_members": 312,
      "active_members": 180,
      "karma_last_30_days": 4800,
      "active_circles": 8,
      "events_last_90_days": 6
    },
    "issues": [
      {
        "type": "circle_inactivity",
        "severity": "medium",
        "message": "4 circles have no meetings in the last 30 days."
      }
    ],
    "recent_notes": [
      {
        "id": "note-uuid",
        "note": "Campus lead requested mentor support for Web Development.",
        "created_at": "2026-05-20T10:00:00+05:30"
      }
    ]
  }
}
```

Endpoint: `POST /api/v1/dashboard/enabler/campuses/<campus_id>/notes/`

Usage: Enabler adds a review note, blocker, campus visit update, or follow-up item.

Request body:

```json
{
  "note": "Campus needs support to restart inactive learning circles.",
  "status": "open",
  "priority": "high",
  "follow_up_date": "2026-06-05"
}
```

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus note added successfully"]
  },
  "response": {
    "note_id": "note-uuid",
    "campus_id": "org-uuid",
    "status": "open",
    "created_at": "2026-05-28T10:30:00+05:30"
  }
}
```

## 19. Enabler Reports

Endpoint: `GET /api/v1/dashboard/enabler/reports/`

Usage: Enabler views or exports summary reports for assigned campuses, district activity, intervention outcomes, and pending action items.

Query params:

| Param | Type | Required | Notes |
|---|---|---:|---|
| `period` | string | No | `30d`, `90d`, `custom`. |
| `date_from` | date | No | Required when `period=custom`. |
| `date_to` | date | No | Required when `period=custom`. |
| `format` | string | No | `json`, `csv`; default `json`. |

Request body: none.

Response body:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Enabler report fetched successfully"]
  },
  "response": {
    "period": "30d",
    "summary": {
      "assigned_campuses": 12,
      "active_campuses": 8,
      "at_risk_campuses": 3,
      "followups_closed": 14,
      "followups_pending": 9
    },
    "campuses": [
      {
        "campus_id": "org-uuid",
        "campus_name": "Example College",
        "health_score": 72,
        "karma_last_30_days": 4800,
        "events_last_30_days": 2,
        "followups_pending": 2
      }
    ]
  }
}
```

