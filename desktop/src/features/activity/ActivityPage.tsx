import { Button } from '@/components/ui/Button';

interface EventItem {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  agent?: string;
}

export function ActivityPage() {
  const events: EventItem[] = [
    { id: '1', type: 'agent.started', description: 'Coding agent started task: Implement chat messaging', timestamp: '2 minutes ago', agent: 'coding' },
    { id: '2', type: 'task.completed', description: 'Task completed: Configure FastAPI backend', timestamp: '15 minutes ago', agent: 'system' },
    { id: '3', type: 'tool.called', description: 'Tool called: filesystem.read (main.py)', timestamp: '30 minutes ago', agent: 'coding' },
    { id: '4', type: 'tool.verified', description: 'Tool verified: file copy main.py → copy_of_main.py', timestamp: '45 minutes ago', agent: 'coding' },
    { id: '5', type: 'mcp.connected', description: 'MCP server connected: Filesystem', timestamp: '1 hour ago', agent: 'system' },
    { id: '6', type: 'conversation.created', description: 'New conversation started with companion', timestamp: '2 hours ago', agent: 'companion' },
  ];

  const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
    'agent.started': { color: 'bg-blue-500/20 text-blue-400', label: 'Agent Started' },
    'task.completed': { color: 'bg-emerald-500/20 text-emerald-400', label: 'Task Completed' },
    'tool.called': { color: 'bg-primary/20 text-primary', label: 'Tool Called' },
    'tool.verified': { color: 'bg-emerald-500/20 text-emerald-400', label: 'Tool Verified' },
    'mcp.connected': { color: 'bg-purple-500/20 text-purple-400', label: 'MCP Connected' },
    'conversation.created': { color: 'bg-pink-500/20 text-pink-400', label: 'Conversation' },
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Activity & History</h2>
          <p className="text-xs text-slate-400">View agent events and execution history</p>
        </div>
        <Button size="sm">Export Log</Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-3">
          {events.map((ev: EventItem) => {
            const config = TYPE_CONFIG[ev.type] || { color: 'bg-slate-500/20 text-slate-400', label: 'Event' };
            return (
              <div key={ev.id} className="flex items-start gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800/50">
                <div className="w-8 h-8 rounded flex items-center justify-center text-xs font-bold mb-1" style={{ backgroundColor: config.color.includes('blue') ? '#1e3a8a' : config.color.includes('emerald') ? '#064e3b' : config.color.includes('purple') ? '#4c1d95' : config.color.includes('pink') ? '#7f1d1d' : '#334155', color: '#fff' }}>
                  {ev.type.split('.')[0].charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-2 py-0.5 rounded ${config.color}`}>{config.label}</span>
                    {ev.agent && (
                      <span className="text-[10px] text-slate-500">{ev.agent}</span>
                    )}
                  </div>
                  <p className="text-sm text-slate-200">{ev.description}</p>
                  <span className="text-[10px] text-slate-500">{ev.timestamp}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
