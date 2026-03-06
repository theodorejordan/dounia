# TypeScript Setup for Dounia

## Overview

The JavaScript code has been refactored to use TypeScript for better type safety and maintainability.

## Directory Structure

```
/src/                    # TypeScript source files
  /core/                # Global functionality (sidebar, etc.)
  /components/          # Reusable UI components
  /pages/               # Page-specific logic
  /utils/               # Utility functions

/static/js/             # Compiled JavaScript (generated, don't edit)
  /core/
  /components/
  /pages/
  /utils/
```

## Development Workflow

### First Time Setup

```bash
# Install dependencies
npm install
```

### Building TypeScript

```bash
# Compile TypeScript once
npm run build

# Watch mode (auto-compile on save)
npm run watch
```

### After Making Changes

1. Edit TypeScript files in `/src/`
2. Run `npm run build` (or use watch mode)
3. Compiled JavaScript appears in `/static/js/`
4. Django serves the compiled files from `/static/js/`

## Important Notes

- **Never edit files in `/static/js/` directly** - they're generated from TypeScript
- **Always edit TypeScript source in `/src/`**
- **Run `npm run build` before committing** to ensure compiled JS is up to date
- Source maps (`.js.map`) and type definitions (`.d.ts`) are in `.gitignore`

## Phase 1 Complete ✅

**Extracted modules:**
- `src/utils/helpers.ts` - Utility functions (escapeHtml, getCsrfToken)
- `src/core/sidebar.ts` - Sidebar toggle with localStorage persistence

**Updated templates:**
- `templates/base.html` - Now imports compiled sidebar module

## Benefits of TypeScript

1. **Type Safety**: Catch errors at compile time
2. **Better IDE Support**: Autocomplete and inline documentation
3. **Refactoring**: Rename functions/variables safely across files
4. **Documentation**: Types serve as inline documentation

## Example

**Before (inline JavaScript):**
```html
<script>
  const sidebar = document.getElementById('sidebar');
  // ... 30 lines of code ...
</script>
```

**After (TypeScript module):**
```html
<script type="module">
  import { initSidebar } from "{% static 'js/core/sidebar.js' %}";
  initSidebar();
</script>
```

## Next Steps

Continue with Phase 2: Extract collection page components (album cards, pagination, filters).
