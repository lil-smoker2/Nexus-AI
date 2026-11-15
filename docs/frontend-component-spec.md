# NEXUS AI — Frontend Component Specification

**Status:** Draft — Phase 0, Step 0.5  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART III

## 1. Technology stack

- Shell: Tauri (Rust backend + webview frontend)
- UI: React + TypeScript
- Styling: Tailwind CSS
- State management: to be selected (React Context / Zustand / Redux Toolkit)
- API client: fetch wrapper or axios with typed responses
- WebSocket: native WebSocket for event streaming
- Build: Vite

## 2. Global application layout

| Region | Component | Responsibility |
|---|---|---|
| Left sidebar | `Sidebar` | Collapsible navigation, agent status, window controls |
| Top bar | `TopNav` | Global search, notifications, user settings |
| Main workspace | `MainContent` | Page-level routing (Home, Chat, Companion, etc.) |
| Context panel | `ContextPanel` | Optional side panel for active task context |
| Status area | `StatusBar` | Backend connection, agent activity, system resources |
| Notification centre | `NotificationCentre` | Recent alerts, approvals, events |

## 3. Navigation destinations

1. Home — dashboard with widgets (greeting, quick actions, agent availability, active tasks, pending approvals, recent conversations, upcoming reminders, MCP/model status, weather/time, system resources)
2. Chat — conversation list, message history, streaming, markdown/code rendering, attachments
3. Companion — natural conversation, memory controls, unresolved topics, follow-up history, goals, proactive settings
4. Coding Agent — project selector, plan/TODO panel, file explorer, diff review, terminal output, test results, approval controls
5. Computer Agent — OS info, active window, browser sessions, accessibility inspection, screenshot/OCR, permission requests
6. Life Management — tasks, reminders, schedules, deadlines, goals, summaries
7. Tasks — task listing, filtering, dependencies
8. Workspaces and Projects — workspace registration, project scanning
9. Memory — search, categories, edit/delete, retention, unresolved items
10. MCP Servers — server list, add/edit/remove, connect/disconnect, tool discovery, logs
11. Models — provider management, local/cloud registration, model selection, testing
12. Integrations — external service configuration
13. Activity and History — event log, execution history, audit trail
14. Settings — general, appearance, models, agent behaviour, memory, voice, permissions, browser, MCP, notifications, privacy, backup

## 4. Reusable component library

### 4.1 Design system (Theme)
- Color variables (dark/light themes)
- Typography scale
- Spacing system
- Border and radius system

### 4.2 Components

| Component | Variants / States |
|---|---|
| Button | primary, secondary, danger, ghost; default, loading, disabled |
| Input | text, password, number, select; default, error, disabled |
| Dropdown menu | open/closed, with icons |
| Modal dialog | default, confirmation, destructive |
| Tooltip | top/bottom/left/right |
| Notification | info, success, warning, error; auto-dismiss |
| Loading indicator | spinner, skeleton, thinking/working state |
| Empty state | illustration + action button |
| Error state | message + retry action |
| Confirmation dialog | confirm/cancel |
| Card | default, bordered, elevated |
| Panel | resizable, collapsible |
| Badge | status colors |
| Progress bar | determinate/indeterminate |
| Avatar | user/agent avatar |
| Switch | on/off |
| Slider | range input |
| Tabs | horizontal/vertical |
| Accordion | expand/collapse |
| Table | sortable, paginatable |
| File comparison widget | side-by-side original vs copied (Phase 2.3) |
| Weather/time widget | dashboard widget (Phase 2.1) |

## 5. State management

- Global: auth, theme, backend connection status, notifications
- Page-level: conversation messages, task list, agent state
- Form state: controlled inputs with validation
- WebSocket events: update UI optimistically where safe

## 6. API client

- Centralized client in `src/services/api.ts`
- Typed request/response functions matching backend Pydantic schemas
- Request/response interceptors for auth tokens and error handling
- Loading and error states exposed per endpoint
- WebSocket client in `src/services/websocket.ts` for event streaming

## 7. Forms and validation

- Every form has client-side validation matching backend constraints
- Error messages displayed inline
- Submission states: idle / loading / success / error
- No decorative controls — every control has a defined action

## 8. Accessibility

- Keyboard navigation throughout
- ARIA labels on interactive elements
- Focus management in modals and dropdowns
- Color contrast meets WCAG AA
- Screen reader testing

## 9. Responsive desktop layouts

- Target: common desktop resolutions (1366×768 to 3840×2160)
- Resizable panels (sidebar, context panel)
- Long conversations, large project trees, extensive task lists supported

## 10. Frontend testing structure

| Test type | Tool | Location |
|---|---|---|
| Unit | Vitest | `desktop/src/**/*.test.ts` |
| Component | React Testing Library + Vitest | `desktop/src/**/*.test.tsx` |
| E2E | Playwright | `desktop/tests/e2e/` |

## 11. Frontend conventions

- Formatting: Prettier
- Linting: ESLint with TypeScript plugin
- Type checking: `tsc --noEmit`
- File naming: kebab-case for files, PascalCase for components
- Component structure: one component per file, co-located styles
