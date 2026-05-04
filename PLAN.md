# Dounia — Advanced Features Plan

## Context

Dounia is currently a single-user personal album collection manager (no auth, admin-only). The goal is to evolve it into a semi-public collaborative platform where:
- Visitors can browse the collection (read-only, trash button hidden)
- Registered users can submit albums for review
- Admin (you) curates submissions and manages projects
- Projects group albums into curated collections with a visual grid view

This plan covers three phases: **Auth + Profile**, **Submissions**, and **Projects**. Homepage is deferred.

---

## Django Permissions — Architecture Note

Django has a built-in permission system that's efficient and template-friendly, similar to EmberJS abilities:

- **Built-in model permissions**: every model auto-gets `add_<model>`, `change_<model>`, `delete_<model>`, `view_<model>` permissions
- **Custom permissions**: defined in `Meta.permissions` on the model
- **Template access**: `{% if user.is_staff %}` or `{% if perms.albums.delete_album %}` — computed once per request, cached on the user object, no redundant DB hits
- **View access**: `@login_required`, `@permission_required('albums.delete_album')`, or `UserPassesTestMixin`

For this app, roles are simple enough to use just two checks everywhere:
```python
user.is_authenticated   # logged in
user.is_staff           # admin (you)
```
In templates: `{% if request.user.is_staff %}` — zero extra computation.

If finer granularity is needed later (e.g. moderator role), `django-rules` adds a clean rule-based ability system without model-level overhead.

---

## User roles

| Role | Access |
|------|--------|
| Anonymous | Browse collection (no trash button), view public profiles, homepage |
| Authenticated user | + Submit albums (existing tags only, ≥1 tag), view projects (read-only), own submission history on profile |
| Admin (`is_staff`) | + Trash button on albums, add albums directly, review submissions, create/edit/delete projects, project Tab 2 |

---

## Phase 1: Auth + Profile

### User model
Use Django's built-in `User` model as-is — no custom model needed.
- `username` = pseudo (display name)
- `email`, `password` — standard fields
- Profile page = edit view for these fields + logout button

### Sidebar changes
Show **all** sidebar links always. Disable/grey them out when the user lacks permission — don't hide them. This gives a consistent layout and hints at what exists.

```
Sidebar bottom:
  [ avatar/initials ]  username  [ ⚙ gear icon → /profile/ ]
```

Clicking the gear or the username area goes to the profile page.
The logout button lives on the profile page only (red button at the bottom).

### New URLs & views
```
/register/           — registration form (username, email, password ×2)
/login/              — LoginView with custom template
/profile/            — edit own profile + red logout button at bottom
/profile/<username>/ — public profile: user's approved submissions
```
No `/logout/` URL in nav — logout is a POST form button on `/profile/`.

### Register / Login UI
- Simple centered form on a clean white background (no sidebar, minimal chrome)
- Same Tailwind style as the rest of the app but stripped-down layout
- Register: username, email, password, confirm password
- Login: username/email, password, "Remember me" checkbox, link to register

### Profile page UI
- Edit fields: username (pseudo), email, change password section
- Bottom of page: red "Log out" button (POST to `/logout/`)
- Public profile (`/profile/<username>/`): shows approved submitted albums (grid)

### Permission enforcement on existing views
- `add_album_view` → `@login_required` (behavior differs by role — Phase 2)
- `delete_album_view` → `@login_required` + `is_staff` check (403 otherwise)
- Collection page → stays public; trash button conditionally rendered: `{% if request.user.is_staff %}`
- All other browsing stays public

### Files to modify/create
- `albums/views.py` — add `register_view`, `profile_view`; guard `delete_album_view`
- `albums/urls.py` — add auth + profile URL patterns
- `templates/base.html` — sidebar: all links always shown, disable non-authed ones; bottom profile widget
- `templates/registration/login.html` — new: minimal centered form
- `templates/registration/register.html` — new: minimal centered form
- `templates/albums/profile.html` — new: edit profile + logout button
- `templates/albums/public_profile.html` — new: approved submissions grid
- `templates/albums/collection.html` — hide trash button for non-staff

---

## Phase 2: Album Submissions

### Album model changes
Add 3 fields to `Album`:
```python
submitted_by = ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                          on_delete=SET_NULL, related_name='submissions')
status = CharField(
    choices=[('published','Published'), ('pending','Pending'), ('rejected','Rejected')],
    default='published', max_length=20
)
rejection_notes = TextField(blank=True)
```
- Admin-added albums: `status='published'`, `submitted_by=None`
- User submissions: `status='pending'`, `submitted_by=user`
- Approved: `status='published'`; Rejected: `status='rejected'` + notes

### Submission flow (user)
Same `add_album_view`, branched by role:
- **Admin**: unchanged — "Add to collection", free tag input, status='published'
- **Authenticated user**: "Submit for review", Tagify `freeInput=false` (existing tags only, whitelist enforced), ≥1 tag required (server-side validation), status='pending'
- **Anonymous**: redirected to `/login/`

### Admin review page
```
/submissions/   — admin-only (is_staff required)
```
- Grid of pending album cards (same visual as collection)
- Each card: **Approve** / **Reject** action buttons
- Reject → inline HTMX textarea for rejection notes → confirm
- Approve → `status='published'` → album appears in main collection

### Collection + API filter
- All public-facing album queries filter `status='published'`
- `AlbumManager.with_filters()` gets a `status` default of `'published'`

### Profile pages — submission history
`/profile/` (own):
- Sections: Pending | Approved | Rejected
- Rejected items show rejection notes inline

`/profile/<username>/` (public):
- Shows only approved submissions (grid view, same component)

### Files to modify/create
- `albums/models.py` — add 3 fields to `Album`
- `albums/migrations/` — new migration
- `albums/managers.py` (or `models.py`) — add `status='published'` default filter
- `albums/views.py` — update `add_album_view`, add `submissions_review_view`
- `albums/services.py` — accept `submitted_by` + `status` params in album creation
- `templates/albums/add_album.html` — conditional UI (staff vs user)
- `templates/albums/submissions.html` — new: admin review page
- `templates/albums/profile.html` — submission history sections

---

## Phase 3: Projects

### New models

```python
class Project(models.Model):
    name = CharField(max_length=255)
    subtitle = CharField(max_length=255, blank=True)
    cover = ForeignKey('Album', null=True, blank=True, on_delete=SET_NULL,
                       related_name='cover_for_projects')
    albums = ManyToManyField('Album', through='ProjectAlbum')
    notes = TextField(blank=True)       # grid tab notes section
    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class ProjectAlbum(models.Model):
    project = ForeignKey(Project, on_delete=CASCADE)
    album = ForeignKey(Album, on_delete=CASCADE)
    position = PositiveIntegerField(default=0)   # drag-drop order
    added_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position']
        unique_together = [('project', 'album')]
```

### Sidebar
Add "Projects" link to sidebar (visible to all, disabled/greyed for anonymous).

### Album selection flow (collection page, admin only)
- Admin sees checkboxes on album cards (rendered only for `is_staff`)
- Selection state tracked in JS (Set of album IDs)
- Fixed bottom action bar slides up when ≥1 album selected:
  ```
  [ 3 albums selected ]  [ Create Project ]  [ Reset Selection ]
  ```
- "Create Project" → modal overlay with: Name (required), Subtitle (optional)
- On modal submit → `POST /projects/create/` with album IDs → creates `Project` + `ProjectAlbum` rows → redirect to new project detail page

### New URLs
```
/projects/                              — project list (auth required)
/projects/create/                       — POST only, admin only
/projects/<pk>/                         — project detail (auth required)
/projects/<pk>/edit/                    — POST: update name/subtitle/cover/notes, admin only
/projects/<pk>/albums/<album_pk>/remove/ — POST: remove album from project, admin only
/projects/<pk>/reorder/                 — POST: save grid positions [{id, position}], admin only
```

### Project list page (`/projects/`)
- Grid of project cards sorted by `created_at` desc
- Each card: project cover image, name, subtitle, album count
- Auth required (anonymous → redirect to login); read-only for non-admin

### Project detail — access by role
| Role | Tab 1 (Info + Collection) | Tab 2 (Grid + Notes) |
|------|--------------------------|----------------------|
| Admin | Full edit: name/subtitle/cover inline; remove album from project | Drag-drop reorder, notes, grid size toggle |
| Logged user | Read-only: static info + album grid (no actions, no filters) | Hidden (tab not rendered) |
| Anonymous | Redirect to login | — |

### Project detail — Tab 1: Info + Collection
**Admin:**
- Inline editable fields: name, subtitle, cover (dropdown of associated albums) — save via HTMX on change
- Album grid below using `_album_grid.html` partial
  - Delete action overridden to "Remove from project" (POST to remove URL, album stays in main collection)
  - Standard artist/tag filters work within the project's album set

**Logged user (read-only):**
- Static display: project name, subtitle, cover image
- Album grid below (no action buttons, no filters needed)

### Project detail — Tab 2: Grid View (admin only)
- Grid size toggle: **4×6** | **5×7** (stored in localStorage or on the Project model)
- Album covers in grid cells, labelled with album name on hover
- **SortableJS** (CDN, no build step) for drag-and-drop
  - `onEnd` callback → `POST /projects/<pk>/reorder/` with ordered array of album IDs
  - Server updates `ProjectAlbum.position` for each in a bulk update
- Notes section below grid: `<textarea>` with autosave via HTMX `hx-trigger="blur"` → `POST /projects/<pk>/edit/`

### Dependencies to add
- `sortablejs` — CDN (same approach as Tagify, HTMX — no build tooling needed)

### Files to create/modify
- `albums/models.py` — add `Project`, `ProjectAlbum`
- `albums/migrations/` — new migration
- `albums/views.py` — add all project views
- `albums/urls.py` — add project URL patterns
- `templates/base.html` — add Projects to sidebar
- `templates/albums/projects_list.html` — new: project grid
- `templates/albums/project_detail.html` — new: two-tab layout
- `templates/albums/collection.html` — add selection checkboxes + bottom action bar (admin only)
- `static/js/` — album selection logic, SortableJS integration (project detail)

---

## Implementation order

1. **Phase 1** — Auth + profile pages + sidebar changes
2. **Phase 2** — Album model migration + submission flow + review page
3. **Phase 3** — Project models + collection selection + project pages

Each phase is independently deployable and testable before moving on.

---

## Future ideas (deferred)

- **Homepage** — latest albums added, latest projects updated, universal search bar
- **Changelog page** — history of updates to the site/collection
- **Dounia logo illustration** — custom illustrated logo

---

## Verification checklist

**Phase 1:**
- [ ] Anonymous can browse collection; trash button absent; sidebar shows all links (some greyed)
- [ ] Register → login → sidebar shows profile widget at bottom
- [ ] Profile page: edit username/email, change password, logout button (red, bottom)
- [ ] Admin (`is_staff`) sees trash button on album cards

**Phase 2:**
- [ ] Authenticated user visits `/add/` → sees "Submit for review", Tagify no free input
- [ ] Submit with 0 tags → server-side validation error
- [ ] Submission appears in `/submissions/` for admin, not in main collection
- [ ] Admin approves → album in collection with `submitted_by` set
- [ ] Admin rejects → user sees notes on their `/profile/` page
- [ ] Public profile shows only approved submissions

**Phase 3:**
- [ ] Admin checks 3 albums → action bar appears → creates project → redirects to project page
- [ ] Tab 1 (admin): edit project name inline; remove album → album stays in main collection
- [ ] Tab 1 (user): read-only, no action buttons, Tab 2 not visible
- [ ] Tab 2: drag to reorder → refresh → order persists
- [ ] Notes textarea autosaves on blur
