# PHASE 12 — Human-like conversational companion

## Objective

Build the personal AI that maintains continuity across conversations and remembers relevant personal context.

### Step 12.1 — Build conversation management

Implement:

- Conversation creation.
- Message persistence.
- Conversation summaries.
- Conversation retrieval.
- Topic extraction.
- Context reconstruction.
- Conversation search.
- Natural short conversations using a conversational engine that responds to ordinary human expressions without interpreting every message as a command.
- Varied, natural responses rather than fixed greeting templates.

### Step 12.2 — Implement working memory

Store:

- Current topic.
- Current discussion.
- Recent messages.
- Unanswered questions.
- Current intentions.
- Active conversational context.
- Personal profile (preferences and goals) managed by the personal profile engine.

### Step 12.3 — Implement long-term memory

Create memory categories using the personal memory engine:

- Personal information.
- Preferences.
- Interests.
- Goals.
- Important events.
- Learning progress.
- Projects.
- Recurring commitments.
- Communication preferences.

### Step 12.4 — Implement semantic memory

Use embeddings and pgvector to retrieve relevant memories even when the user uses different wording.

Combine semantic search with timestamps, categories and importance.

### Step 12.5 — Implement episodic memory

Record important conversational events using the episodic memory engine with:

- Date.
- Topic.
- Participants where relevant.
- Summary.
- Outcome.
- Related memories.

### Step 12.6 — Build unfinished conversation detection

Identify unresolved conversational items using the unresolved discussion tracker:

- Unanswered questions.
- Promises.
- Planned activities.
- Pending decisions.
- Unfinished projects.
- Topics awaiting updates.

Give each item a status:

- Open.
- Waiting for user.
- Waiting for another event.
- Completed.
- Cancelled.
- Expired.

### Step 12.7 — Build conversation follow-up intelligence

Bring up previous discussions using the conversation follow-up engine. The system should evaluate:

1. Is the topic still relevant?
2. Was it already resolved?
3. Is there a reason to bring it up?
4. Is this an appropriate conversational moment?
5. Has the user requested that this topic not be raised?
6. Would mentioning it feel repetitive?

### Step 12.8 — Implement natural conversational behaviour

Support natural conversation using the emotional context engine, which recognizes conversational signals such as:

- Happiness.
- Sadness.
- Frustration.
- Excitement.
- Boredom.
- Confusion.
- Stress.

The engine adjusts tone appropriately, listens and asks relevant questions. Support:

- Greetings.
- Casual conversation.
- Emotional acknowledgement.
- Appropriate humour.
- Follow-up questions.
- Topic transitions.
- Conversation references.
- Personal questions.
- Natural goodbyes.

It should be warm without falsely claiming to have human emotions.

### Step 12.9 — Build proactive conversation

Allow configurable behaviours using the proactive engagement engine:

- Ask about important events.
- Follow up on unfinished topics.
- Ask about progress on goals.
- Check in about planned activities.
- Initiate conversations when permitted.

Include quiet hours, frequency limits and the ability to disable proactive engagement.

### Step 12.10 — Build memory controls

Users must be able to:

- Inspect memories.
- Correct memories.
- Delete memories.
- Disable categories.
- Exclude sensitive topics.
- Control retention.

### Step 12.11 — Build the agent handoff engine (conversation-to-action intelligence)

Classify each conversation item as an instruction, a promise, a goal, a question or casual discussion using conversation-to-action intelligence:

- Personal goal.
- Scheduled reminder.
- Potential task.
- Progress update.
- Information request.
- Casual conversation.
- Potential autonomous project.

The engine must not turn every sentence into a task. It should understand intent and ask for clarification when necessary. When a conversation contains an actionable item, the agent handoff engine converts it into a task and delegates it to the appropriate agent (companion, coding agent, computer agent or life management agent).

### Step 12.12 — Life Management Agent integration

Expose task, schedule and reminder capabilities through a Life Management Agent that shares the central intelligence infrastructure:

- Create and manage TODOs.
- Set reminders and scheduled tasks.
- Track personal organization.
- Hand off organizational work from the companion.

**Completion criteria:** The companion can maintain meaningful conversational continuity over multiple sessions and bring up unresolved topics appropriately.

---


**Roadmap:** [Index](../../overview) · [← Phase 11: Autonomous software engineering agent](phase-11.md) · [Phase 13: Multi-agent orchestration →](phase-13.md)
