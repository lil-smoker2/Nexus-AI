import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { NotificationProvider, useNotifications } from '@/components/Notifications';
import { HomePage } from '@/features/home/HomePage';
import { ChatPage } from '@/features/chat/ChatPage';
import { CompanionPage } from '@/features/companion/CompanionPage';
import { CodingPage } from '@/features/coding/CodingPage';
import { ComputerPage } from '@/features/computer/ComputerPage';
import { LifeManagementPage } from '@/features/life-management/LifeManagementPage';
import { TasksPage } from '@/features/tasks/TasksPage';
import { WorkspacesPage } from '@/features/workspaces/WorkspacesPage';
import { MemoryPage } from '@/features/memory/MemoryPage';
import { MCPPage } from '@/features/mcp/MCPPage';
import { ModelsPage } from '@/features/models/ModelsPage';
import { ActivityPage } from '@/features/activity/ActivityPage';
import { SettingsPage } from '@/features/settings/SettingsPage';

const NAV_ITEMS = [
  { label: 'Home', path: 'home', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { label: 'Chat', path: 'chat', icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
  { label: 'Companion', path: 'companion', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
  { label: 'Coding Agent', path: 'coding', icon: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z' },
  { label: 'Computer Agent', path: 'computer', icon: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935v5.266l2 1.6V5.535a2 2 0 00-2-1.6M15 8.847V7a2 2 0 00-2-2h-1.172M15 11.847l2-1.6V5.535a2 2 0 00-2-1.6M21 12a9 9 0 11-18 0 9 9 0 0018 0z' },
  { label: 'Life Management', path: 'life-management', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C18.832 18.477 17.246 18 15.5 18S12.332 18.477 11 6.253z' },
  { label: 'Tasks', path: 'tasks', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { label: 'Workspaces', path: 'workspaces', icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z' },
  { label: 'Memory', path: 'memory', icon: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 10H6v4h12v-4z' },
  { label: 'MCP', path: 'mcp', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { label: 'Models', path: 'models', icon: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5' },
  { label: 'Activity', path: 'activity', icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
  { label: 'Settings', path: 'settings', icon: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z' },
];

const PAGE_COMPONENTS: Record<string, any> = {
  home: HomePage,
  chat: ChatPage,
  companion: CompanionPage,
  coding: CodingPage,
  computer: ComputerPage,
  'life-management': LifeManagementPage,
  tasks: TasksPage,
  workspaces: WorkspacesPage,
  memory: MemoryPage,
  mcp: MCPPage,
  models: ModelsPage,
  activity: ActivityPage,
  settings: SettingsPage,
};

function Sidebar({ collapsed, toggleSidebar, backendStatus, handleStartBackend, handleStopBackend, currentPage, setCurrentPage }: any) {
  return (
    <aside className={`fixed inset-y-0 left-0 z-20 transform transition-transform duration-300 ${collapsed ? '-translate-x-full' : 'translate-x-0'} bg-slate-950 border-r border-slate-800 w-64`}>
      <div className="flex items-center justify-between h-12 px-4 border-b border-slate-800">
        <span className="font-semibold text-lg tracking-tight">NEXUS AI</span>
        <button onClick={toggleSidebar} className="text-slate-400 hover:text-white">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {collapsed ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            )}
          </svg>
        </button>
      </div>
      <nav className="mt-4 px-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = currentPage === item.path;
          return (
            <button
              key={item.label}
              onClick={() => setCurrentPage(item.path)}
              className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${active ? 'bg-slate-800 text-slate-300' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} /></svg>
              {item.label}
            </button>
          );
        })}
      </nav>
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-slate-300">Backend</p>
            <p className={`text-xs font-medium ${backendStatus === 'connected' ? 'text-emerald-400' : backendStatus === 'starting' ? 'text-blue-400' : 'text-rose-400'}`}>
              {backendStatus === 'connected' ? 'Connected' : backendStatus === 'starting' ? 'Starting…' : 'Disconnected'}
            </p>
          </div>
          <button
            onClick={backendStatus === 'connected' ? handleStopBackend : handleStartBackend}
            disabled={backendStatus === 'starting'}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className={`w-2 h-2 rounded-full ${backendStatus === 'connected' ? 'bg-emerald-500' : backendStatus === 'starting' ? 'bg-blue-500 animate-pulse' : 'bg-rose-500'}`}></span>
            {backendStatus === 'connected' ? 'Disconnect' : backendStatus === 'starting' ? 'Starting…' : 'Connect'}
          </button>
        </div>
      </div>
    </aside>
  );
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'starting'>('disconnected');
  const [currentPage, setCurrentPage] = useState('home');
  const [apiData, setApiData] = useState<any>(null);
  const { addNotification } = useNotifications();

  const toggleSidebar = () => setSidebarCollapsed(!sidebarCollapsed);
  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  const handleStartBackend = useCallback(async () => {
    setBackendStatus('starting');
    try {
      const result = await invoke<string>('start_backend');
      if (result === 'started' || result === 'already_running') {
        setBackendStatus('connected');
        addNotification({ type: 'success', title: 'Backend started', message: 'FastAPI backend is running on port 8000' });
        await fetchApiData();
      } else {
        setBackendStatus('disconnected');
      }
    } catch (e) {
      console.error('Failed to start backend:', e);
      addNotification({ type: 'error', title: 'Backend failed to start', message: String(e) });
      setBackendStatus('disconnected');
    }
  }, [addNotification]);

  const handleStopBackend = useCallback(async () => {
    try {
      await invoke<string>('stop_backend');
      setBackendStatus('disconnected');
      setApiData(null);
      addNotification({ type: 'info', title: 'Backend stopped', message: 'FastAPI backend has been stopped' });
    } catch (e) {
      console.error('Failed to stop backend:', e);
      addNotification({ type: 'error', title: 'Backend failed to stop', message: String(e) });
    }
  }, [addNotification]);

  const fetchApiData = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/');
      if (res.ok) {
        const data = await res.json();
        setApiData(data);
      }
    } catch (e) {
      console.warn('Backend API not reachable:', e);
    }
  }, []);

  const PageComponent = PAGE_COMPONENTS[currentPage] || HomePage;

  return (
    <NotificationProvider>
      <div className={`h-screen w-screen bg-slate-900 text-slate-100 transition-colors duration-300 ${theme === 'light' ? 'bg-slate-50 text-slate-900' : ''}`}>
        <div className="flex h-full w-full overflow-hidden">
          <Sidebar
            collapsed={sidebarCollapsed}
            toggleSidebar={toggleSidebar}
            backendStatus={backendStatus}
            handleStartBackend={handleStartBackend}
            handleStopBackend={handleStopBackend}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
          />

          <main className={`flex-1 h-full overflow-hidden relative ${sidebarCollapsed ? 'ml-0' : 'ml-64'}`}>
            <header className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/80 backdrop-blur z-10 ${theme === 'light' ? 'bg-slate-200/80 border-slate-300 text-slate-900' : ''}">
              <div className="flex items-center gap-4">
                <h1 className="text-lg font-semibold">{currentPage.charAt(0).toUpperCase() + currentPage.slice(1).replace('-', ' ')}</h1>
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                  title="Toggle theme"
                >
                  {theme === 'dark' ? '☀️' : '🌙'}
                </button>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto p-8">
              <div className="max-w-6xl mx-auto">
                {currentPage === 'home' ? (
                  <HomePage apiData={apiData} backendStatus={backendStatus} />
                ) : (
                  <PageComponent />
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </NotificationProvider>
  );
}
