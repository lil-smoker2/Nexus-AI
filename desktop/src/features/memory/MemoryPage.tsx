import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface MemoryItem {
  id: string;
  category: string;
  content: string;
  source: string;
  importance: number;
  created_at: string;
}

export function MemoryPage() {
  const [search, setSearch] = useState('');
  const memories: MemoryItem[] = [
    { id: '1', category: 'interests', content: 'User is learning Python programming', source: 'conversation', importance: 8, created_at: '2 days ago' },
    { id: '2', category: 'goals', content: 'User wants to build an e-commerce application', source: 'conversation', importance: 9, created_at: '1 day ago' },
    { id: '3', category: 'preferences', content: 'User prefers dark theme', source: 'settings', importance: 5, created_at: '5 days ago' },
    { id: '4', category: 'projects', content: 'NEXUS AI desktop application', source: 'workspace', importance: 10, created_at: 'Today' },
    { id: '5', category: 'important_events', content: 'Assignment due Friday', source: 'conversation', importance: 7, created_at: '3 days ago' },
  ];

  const filtered = memories.filter((m) =>
    m.content.toLowerCase().includes(search.toLowerCase()) ||
    m.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Memory Centre</h2>
          <p className="text-xs text-slate-400">View, search, and manage stored memories</p>
        </div>
        <Button size="sm">Export</Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex gap-2 mb-6">
          <Input
            placeholder="Search memories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1"
          />
          <Button size="sm">Clear</Button>
        </div>

        <div className="flex gap-4">
          <div className="flex-1 space-y-3">
            {filtered.map((mem) => (
              <div key={mem.id} className="p-3 bg-slate-900 rounded-xl border border-slate-800/50">
                <div className="flex justify-between items-start mb-2">
                  <Badge variant="default" className="text-[10px]">{mem.category}</Badge>
                  <span className="text-[10px] text-slate-500">{mem.created_at}</span>
                </div>
                <p className="text-sm text-slate-200 mb-1">{mem.content}</p>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">Source: {mem.source}</span>
                  <span className="text-[10px] text-slate-500">Importance: {mem.importance}/10</span>
                </div>
                <div className="flex gap-1 mt-2">
                  <Button size="sm" variant="outline">Correct</Button>
                  <Button size="sm" variant="ghost" title="Delete">🗑️</Button>
                </div>
              </div>
            ))}
          </div>

          <div className="w-72 space-y-4">
            <Card className="p-4">
              <h3 className="text-xs font-medium text-slate-400 mb-3 uppercase tracking-wider">Categories</h3>
              <div className="space-y-2">
                {['personal_info', 'preferences', 'interests', 'goals', 'important_events', 'projects', 'recurring_commitments'].map((cat) => (
                  <div key={cat} className="flex items-center justify-between p-2 text-sm rounded bg-slate-800/50">
                    <span className="text-slate-300">{cat.replace('_', ' ')}</span>
                    <span className="text-[10px] text-slate-500">{memories.filter((m) => m.category === cat).length}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="text-xs font-medium text-slate-400 mb-3 uppercase tracking-wider">Controls</h3>
              <div className="space-y-3">
                <Button size="sm" variant="outline" className="w-full">Inspect all memories</Button>
                <Button size="sm" variant="outline" className="w-full">Correct memories</Button>
                <Button size="sm" variant="outline" className="w-full">Delete memories</Button>
                <Button size="sm" variant="outline" className="w-full">Manage retention</Button>
                <Button size="sm" variant="outline" className="w-full">Exclude topics</Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
