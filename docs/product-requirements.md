# NEXUS AI — Product Requirements

**Status:** Draft — Phase 0, Step 0.1  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md, PART I — PRODUCT VISION

## 1. Product overview

NEXUS AI is a standalone desktop application that acts as a personal AI operating environment. It combines a natural conversational companion with specialized agents that can plan and carry out work on the user's computer.

It is not merely a chatbot, a code editor extension, a collection of scripts, or a web application opened in a browser. The user launches one desktop application and accesses conversational, coding, computer-control, and personal-organization capabilities from a unified interface.

The system should be able to:
- Understand a request.
- Determine what kind of work is required.
- Create a plan.
- Select the appropriate agent.
- Use authorized tools.
- Monitor progress.
- Recover from interruptions.
- Verify results.
- Explain what it accomplished.

## 2. Target platform

- Initial: Arch Linux, GNOME, Wayland
- Future: Windows and other Linux desktop environments through platform-specific adapters
- Portability designed into the architecture from the beginning

## 3. Four specialized agents

### 3.1 Personal Conversational Companion

The companion is the user's natural point of contact. It must support both ordinary conversation and actionable requests.

Core capabilities:
- Natural greetings, casual chat, humour, goodbyes and topic changes.
- Conversation history and context reconstruction.
- Working, long-term, semantic and episodic memory.
- Personal profile containing user-approved preferences, interests and goals.
- Detection of questions that were not answered and topics awaiting an update.
- Tracking of promises, plans, decisions and unfinished discussions.
- Relevant follow-up questions at appropriate times.
- Recognition of conversational signals such as frustration, excitement, sadness, confusion or boredom, with suitable tone adjustment.
- User-controlled proactive conversations, quiet hours and frequency limits.
- Memory inspection, correction, deletion and retention controls.
- Handoff of actionable requests to the coding, computer or life-management agent.
- Clear reporting of what delegated agents actually completed.

The companion must not treat every sentence as a command. It should distinguish casual conversation from a request, a goal, a reminder, a progress update or a potential task.

### 3.2 Autonomous Coding Agent

The coding agent is a project-aware software engineering agent.

Capabilities:
- Open and inspect a selected project workspace.
- Understand project structure, languages, frameworks and dependencies.
- Search files and symbols.
- Read and edit code.
- Create, move, rename and delete files subject to permissions.
- Produce a plan and persistent TODO list.
- Run terminal commands in a controlled environment.
- Install project dependencies when authorized.
- Run tests, builds, linters and formatters.
- Interpret errors and stack traces.
- Debug and revise its changes.
- Inspect Git status and diffs.
- Preserve project-specific memory and decisions.
- Resume interrupted work.
- Verify the result and provide a change report.

It must not silently overwrite important user work. Changes should be reviewable, and risky operations should require approval.

### 3.3 Autonomous Computer Agent

The computer agent operates the user's computer and supported desktop applications.

Capabilities:
- Inspect operating-system and desktop-session information.
- Find, read, create, copy, move and organize files.
- Launch and manage applications.
- Inspect windows and processes.
- Navigate websites and interact with browser pages.
- Work inside supported desktop applications.
- Use application APIs where available.
- Use accessibility interfaces to identify controls.
- Use OCR and image matching when stronger interfaces are unavailable.
- Perform controlled keyboard and mouse actions where necessary.
- Verify the result of important actions.
- Maintain an execution history and report limitations.

Interface understanding priority:
1. Application APIs or structured interfaces.
2. Browser DOM and accessibility information.
3. Operating-system accessibility interfaces.
4. Application-specific adapters.
5. OCR and deterministic image processing.
6. OpenCV template matching and coordinate-based interaction as fallbacks.

A vision-language model is not a required dependency.

### 3.4 Life Management Agent

The life-management agent handles personal organization and scheduled work.

Capabilities:
- Create and manage tasks and subtasks.
- Set reminders.
- Manage schedules and recurring activities.
- Track deadlines and commitments.
- Organize personal goals.
- Provide daily or weekly summaries.
- Follow up on tasks when appropriate.
- Integrate with calendars and notification services when configured.
- Receive requests from the companion and return results to it.

## 4. Orchestration

The four agents are coordinated by one central orchestrator.

The orchestrator should:
1. Receive the user's message or action.
2. Determine the intent and risk level.
3. Identify the appropriate agent or agents.
4. Provide only the context and permissions those agents need.
5. Track delegated work.
6. Coordinate dependencies and shared resources.
7. Collect verified results.
8. Return a clear response through the companion or relevant workspace.

Shared infrastructure includes model management, memory, tool execution, MCP connections, permissions, task persistence, scheduling, notifications, logging and verification.

## 5. Conversation-to-action intelligence

The AI should understand that a conversation can contain an instruction, a promise, a goal, a question or simply casual discussion.

Classifications:
- Personal goal.
- Scheduled reminder.
- Potential task.
- Progress update.
- Information request.
- Casual conversation.
- Potential autonomous project.

It must not turn every sentence into a task. It should understand intent and ask for clarification when necessary.

## 6. First-release minimum viable product

Recommended first-release capabilities:
- Installable desktop shell.
- Backend lifecycle management.
- Persistent chat.
- One local model provider.
- Optional one cloud provider.
- Basic companion memory with user controls.
- Safe filesystem tools.
- Controlled terminal tool.
- Task planning and persistent TODOs.
- One MCP integration.
- Basic browser automation.
- Clear approval and activity history.

Advanced GUI automation, application adapters, full coding autonomy, life-management integrations, proactive engagement and voice are added incrementally after the first release.

## 7. User stories

### Companion
- As a user, I want to greet the AI naturally ("Hey", "Good morning") and receive a varied, natural response, so the interaction feels human-like.
- As a user, I want the AI to remember my interests, goals and previous conversations, so I don't have to repeat myself.
- As a user, I want the AI to follow up on unfinished topics (e.g. an assignment I mentioned earlier), so nothing falls through the cracks.
- As a user, I want the AI to recognize when I'm frustrated or bored and adjust its tone, so the conversation stays appropriate.
- As a user, I want to inspect, correct and delete my stored memories, so I control what the AI remembers about me.
- As a user, I want the AI to distinguish casual chat from actionable requests, so it doesn't create tasks from every sentence I say.

### Coding agent
- As a user, I want to point the AI at a project and ask it to implement a feature, so I can develop software faster.
- As a user, I want the AI to show me which files it changed and run the tests, so I can verify the work.
- As a user, I want risky file operations to require my approval, so important work isn't silently overwritten.

### Computer agent
- As a user, I want the AI to find, organize and move files on my computer, so I can manage my filesystem through conversation.
- As a user, I want the AI to launch applications and inspect running processes, so I can control my desktop without manual navigation.
- As a user, I want the AI to verify that a file copy or application launch actually succeeded, so I can trust the result.

### Life management
- As a user, I want to tell the AI "remind me to pay rent on Friday" and have it create a reminder, so I don't forget commitments.
- As a user, I want the AI to organize my task list when I describe several things to do, so my personal administration is handled through conversation.

### Orchestration
- As a user, I want one application with one conversation entry point, so I don't have to switch between different agents or interfaces manually.

## 8. Non-functional requirements

- Stateful execution: every long-running task has a persistent execution record that survives crashes.
- Least privilege: agents only have the capabilities they need; destructive operations require approval.
- No fake functionality: every control has a defined behaviour; no decorative buttons.
- Observable: important operations produce events streamed to the frontend via WebSockets.
- Untrusted content: website content, documents, downloads and external MCP responses are treated as untrusted input.
- Recovery: the agent can reconstruct execution state from persistent storage after a crash.

## 9. Out of scope for first release

- Vision-language model as a required dependency.
- Microsoft Access automation on Arch Linux (Windows-only).
- Full PostgreSQL/vector search (SQLite is the initial database; PostgreSQL optional later).
- All seven custom MCP servers (start with one, add more incrementally).
- Voice interaction (Phase 16).
