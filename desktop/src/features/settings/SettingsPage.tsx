import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

export function SettingsPage() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [quietHours, setQuietHours] = useState(false);
  const [proactive, setProactive] = useState(true);

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      <div className="w-72 border-r border-slate-800 bg-slate-950 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-lg font-bold">Settings</h2>
        </div>
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {[
            'General',
            'Appearance',
            'Model Providers',
            'Local Models',
            'Cloud Providers',
            'Agent Behaviour',
            'Memory',
            'Voice',
            'Computer Permissions',
            'Browser Settings',
            'MCP',
            'Integrations',
            'Database & Storage',
            'Notifications & Quiet Hours',
            'Privacy',
            'Logs & Diagnostics',
            'Backup & Restore',
          ].map((section) => (
            <button
              key={section}
              onClick={() => {}}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <span className="w-5 text-center">{section.charAt(0)}</span>
              {section}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl">
          <h2 className="text-xl font-bold mb-6">General Settings</h2>

          <Card className="p-6 mb-6">
            <h3 className="text-sm font-medium mb-4">Appearance</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-200">Theme</p>
                  <p className="text-[10px] text-slate-500">Choose dark or light theme</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={theme === 'dark' ? 'default' : 'outline'}
                    onClick={() => setTheme('dark')}
                  >
                    Dark
                  </Button>
                  <Button
                    size="sm"
                    variant={theme === 'light' ? 'default' : 'outline'}
                    onClick={() => setTheme('light')}
                  >
                    Light
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 mb-6">
            <h3 className="text-sm font-medium mb-4">Proactive Engagement</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-200">Proactive conversations</p>
                  <p className="text-[10px] text-slate-500">Allow companion to initiate conversations</p>
                </div>
                <button
                  onClick={() => setProactive(!proactive)}
                  className="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                      proactive ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          </Card>

          <Card className="p-6 mb-6">
            <h3 className="text-sm font-medium mb-4">Quiet Hours</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-200">Quiet hours</p>
                  <p className="text-[10px] text-slate-500">Disable proactive notifications during set hours</p>
                </div>
                <button
                  onClick={() => setQuietHours(!quietHours)}
                  className="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                      quietHours ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
              {quietHours && (
                <div className="flex gap-2">
                  <Input placeholder="Start time" />
                  <Input placeholder="End time" />
                </div>
              )}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-sm font-medium mb-4">Backup & Restore</h3>
            <div className="space-y-3">
              <Button variant="outline" className="w-full">Backup data</Button>
              <Button variant="outline" className="w-full">Restore from backup</Button>
              <Button variant="outline" className="w-full">Export memories</Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
