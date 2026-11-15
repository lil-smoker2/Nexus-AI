import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useNotifications } from '@/components/Notifications';

interface HomePageProps {
  apiData: any;
  backendStatus: string;
}

export function HomePage({ apiData, backendStatus }: HomePageProps) {
  const { addNotification } = useNotifications();
  const [clock, setClock] = useState<string>('--:--:--');

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      setClock(now.toLocaleTimeString('en-US', { hour12: false }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleConnect = async () => {
    try {
      const result = await (window as any).__TAURI__.invoke('start_backend');
      if (result === 'started' || result === 'already_running') {
        addNotification({ type: 'success', title: 'Backend started' });
      }
    } catch (e) {
      addNotification({ type: 'error', title: 'Failed to start backend', message: String(e) });
    }
  };

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold">Welcome to NEXUS AI</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <div className="p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-2">Agent Availability</h3>
            <div className="space-y-2">
              {['Companion', 'Coding Agent', 'Computer Agent', 'Life Management'].map((agent) => (
                <div key={agent} className="flex items-center justify-between">
                  <span className="text-sm">{agent}</span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xs font-medium text-emerald-400">Online</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-2">Active Tasks</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Project setup</p>
                  <p className="text-xs text-slate-400">Pending</p>
                </div>
                <div className="w-24 bg-slate-700 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '30%' }} />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Backend config</p>
                  <p className="text-xs text-slate-400">In progress</p>
                </div>
                <div className="w-24 bg-slate-700 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: '60%' }} />
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-2">Weather & Time</h3>
            <div className="flex items-center gap-4">
              <div className="text-2xl">☀️</div>
              <div>
                <p className="text-sm font-medium">Arch Linux Desktop</p>
                <p className="text-xl font-mono font-bold">{clock}</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <div className="p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-4">Backend Status</h3>
          {apiData && (
            <div className="space-y-2 text-sm">
              <p><span className="font-medium text-slate-300">Service:</span> {apiData.name}</p>
              <p><span className="font-medium text-slate-300">Version:</span> {apiData.version}</p>
              <p><span className="font-medium text-slate-300">Status:</span> <span className="text-emerald-400">{apiData.status}</span></p>
            </div>
          )}
          {!apiData && backendStatus === 'connected' && (
            <p className="text-slate-400 text-sm">Fetching backend data…</p>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Button variant="default" className="w-full" onClick={handleConnect}>
          Start Backend
        </Button>
        <Button variant="outline" className="w-full">
          New Coding Task
        </Button>
      </div>
    </div>
  );
}
