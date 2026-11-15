import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface TaskItem {
  id: string;
  title: string;
  category: string;
  dueDate?: string;
  completed: boolean;
  priority: 'low' | 'medium' | 'high';
}

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

const PRIORITY_BADGE_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'outline' | 'secondary'> = {
  low: 'default',
  medium: 'warning',
  high: 'destructive',
};

export function LifeManagementPage() {
  const [newTask, setNewTask] = useState('');
  const [tasks, setTasks] = useState<TaskItem[]>([
    { id: '1', title: 'Finish database assignment', category: 'Academic', dueDate: 'Friday', completed: false, priority: 'high' },
    { id: '2', title: 'Organize Downloads folder', category: 'Computer management', dueDate: 'Today', completed: false, priority: 'medium' },
    { id: '3', title: 'Pay rent', category: 'Personal reminder', dueDate: '1st of month', completed: false, priority: 'high' },
    { id: '4', title: 'Review pull request', category: 'Work', dueDate: 'Tomorrow', completed: true, priority: 'medium' },
  ]);

  const addTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    setTasks((prev) => [
      ...prev,
      { id: Date.now().toString(), title: newTask, category: 'General', dueDate: undefined, completed: false, priority: 'medium' },
    ]);
    setNewTask('');
  };

  const toggleTask = (id: string) => {
    setTasks((prev) => prev.map((t) => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const completedCount = tasks.filter((t) => t.completed).length;
  const totalCount = tasks.length;

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      {/* Left: Task list */}
      <div className="w-2/5 border-r border-slate-800 bg-slate-950 flex flex-col">
        <div className="p-4 border-b border-slate-800 bg-slate-950/50">
          <h2 className="text-lg font-semibold">Tasks & Reminders</h2>
          <p className="text-xs text-slate-400 mt-1">{completedCount} of {totalCount} completed</p>
          <div className="w-full bg-slate-800 rounded-full h-2 mt-2">
            <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${totalCount === 0 ? 0 : (completedCount / totalCount) * 100}%` }} />
          </div>
        </div>

        <div className="p-4">
          <form onSubmit={addTask} className="flex gap-2 mb-4">
            <Input
              placeholder="New task..."
              value={newTask}
              onChange={(e) => setNewTask(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" size="sm">Add</Button>
          </form>

          <div className="space-y-2">
            {tasks.map((task) => (
              <div key={task.id} className="flex items-center gap-3 p-2 bg-slate-900 rounded border border-slate-800/50">
                <input
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => toggleTask(task.id)}
                  className="w-4 h-4 text-primary"
                />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${task.completed ? 'line-through text-slate-500' : 'text-slate-200'}`}>{task.title}</p>
                  <p className="text-[10px] text-slate-500">{task.category} • {task.dueDate || 'No due date'}</p>
                </div>
                <Badge variant={PRIORITY_BADGE_VARIANT[task.priority]}>{PRIORITY_LABELS[task.priority]}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Schedule & summaries */}
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-slate-800 bg-slate-950/50">
          <h2 className="text-lg font-semibold">Schedule</h2>
          <p className="text-xs text-slate-400 mt-1">Upcoming reminders and recurring activities</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <Card className="p-4">
              <h3 className="text-sm font-medium mb-3">Today</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-2 rounded bg-slate-800/50">
                  <div>
                    <p className="text-sm font-medium">Organize Downloads folder</p>
                    <p className="text-xs text-slate-400">Computer management • Due today</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline">Snooze</Button>
                    <Button size="sm">Complete</Button>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="text-sm font-medium mb-3">This Week</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-2 rounded bg-slate-800/50">
                  <div>
                    <p className="text-sm font-medium">Finish database assignment</p>
                    <p className="text-xs text-slate-400">Academic • Due Friday</p>
                  </div>
                  <Badge variant="warning">High priority</Badge>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-slate-800/50">
                  <div>
                    <p className="text-sm font-medium">Pay rent</p>
                    <p className="text-xs text-slate-400">Personal reminder • 1st of month</p>
                  </div>
                  <Badge variant="warning">High priority</Badge>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="text-sm font-medium mb-3">Daily Summary</h3>
              <div className="space-y-2 text-sm">
                <p className="text-slate-300">You have {totalCount - completedCount} pending tasks.</p>
                <p className="text-slate-300">{completedCount} tasks completed today.</p>
                <p className="text-slate-300">2 high-priority items need attention this week.</p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
