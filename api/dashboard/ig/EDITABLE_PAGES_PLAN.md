# Editable IG Pages Feature

## Planned Changes

### 1. Database Schema Updates
- Add `page_content` JSONField to Interest Group model
- Add `IGPageSection` model for dynamic sections

### 2. New API Endpoints
- GET /api/dashboard/ig/{id}/page/ - Get IG page content
- PUT /api/dashboard/ig/{id}/page/ - Update IG page content
- POST /api/dashboard/ig/{id}/sections/ - Add new section
- DELETE /api/dashboard/ig/{id}/sections/{section_id}/ - Remove section

### 3. Dynamic Fields Support
- Text sections
- Image sections
- Video embeds
- Custom HTML blocks

## Status
Work in progress - implementing editable pages with dynamic field support
