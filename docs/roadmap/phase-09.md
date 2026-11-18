# PHASE 9 — Screenshot, OCR and GUI recognition engine

## Objective

Build an interface-understanding system without requiring a vision-language model.

This phase is especially important for your proposed architecture.

### Step 9.1 — Build screen capture

Implement:

- Screenshot capture.
- Active monitor selection.
- Window capture where supported.
- Resolution detection.
- Scaling detection.
- Screenshot timestamps.
- Screenshot storage policies.

On GNOME Wayland, investigate xdg-desktop-portal ScreenCast and RemoteDesktop capabilities and their permission requirements.

Do not assume X11 automation techniques work unchanged on Wayland.

### Step 9.2 — Build OCR

Integrate Tesseract OCR.

Implement:

- Text detection.
- Text extraction.
- Bounding-box extraction.
- Language selection.
- Confidence scores.
- Region-based OCR.
- OCR result caching.

### Step 9.3 — Build template recognition

Use OpenCV.

Implement:

- Template registration.
- Template matching.
- Matching confidence.
- Region-of-interest detection.
- Scale variation.
- Theme variations.
- Template versioning.
- Recognition failure reporting.

### Step 9.4 — Build visual element classification

Recognize common interface elements:

- Buttons.
- Text boxes.
- Menus.
- Icons.
- Dialogs.
- Checkboxes.
- Tabs.
- Toolbars.
- Status indicators.

Use deterministic image processing and known interface templates, not an assumption that every icon can be identified universally.

### Step 9.5 — Build the accessibility inspection engine

Integrate AT-SPI2 and available application accessibility interfaces.

Retrieve:

- Element names.
- Roles.
- States.
- Bounding boxes where available.
- Parent-child relationships.
- Focus information.
- Available actions.

Accessibility information should take priority over image matching.

### Step 9.6 — Build the recognition fusion engine

Combine:

1. Accessibility information.
2. Application-specific metadata.
3. OCR.
4. Template matching.
5. Window information.
6. Screenshot coordinates.

Generate one structured representation of the active interface.

### Step 9.7 — Build GUI interaction

Implement controlled:

- Mouse movement.
- Clicking.
- Keyboard input.
- Shortcuts.
- Scrolling.
- Focus changes.

Use supported desktop interfaces and permission-based input mechanisms.

### Step 9.8 — Build the verification engine

After every important action:

1. Inspect the application state.
2. Check accessibility changes.
3. Check OCR results.
4. Compare relevant screenshot regions.
5. Determine whether the expected result occurred.
6. Retry or report failure.

### Step 9.9 — Build application-independent fallback

When an application is unknown:

1. Inspect its window.
2. Retrieve available accessibility information.
3. Capture a screenshot.
4. Extract visible text.
5. Identify known visual templates.
6. Present structured information to the model.
7. Execute only actions supported by the available evidence.

**Completion criteria:** The agent can inspect known interfaces and perform basic GUI actions using structured data, OCR and templates without requiring a VLM.

---


**Roadmap:** [Index](../../overview) · [← Phase 8: Browser navigation and web automation](phase-08.md) · [Phase 10: Application adapter framework →](phase-10.md)
