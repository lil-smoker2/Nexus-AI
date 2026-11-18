# PHASE 2 — Implement the complete frontend

## Objective

Finish the actual user interface before connecting all advanced AI capabilities.

### Step 2.1 — Home dashboard

Implement:

- Welcome section.
- Quick actions.
- Agent availability.
- Active task overview.
- Recent conversations.
- Recent projects.
- Pending approvals.
- MCP server status.
- Model status.
- Weather and time widgets.
- Notification summary.
- System resource information.

Every dashboard card should retrieve information from a defined backend endpoint.

### Step 2.2 — Chat workspace

Implement the primary companion conversation in the four-area layout defined in `docs/chat-experience.md`: navigation rail, companion stage, conversation, and optional context panel. Keep general chat capabilities available within the same conversation surface.

Implement:

- Conversation list.
- Message history.
- Message rendering.
- Markdown support.
- Code highlighting.
- Attachments.
- Message editing.
- Regeneration.
- Conversation search.
- Conversation creation.
- Conversation deletion.
- Streaming responses.
- Agent selection.
- Model selection.
- Dedicated companion avatar and explicit availability/listening state.
- Context panel with separate user-facing `Thinking` and `Memories` views.
- Context-panel collapse/restore without losing the selected conversation or scroll position.

The `Thinking` view may summarize user-visible progress or relevant context, but must never expose private chain-of-thought, system prompts, credentials, or unrestricted internal traces. Memory entries must be grounded in stored data and offer the established memory controls. The preview is illustrative; demonstrate data must not be presented as live AI output.

### Step 2.3 — Coding agent workspace

Create independent panels for:

1. Task conversation.
2. Planning.
3. TODO list.
4. Tool activity.
5. File explorer with side-by-side file comparison widgets that show the original and copied files when a copy operation completes.
6. Execution history.
7. Project information.
8. Approval requests.

Implement controls for starting, pausing, resuming, stopping and retrying tasks.

### Step 2.4 — Computer agent workspace

Create:

- Operating-system information.
- Active window information.
- Application list.
- Browser sessions.
- Automation sessions.
- Accessibility inspector.
- Screenshot inspector.
- OCR output.
- Template recognition results.
- Available automation tools.
- Execution logs.

### Step 2.5 — Companion workspace

Implement the companion as the primary chat experience, sharing the navigation, companion-stage, conversation, and context-panel behavior specified in `docs/chat-experience.md`.

Implement:

- Natural chat.
- Personal memory panel.
- Unanswered questions.
- Follow-up history.
- Personal goals.
- Preferences.
- Conversation summaries.
- Proactive conversation settings.
- User-facing activity summaries in place of private internal reasoning.
- Clear empty, loading, offline, and error states for memory and conversation context.

### Step 2.6 — MCP management

Implement:

- Server listing.
- Add server.
- Edit configuration.
- Remove server.
- Connect.
- Disconnect.
- Restart.
- Tool discovery.
- Tool inspection.
- Connection status.
- Server logs.

### Step 2.7 — Models and integrations

Implement:

- Provider management.
- Local model registration.
- Cloud provider configuration.
- Model selection.
- Model testing.
- Default model settings.
- MCP integrations.
- External service configuration.

### Step 2.8 — Tasks and memory

Implement:

- Task listing.
- Task details.
- Subtasks.
- Task dependencies.
- Task filters.
- Memory categories.
- Memory editing.
- Memory deletion.
- Memory search.

### Step 2.9 — Frontend quality assurance

Test:

- Navigation.
- Forms.
- Validation.
- Modals.
- Keyboard shortcuts.
- Responsive desktop layouts.
- Loading states.
- Error states.
- Empty states.
- Long conversations.
- Large task lists.
- Panel resizing.
- Compare the companion chat against `docs/chat-experience.md` and `docs/nexus-ai-chat-preview.svg` at the reference and minimum supported window sizes.
- Verify context-panel privacy, memory persistence states, keyboard operation, reduced-motion behavior, and that collapsing panels preserves conversation state.

**Completion criteria:** The frontend is complete as an application interface, with all interactions connected to real or explicitly pending backend contracts.

---


**Roadmap:** [Index](../../overview) · [← Phase 1: Create the desktop application foundation](phase-01.md) · [Phase 3: AI model integration →](phase-03.md)
