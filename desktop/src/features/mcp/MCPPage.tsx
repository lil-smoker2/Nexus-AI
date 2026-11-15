import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface MCPServer {
  id: string;
  name: string;
  transport: 'stdio' | 'streamable_http';
  endpoint: string;
  status: 'connected' | 'disconnected' | 'error';
  tools: number;
}

export function MCPPage() {
  const servers: MCPServer[] = [
    { id: '1', name: 'Filesystem', transport: 'stdio', endpoint: 'npx @modelcontextprotocol/server-filesystem /home/david/documents', status: 'connected', tools: 8 },
    { id: '2', name: 'Terminal', transport: 'stdio', endpoint: 'python -m mcp_terminal_server', status: 'connected', tools: 5 },
    { id: '3', name: 'Browser', transport: 'stdio', endpoint: 'npx @modelcontextprotocol/server-browser', status: 'disconnected', tools: 6 },
    { id: '4', name: 'Database', transport: 'streamable_http', endpoint: 'http://localhost:8080/mcp', status: 'error', tools: 4 },
  ];

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">MCP Centre</h2>
          <p className="text-xs text-slate-400">Manage Model Context Protocol servers</p>
        </div>
        <Button size="sm">Add Server</Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-3">
          {servers.map((server) => (
            <div key={server.id} className="p-3 bg-slate-900 rounded-xl border border-slate-800/50">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-medium text-slate-200">{server.name}</p>
                  <p className="text-[10px] text-slate-500">{server.transport} • {server.tools} tools</p>
                </div>
                <Badge variant={server.status === 'connected' ? 'success' : server.status === 'error' ? 'destructive' : 'default'} className="text-[10px]">
                  {server.status}
                </Badge>
              </div>
              <p className="text-[10px] text-slate-500 truncate mb-2">{server.endpoint}</p>
              <div className="flex gap-1">
                <Button size="sm" variant={server.status === 'connected' ? 'outline' : 'default'} disabled={server.status === 'connected'}>
                  Connect
                </Button>
                <Button size="sm" variant="outline" disabled={server.status === 'connected'}>
                  Disconnect
                </Button>
                <Button size="sm" variant="outline">Tools</Button>
                <Button size="sm" variant="ghost">⚙️</Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
