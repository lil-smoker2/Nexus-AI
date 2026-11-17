import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface MCPTool {
  name: string;
  description?: string;
  inputSchema?: any;
  permission?: string;
}

interface MCPServer {
  id: string;
  name: string;
  description?: string;
  transport: string;
  endpoint: string;
  args?: any[];
  status: 'connected' | 'disconnected' | 'error';
  tools_count: number;
  discovered_tools?: MCPTool[];
}

interface ToolCallResult {
  success: boolean;
  content?: any;
  error?: string;
  tool?: string;
  server_name?: string;
}

const API = 'http://127.0.0.1:8000/api/v1/mcp';

export function MCPPage() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toolName, setToolName] = useState('');
  const [toolArgs, setToolArgs] = useState('{}');
  const [result, setResult] = useState<ToolCallResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const selected = useMemo(() => servers.find(s => s.id === selectedId) || servers[0] || null, [servers, selectedId]);

  useEffect(() => { if (selected && selected.id !== selectedId) setSelectedId(selected.id); }, [selected, selectedId]);
  useEffect(() => { if (selected?.discovered_tools?.length && !toolName) setToolName(selected.discovered_tools[0].name); }, [selected, toolName]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/servers`);
      if (!res.ok) throw new Error(`Failed to load servers (${res.status})`);
      const data = await res.json();
      setServers(data.servers || []);
      if (!selectedId && data.servers?.length) setSelectedId(data.servers[0].id);
    } catch (e: any) {
      setError(e.message || 'Failed to load MCP servers');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function act(serverId: string, action: 'connect' | 'disconnect') {
    setBusy(`${action}:${serverId}`);
    setError(null);
    try {
      const res = await fetch(`${API}/servers/${serverId}/${action}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Action failed (${res.status})`);
      await load();
    } catch (e: any) {
      setError(e.message || 'Action failed');
    } finally {
      setBusy(null);
    }
  }

  async function runTool() {
    if (!selected) return;
    setBusy(`call:${selected.id}`);
    setError(null);
    setResult(null);
    try {
      let args: any = {};
      try { args = toolArgs.trim() ? JSON.parse(toolArgs) : {}; } catch { throw new Error('Arguments must be valid JSON'); }
      const res = await fetch(`${API}/servers/${selected.id}/tools/call`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: toolName, arguments: args }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Tool call failed (${res.status})`);
      setResult(data);
      await load();
    } catch (e: any) {
      setError(e.message || 'Tool call failed');
    } finally {
      setBusy(null);
    }
  }

  const statusVariant = (s: string) => s === 'connected' ? 'success' : s === 'error' ? 'destructive' : 'default';

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="w-80 border-r border-slate-800 flex flex-col bg-slate-950/40">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">MCP Centre</h2>
            <p className="text-[11px] text-slate-400">Manage MCP servers & tools</p>
          </div>
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>{loading ? '...' : 'Refresh'}</Button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {servers.map((server) => (
            <button key={server.id} onClick={() => { setSelectedId(server.id); setToolName(server.discovered_tools?.[0]?.name || ''); setResult(null); }}
              className={`w-full text-left p-3 rounded-xl border ${selected?.id === server.id ? 'border-indigo-500/60 bg-indigo-500/10' : 'border-slate-800/60 bg-slate-900/60 hover:bg-slate-800/50'}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-slate-200">{server.name}</span>
                <Badge variant={statusVariant(server.status) as any} className="text-[10px]">{server.status}</Badge>
              </div>
              <p className="text-[10px] text-slate-500">{server.transport} • {server.tools_count} tools</p>
              <p className="text-[10px] text-slate-500 truncate">{server.endpoint}</p>
            </button>
          ))}
          {!servers.length && !loading && <p className="text-sm text-slate-500 p-2">No MCP servers found.</p>}
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        {error && <div className="m-4 mb-0 p-2 rounded border border-red-500/40 bg-red-500/10 text-red-300 text-xs">{error}</div>}
        {selected ? (
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-xl font-semibold">{selected.name}</h3>
                  <p className="text-sm text-slate-400">{selected.description || 'MCP server'}</p>
                  <p className="text-xs text-slate-500 mt-1">{selected.transport} • {selected.endpoint}</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => act(selected.id, 'connect')} disabled={busy !== null || selected.status === 'connected'}>
                    {busy === `connect:${selected.id}` ? 'Connecting...' : 'Connect'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => act(selected.id, 'disconnect')} disabled={busy !== null || selected.status === 'disconnected'}>
                    {busy === `disconnect:${selected.id}` ? '...' : 'Disconnect'}
                  </Button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(selected.discovered_tools || []).map(t => (
                  <button key={t.name} onClick={() => setToolName(t.name)} className={`px-2 py-1 rounded text-[11px] border ${toolName===t.name?'border-indigo-500 text-indigo-300 bg-indigo-500/10':'border-slate-700 text-slate-300'}`}>
                    {t.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 space-y-3">
              <h4 className="font-medium">Call Tool</h4>
              <div className="grid grid-cols-1 gap-2">
                <label className="text-xs text-slate-400">Tool</label>
                <input value={toolName} onChange={e => setToolName(e.target.value)} className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-sm" placeholder="tool name (e.g. fs.list_directory)" />
                <label className="text-xs text-slate-400">Arguments (JSON)</label>
                <textarea value={toolArgs} onChange={e => setToolArgs(e.target.value)} rows={6} className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-xs font-mono" />
                <div><Button size="sm" onClick={runTool} disabled={busy !== null || !toolName}> {busy === `call:${selected.id}` ? 'Running...' : 'Run Tool'} </Button></div>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/40">
              <h4 className="font-medium mb-2">Result</h4>
              {result ? (
                <pre className="text-xs whitespace-pre-wrap break-words text-slate-200 bg-slate-900/70 p-3 rounded border border-slate-800">{JSON.stringify(result, null, 2)}</pre>
              ) : (
                <p className="text-sm text-slate-500">No tool call yet.</p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500">{loading ? 'Loading MCP servers...' : 'Select a server'}</div>
        )}
      </div>
    </div>
  );
}
