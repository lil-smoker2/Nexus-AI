import { useState } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

interface Workspace {
  id: string;
  name: string;
  path: string;
  language: string;
  files: number;
  git: boolean;
  lastOpened: string;
}

export function WorkspacesPage() {
  const [newWorkspace, setNewWorkspace] = useState('');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([
    { id: '1', name: 'nexus-ai', path: '/home/david/Documents/AI', language: 'TypeScript', files: 45, git: true, lastOpened: '2 hours ago' },
    { id: '2', name: 'my-web-app', path: '/home/david/projects/web-app', language: 'React', files: 120, git: true, lastOpened: '1 day ago' },
    { id: '3', name: 'scripts', path: '/home/david/scripts', language: 'Python', files: 15, git: false, lastOpened: '3 days ago' },
  ]);

  const addWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspace.trim()) return;
    setWorkspaces((prev) => [
      ...prev,
      { id: Date.now().toString(), name: newWorkspace, path: `/home/david/projects/${newWorkspace}`, language: 'Unknown', files: 0, git: false, lastOpened: 'Just now' },
    ]);
    setNewWorkspace('');
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Workspaces & Projects</h2>
          <p className="text-xs text-slate-400">Manage your development workspaces</p>
        </div>
        <Button size="sm">Refresh</Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <form onSubmit={addWorkspace} className="flex gap-2 mb-6">
          <Input
            placeholder="Workspace path or name..."
            value={newWorkspace}
            onChange={(e) => setNewWorkspace(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" size="sm">Add Workspace</Button>
        </form>

        <div className="space-y-3">
          {workspaces.map((ws) => (
            <div key={ws.id} className="flex items-center justify-between p-3 bg-slate-900 rounded-xl border border-slate-800/50 group">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white text-sm font-bold">{ws.language.charAt(0)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{ws.name}</p>
                  <p className="text-[10px] text-slate-500 truncate" title={ws.path}>{ws.path}</p>
                  <div className="flex gap-1 text-[10px] text-slate-500 mt-1">
                    <span>{ws.language}</span>
                    <span>• {ws.files} files</span>
                    <span>• {ws.git ? 'Git' : 'No Git'}</span>
                    <span>• {ws.lastOpened}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="outline">Open</Button>
                <Button size="sm" variant="ghost" title="Settings">⚙️</Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
