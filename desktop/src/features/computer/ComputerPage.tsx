import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface AppItem {
  name: string;
  status: 'running' | 'stopped';
  type: string;
}

const APPS: AppItem[] = [
  { name: 'Firefox', status: 'running', type: 'Browser' },
  { name: 'GNOME Files', status: 'running', type: 'File Manager' },
  { name: 'LibreOffice Writer', status: 'stopped', type: 'Document' },
  { name: 'Terminal', status: 'running', type: 'Terminal' },
  { name: 'VS Code', status: 'stopped', type: 'Editor' },
];

export function ComputerPage() {
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState<string[]>([]);

  const runCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim()) return;
    setOutput((prev) => [...prev, `$ ${command}`]);
    setCommand('');
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      {/* Left: System info */}
      <div className="w-1/3 border-r border-slate-800 bg-slate-950 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-lg font-semibold">System Information</h2>
          <Card className="mt-4 p-4">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Distribution</span>
                <span className="text-slate-200">Arch Linux</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Kernel</span>
                <span className="text-slate-200">6.10.x-arch</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Desktop</span>
                <span className="text-slate-200">GNOME 51.1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Session</span>
                <span className="text-slate-200">Wayland</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">User</span>
                <span className="text-slate-200">david</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Shell</span>
                <span className="text-slate-200">bash</span>
              </div>
            </div>
          </Card>

          <Card className="mt-4 p-4">
            <h3 className="text-xs font-medium text-slate-400 mb-3 uppercase tracking-wider">Resources</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">CPU</span>
                  <span className="text-slate-200">12%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: '12%' }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Memory</span>
                  <span className="text-slate-200">4.2 GB / 16 GB</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '26%' }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Disk</span>
                  <span className="text-slate-200">120 GB / 500 GB</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div className="bg-amber-500 h-2 rounded-full" style={{ width: '24%' }} />
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Right: App control & Terminal */}
      <div className="flex-1 flex flex-col">
        <div className="h-1/2 border-b border-slate-800 flex flex-col">
          <div className="p-4 border-b border-slate-800 bg-slate-950/50">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Application Control</h2>
                <p className="text-xs text-slate-400">Launch, inspect, and manage applications</p>
              </div>
              <Button size="sm">Refresh</Button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              {APPS.map((app) => (
                <div key={app.name} className="flex items-center justify-between p-2 bg-slate-900/50 rounded border border-slate-800/50">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-slate-700 flex items-center justify-center text-sm">{app.name.charAt(0)}</div>
                    <div>
                      <p className="text-sm text-slate-200">{app.name}</p>
                      <p className="text-[10px] text-slate-500">{app.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={app.status === 'running' ? 'success' : 'default'}>{app.status}</Badge>
                    <Button size="sm" variant="outline" disabled={app.status === 'running'}>
                      Launch
                    </Button>
                    <Button size="sm" variant="outline" disabled={app.status === 'stopped'}>
                      Stop
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="h-1/2 flex flex-col border-t border-slate-800">
          <div className="p-4 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Terminal</h2>
              <p className="text-xs text-slate-400">Execute authorized commands</p>
            </div>
            <Badge variant="default">Shell: bash</Badge>
          </div>
          <div className="flex-1 p-4 bg-black/80 text-green-400 font-mono text-sm overflow-y-auto">
            {output.length > 0 ? output.map((line, i) => <div key={i}>{line}</div>) : (
              <div className="text-slate-500">Welcome to the terminal. Type a command below.</div>
            )}
            <div className="mt-2 text-slate-300">david@archlinux:~$ <span className="text-white">_</span></div>
          </div>
          <div className="p-3 border-t border-slate-800 bg-slate-950">
            <form onSubmit={runCommand} className="flex gap-2">
              <Input
                placeholder="Enter command..."
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                className="flex-1"
              />
              <Button type="submit">Run</Button>
            </form>
            <p className="text-[10px] text-slate-500 mt-1">Commands require approval for destructive or privileged operations.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
