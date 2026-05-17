# Dounia — Roadmap

## Overview

Dounia is a collaborative album collection platform:
- **Visitors** can browse the collection (read-only)
- **Registered users** can submit albums for review
- **Admin** curates submissions, manages the collection, and creates projects

---

## User Roles

| Role | Access |
|------|--------|
| Anonymous | Browse collection, view public profiles |
| Authenticated | + Submit albums (existing tags only), view own submissions |
| Admin (`is_staff`) | + Add albums directly, review submissions, delete albums, manage projects |

---

## Phase 1: Auth + Profile ✅ COMPLETE

- Registration, login, logout
- Profile page with avatar upload, edit username/email, change password
- Public profile page (`/profile/<username>/`)
- Sidebar shows profile widget when logged in
- Trash button visible only to admin

---

## Phase 2: Album Submissions ✅ COMPLETE

### Implementation
- **Submission model** — separate from Album, stores pending submissions
- **Regular users** see "Submit album" in sidebar → `/submit/`
- **Admin** sees "Add album" (direct) + "Submissions" (review queue)
- Tags: users can only select existing tags (`enforceWhitelist: true`)
- Profile page: left menu with Edit Info / Submissions sections
- Admin review page at `/submissions/` with Accept/Delete actions

### URLs
```
/submit/                    — user submission form
/profile/                   — edit info section
/profile/submissions/       — user's submission history
/submissions/               — admin review page
/submissions/<pk>/approve/  — approve submission (creates album)
/submissions/<pk>/delete/   — delete submission
```

---

## Phase 3: Projects — NOT STARTED

### Models
- `Project` — name, subtitle, cover (FK to Album), notes
- `ProjectAlbum` — through table with position for ordering

### Features
- Admin selects albums from collection → creates project
- Project detail with two tabs:
  - **Tab 1**: Info + album grid (read-only for users)
  - **Tab 2**: Drag-drop grid reorder + notes (admin only)
- SortableJS for drag-drop

### URLs
```
/projects/                  — project list
/projects/<pk>/             — project detail
/projects/<pk>/edit/        — update project
/projects/<pk>/reorder/     — save grid positions
```

---

## Future Ideas

- **More import sources** — YouTube Music, Apple Music, RateYourMusic
- **Homepage** — latest albums, latest projects, search
- **Album detail drawer** — right side slide-in panel with full album info
- **Comments** — users can comment on albums inside the right side panel
- **Dounia logo illustration**
- **Clicking on artist to filter**
- **one single filter bar with every filter available**
- **count on collection**

---

## Progress

### Completed
- [x] Phase 1: Auth + Profile
- [x] Phase 2: Album Submissions
- [x] Changelog page
- [x] HTMX filtering with URL persistence
- [x] Album import (Deezer, Discogs, Bandcamp)
- [x] Category filters with child tags

### Next
- [ ] Phase 3: Projects
