# Fix: College Sorting Bug - sortBy=org and Multi-Field Sorting

## Root Cause Analysis

The bug was in the `sort_fields` dictionary definition in `api/dashboard/college/college_view.py` line 20.

**Original code:**
```python
sort_fields={'org': 'org'},
```

**Issue:** 
- The value `'org'` refers to the raw `Organization` model instance/object itself
- When Django ORM tries to sort by a foreign key object without specifying a field, it defaults to sorting by the object's primary key (UUID in this case)
- This made the sort appear random to users instead of sorting alphabetically by organization name
- The endpoint only supported the 'org' field and lacked support for 'level' and 'created_at'

## The Fix

Updated `sort_fields` dictionary to use the proper ORM field lookup paths:

```python
sort_fields={
    'org': 'org__title',
    'level': 'level',
    'created_at': 'created_at',
},
```

**Explanation:**
- `'org': 'org__title'` - Uses Django's double-underscore notation to traverse the foreign key relationship and access the Organization's `title` field
- `'level': 'level'` - Direct reference to the College model's `level` integer field
- `'created_at': 'created_at'` - Direct reference to the College model's `created_at` datetime field

## How the Sorting Works

The `CommonUtils.get_paginated_queryset()` function automatically handles:
- Ascending/descending order via the "-" prefix (e.g., `?sortBy=-org`)
- Field lookup validation (unsupported fields are gracefully ignored)
- Query parameter: `sortBy`

### Supported Query Parameters

| Query Parameter | Result | ORM Field Used |
|---|---|---|
| `?sortBy=org` | A → Z by org name | `org__title` |
| `?sortBy=-org` | Z → A by org name | `-org__title` |
| `?sortBy=level` | Ascending by level | `level` |
| `?sortBy=-level` | Descending by level | `-level` |
| `?sortBy=created_at` | Oldest first | `created_at` |
| `?sortBy=-created_at` | Newest first | `-created_at` |

## Verification Steps

### Using Postman or cURL

1. **Test org ascending (A→Z):**
   ```
   GET /api/v1/dashboard/college/?sortBy=org&pageIndex=1&perPage=10
   ```
   Expected: Colleges sorted alphabetically by organization name

2. **Test org descending (Z→A):**
   ```
   GET /api/v1/dashboard/college/?sortBy=-org&pageIndex=1&perPage=10
   ```
   Expected: Colleges sorted reverse alphabetically

3. **Test level ascending:**
   ```
   GET /api/v1/dashboard/college/?sortBy=level&pageIndex=1&perPage=10
   ```
   Expected: Colleges sorted by level ascending (0, 1, 2, etc.)

4. **Test level descending:**
   ```
   GET /api/v1/dashboard/college/?sortBy=-level&pageIndex=1&perPage=10
   ```
   Expected: Colleges sorted by level descending

5. **Test created_at ascending:**
   ```
   GET /api/v1/dashboard/college/?sortBy=created_at&pageIndex=1&perPage=10
   ```
   Expected: Colleges sorted oldest first

6. **Test created_at descending:**
   ```
   GET /api/v1/dashboard/college/?sortBy=-created_at&pageIndex=1&perPage=10
   ```
   Expected: Colleges sorted newest first

7. **Test with search (regression test):**
   ```
   GET /api/v1/dashboard/college/?search=mit&pageIndex=1&perPage=10
   ```
   Expected: Search still works independently of sorting

8. **Test unsupported field (graceful fallback):**
   ```
   GET /api/v1/dashboard/college/?sortBy=invalid_field&pageIndex=1&perPage=10
   ```
   Expected: No error, returns results in default order

## Edge Cases & Considerations

1. **Null/Empty Organization Titles:** The sort gracefully handles colleges with null or empty org titles (they typically sort first or last depending on database collation)

2. **Case-Sensitive Sorting:** The original organization title case is preserved during sorting (e.g., "MIT" vs "mit" may have different sort positions depending on database collation settings)

3. **Pagination + Sorting:** Both features work together correctly - the sort is applied before pagination, ensuring consistent results across pages

4. **Unsupported Fields:** Fields not in the `sort_fields` dict are silently ignored (no error thrown), maintaining backward compatibility

5. **Multiple Colleges Same Level:** When sorting by level, colleges with the same level maintain their natural database order unless a secondary sort is specified

6. **Date Sorting:** `created_at` sorting works correctly with the database's timezone-aware datetime values

## Files Modified

- `api/dashboard/college/college_view.py` (lines 12-15)

## Related Code

- `utils/utils.py` - `CommonUtils.get_paginated_queryset()` function handles the sort logic
- `db/organization.py` - College model definition with `org` OneToOneField relationship to Organization
