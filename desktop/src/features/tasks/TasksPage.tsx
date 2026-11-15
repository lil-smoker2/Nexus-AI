import { useState } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface TaskItem {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'blocked';
  priority: 'low' | 'medium' | 'high';
  assignee?: string;
  dueDate?: string;
  tags: string[];
}

const STATUS_BADGE: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'outline' | 'secondary'> = {
  pending: 'default',
  in_progress: 'default',
  completed: 'success',
  blocked: 'destructive',
};

export function TasksPage() {
  const [newTask, setNewTask] = useState('');
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed' | 'blocked'>('all');
  const [tasks, setTasks] = useState<TaskItem[]>([
    { id: '1', title: 'Configure FastAPI backend', status: 'completed', priority: 'high', assignee: 'system', dueDate: 'Today', tags: ['backend', 'setup'] },
    { id: '2', title: 'Implement chat messaging', status: 'completed', priority: 'high', assignee: 'frontend', dueDate: 'Today', tags: ['frontend', 'chat'] },
    { id: '3', title: 'Build file copy/delete widgets', status: 'in_progress', priority: 'medium', assignee: 'frontend', dueDate: 'Tomorrow', tags: ['frontend', 'file-ops'] },
    { id: '4', title: 'Add model provider integration', status: 'pending', priority: 'high', assignee: 'backend', dueDate: 'Next week', tags: ['backend', 'models'] },
    { id: '5', title: 'Implement MCP filesystem server', status: 'pending', priority: 'medium', assignee: 'backend', dueDate: 'Next week', tags: ['mcp', 'filesystem'] },
  ]);

  const addTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    setTasks((prev) => [
      ...prev,
      { id: Date.now().toString(), title: newTask, status: 'pending', priority: 'medium', assignee: undefined, dueDate: undefined, tags: [] },
    ]);
    setNewTask('');
  };

  const setStatus = (id: string, status: TaskItem['status']) => {
    setTasks((prev) => prev.map((t) => t.id === id ? { ...t, status } : t));
  };

  const filtered = tasks.filter((t) => filter === 'all' || t.status === filter);

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="p-6 border-b border-slate-800 bg-slate-950/50 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Task Management</h2>
          <p className="text-xs text-slate-400">Create, track, and organize all tasks</p>
        </div>
        <Button size="sm">Export</Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <form onSubmit={addTask} className="flex gap-2 mb-6">
          <Input
            placeholder="New task title..."
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" size="sm">Add Task</Button>
        </form>

        <div className="flex gap-2 mb-6">
          {(['all', 'pending', 'completed', 'blocked'] as const).map((f) => (
            <Button
              key={f}
              size="sm"
              variant={filter === f ? 'default' : 'outline'}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </Button>
          ))}
        </div>

        <div className="space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-10 text-sm text-slate-400">
              No tasks match this filter.
            </div>
          ) : (
            filtered.map((task) => (
              <div key={task.id} className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800/50">
                <Badge variant={STATUS_BADGE[task.status]} className="text-[10px]">
                  {task.status.replace('_', ' ')}
                </Badge>
                <Badge variant="default" className="text-[10px] bg-slate-800 text-slate-300">
                  {task.priority}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 truncate">{task.title}</p>
                  <div className="flex gap-2 text-[10px] text-slate-500 mt-1">
                    {task.assignee && <span>• {task.assignee}</span>}
                    {task.dueDate && <span>• {task.dueDate}</span>}
                    {task.tags.map((tag) => <span key={tag}>• #{tag}</span>)}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button size="icon" variant="ghost" onClick={() => setStatus(task.id, 'pending')}>⏳</Button>
                  <Button size="icon" variant="ghost" onClick={() => setStatus(task.id, 'in_progress')}>▶️</Button>
                  <Button size="icon" variant="ghost" onClick={() => setStatus(task.id, 'completed')}>✅</Button>
                  <Button size="icon" variant="ghost" onClick={() => setStatus(task.id, 'blocked')}>🚫</Button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
