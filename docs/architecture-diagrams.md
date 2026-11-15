# NEXUS AI — Architecture Diagrams

**Status:** Draft — Phase 0, Step 0.2  
**Source:** NEXUS_AI_Revised_Master_Roadmap.md

## 1. Component architecture

The chat UI is a frontend composition over these services, not a separate AI execution layer:

```mermaid
flowchart LR
    Nav["Navigation rail"] --> Chat["Conversation view"]
    Avatar["Companion stage"] --> Chat
    Chat --> Composer["Message composer"]
    Chat --> Context["Context panel"]
    Context --> Activity["Approved activity summaries"]
    Context --> Memory["Memory service"]
    Chat <--> API["REST / WebSocket API"]
    API <--> Orchestrator["Backend orchestrator"]
    API <--> DB["Conversation and memory storage"]
```

The companion avatar is a presentation element. Agent status, messages, activity summaries, and memories must be sourced from their respective application services.

```mermaid
graph TD
    subgraph Desktop["Desktop Layer (Tauri)"]
        UI["React + TypeScript UI<br/>Tailwind CSS"]
        Commands["Tauri Commands<br/>(scoped desktop integration)"]
        Events["Tauri Events<br/>(frontend notification)"]
    end

    subgraph Backend["Backend Layer (Python + FastAPI)"]
        API["FastAPI REST API<br/>Pydantic validation"]
        WS["WebSocket Server<br/>(event streaming)"]
        Orchestrator["Central Orchestrator<br/>request classification & delegation"]
        Agents["Agents<br/>Companion • Coding • Computer • Life Management"]
        Tools["Tool Registry & Executor<br/>permission-checked execution"]
        Memory["Memory Service<br/>working / long-term / episodic"]
        MCP["MCP Client Manager<br/>server connections & tool discovery"]
        Scheduler["Scheduler / Background Worker<br/>reminders & recurring tasks"]
        Permissions["Permission Service<br/>categories & approvals"]
        Exec["Persistent Execution Engine<br/>state, checkpoints, recovery"]
        DB["Database Layer<br/>SQLite + repository layer"]
        Logging["Logging & Observability<br/>events, audit, metrics"]
    end

    subgraph External["External Systems"]
        Models["Local & Cloud LLM Providers<br/>(llama.cpp, cloud adapters)"]
        MCP_Servers["External MCP Servers<br/>(stdio / Streamable HTTP)"]
        OS["Arch Linux OS & GNOME Wayland<br/>(D-Bus, GIO, AT-SPI2, portals)"]
        FS["Filesystem<br/>authorized directories"]
        Browser["Browser<br/>(Playwright automation)"]
    end

    UI <--> Commands
    Commands <--> API
    API <--> WS
    WS <--> Events
    API <--> Orchestrator
    Orchestrator <--> Agents
    Agents <--> Tools
    Agents <--> Memory
    Agents <--> MCP
    Agents <--> Scheduler
    Agents <--> Permissions
    Orchestrator <--> Exec
    Orchestrator <--> DB
    Orchestrator <--> Logging
    API <--> DB
    Tools <--> FS
    Tools <--> OS
    MCP <--> MCP_Servers
    Models <--> Agents
    OS <--> Browser
```

## 2. Agent interaction / orchestration flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Frontend UI
    participant API as Backend API
    participant O as Orchestrator
    participant C as Companion Agent
    participant CM as Coding Agent
    participant CP as Computer Agent
    participant LM as Life Management Agent
    participant T as Tool Executor
    participant DB as Database

    U->>UI: sends message or action
    UI->>API: POST /api/v1/message
    API->>O: route request
    O->>O: classify intent & risk level
    alt casual conversation
        O->>C: handle conversation
        C-->>O: natural response
    else actionable request
        O->>O: select agent(s)
        O->>CM: delegate coding task
        O->>CP: delegate computer task
        O->>LM: delegate organization task
        CM->>T: request tool execution
        T->>T: permission check
        T->>FS: execute filesystem operation
        FS-->>T: result
        T->>T: verify result
        T-->>CM: verified result
        CM-->>O: completion report
        O->>DB: persist execution state
    end
    O-->>API: aggregated result
    API-->>UI: WebSocket event + response
    UI-->>U: display result
```

## 3. Data flow — user request to verified result

```mermaid
flowchart TD
    A[User input<br/>(chat, voice, command)] --> B[Frontend UI]
    B --> C[WebSocket / REST API]
    C --> D[Orchestrator]
    D --> E{Intent classification}
    E -->|Casual| F[Companion Agent<br/>natural response]
    E -->|Actionable| G[Select agent(s)<br/>Companion / Coding / Computer / Life Mgmt]
    G --> H[Build context<br/>memory + permissions]
    H --> I[Agent proposes action]
    I --> J[Permission check]
    J -->|Denied| K[Request user approval]
    J -->|Granted| L[Tool Executor]
    L --> M[Execute operation]
    M --> N[Post-action verification]
    N -->|Failed| O[Retry / replan / report error]
    N -->|Succeeded| P[Record result + verification evidence]
    P --> Q[Update execution state<br/>checkpoint persisted]
    Q --> R[Aggregate result]
    R --> S[Return to Companion]
    S --> T[WebSocket event to frontend]
    T --> U[Display to user]
```

## 4. Execution state (persistent)

```mermaid
graph TD
    EID[Execution ID] --> Obj[User objective]
    Obj --> Plan[Plan version]
    Plan --> Curr[Current task]
    Curr --> Done[Completed tasks]
    Curr --> Pend[Pending tasks]
    Done --> TC[Tool calls & results]
    Pend --> TC
    TC --> Err[Errors & retries]
    Err --> Ckpt[Checkpoints]
    Ckpt --> Approval[Approval & permission decisions]
    Approval --> VE[Verification evidence]
    VE --> FR[Final report]
    FR --> Persist[Persisted in database<br/>survives crash & restart]
```

## 5. Permission flow

```mermaid
flowchart TD
    A[Tool request from agent] --> B[Resolve permission category<br/>read/write/modify/delete/execute/install/network/credentials/financial/administrative]
    B --> C{Agent has permission?}
    C -->|No| D[Reject - unauthorized]
    C -->|Yes| E{Resource in allowed scope?}
    E -->|No| F[Reject - out of scope]
    E -->|Yes| G{Risky operation?}
    G -->|Yes| H[Request user approval<br/>narrowly scoped]
    H -->|Granted| I[Execute with audit log]
    H -->|Denied| J[Reject - approval denied]
    G -->|No| I
    I --> K[Record tool call & result]
    K --> L[Post-action verification]
```

## 6. Backend lifecycle (Tauri manages Python process)

```mermaid
stateDiagram-v2
    [*] --> BackendStopped
    BackendStopped --> Starting: Tauri launch command
    Starting --> Ready: health-check OK
    Ready --> Running: frontend connects
    Running --> Ready: idle
    Running --> Stopping: shutdown / crash
    Stopping --> BackendStopped: process exited
    Stopping --> Starting: auto-restart on crash
    Ready --> BackendStopped: manual stop
```
