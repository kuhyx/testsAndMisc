Mini Articles (<=14KB)

- Single-file site: `index.html` with inline CSS & JS
- Features:
  - List of articles with thumbnails (cards)
  - Read view: thumbnail, title, body (supports inline images/videos)
  - Create view: title, thumbnail picker/drag-drop, rich body via contenteditable
  - Drag/drop or choose images/videos anywhere in the body
  - Local persistence via localStorage (no server required)

How to open
- Open `site/index.html` in a browser.

Tests
- `pytest` includes a test to enforce the 14KB budget for `index.html`.
