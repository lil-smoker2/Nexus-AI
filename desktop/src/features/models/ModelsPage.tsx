import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface Model {
  id: string;
  name: string;
  provider: 'local' | 'cloud';
  status: 'available' | 'unavailable';
  context: string;
  capabilities: string[];
}

export function ModelsPage() {
  const models: Model[] = [
    { id: '1', name: 'llama-3.1-8b', provider: 'local', status: 'available', context: '8192', capabilities: ['text', 'streaming', 'tools'] },
    { id: '2', name: 'codellama-7b', provider: 'local', status: 'available', context: '4096', capabilities: ['text', 'code', 'tools'] },
    { id: '3', name: 'gpt-4', provider: 'cloud', status: 'unavailable', context: '8192', capabilities: ['text', 'streaming', 'tools', 'structured'] },
  ];

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Models & Integrations</h2>
          <p className="text-xs text-slate-400">Configure model providers and integrations</p>
        </div>
        <Button size="sm">Test Connection</Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card className="p-4">
              <h3 className="text-sm font-medium mb-3">Available Models</h3>
              <div className="space-y-3">
                {models.map((m) => (
                  <div key={m.id} className="p-3 rounded border border-slate-800 bg-slate-800/50">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-sm font-medium">{m.name}</span>
                      <Badge variant={m.status === 'available' ? 'success' : 'destructive'} className="text-[10px]">{m.status}</Badge>
                    </div>
                    <div className="flex gap-2 text-[10px] text-slate-500 mb-2">
                      <span>{m.provider}</span>
                      <span>• Context: {m.context}</span>
                    </div>
                    <div className="flex gap-1">
                      {m.capabilities.map((cap) => (
                        <span key={cap} className="text-[10px] bg-slate-700 px-2 py-0.5 rounded">{cap}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="text-sm font-medium mb-3">Provider Configuration</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Local model path</label>
                  <Input placeholder="/path/to/model.gguf" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Cloud API key</label>
                  <Input type="password" placeholder="••••••••" />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Default provider</label>
                  <select className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none">
                    <option>llama-3.1-8b (local)</option>
                    <option>codellama-7b (local)</option>
                    <option>gpt-4 (cloud)</option>
                  </select>
                </div>
                <Button size="sm" className="w-full">Save Configuration</Button>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="p-4">
              <h3 className="text-sm font-medium mb-3">Integrations</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-2 rounded bg-slate-800/50">
                  <span className="text-sm text-slate-200">MCP Servers</span>
                  <Badge variant="default" className="text-[10px]">3 connected</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-slate-800/50">
                  <span className="text-sm text-slate-200">Browser Automation</span>
                  <Badge variant="success" className="text-[10px]">Ready</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-slate-800/50">
                  <span className="text-sm text-slate-200">Calendar</span>
                  <Badge variant="default" className="text-[10px]">Not configured</Badge>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
