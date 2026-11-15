import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'starting'>('disconnected');
  const [apiData, setApiData] = useState<any>(null);

  const toggleSidebar = () => setSidebarCollapsed(!sidebarCollapsed);
  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  const handleStartBackend = useCallback(async () => {
    setBackendStatus('starting');
    try {
      const result = await invoke<string>('start_backend');
      if (result === 'started' || result === 'already_running') {
        setBackendStatus('connected');
        await fetchApiData();
      } else {
        setBackendStatus('disconnected');
      }
    } catch (e) {
      console.error('Failed to start backend:', e);
      setBackendStatus('disconnected');
    }
  }, []);

  const handleStopBackend = useCallback(async () => {
    try {
      await invoke<string>('stop_backend');
      setBackendStatus('disconnected');
      setApiData(null);
    } catch (e) {
      console.error('Failed to stop backend:', e);
    }
  }, []);

  const checkBackendStatus = useCallback(async () => {
    try {
      const status = await invoke<string>('backend_status');
      if (status === 'running') {
        setBackendStatus('connected');
        await fetchApiData();
      } else {
        setBackendStatus('disconnected');
      }
    } catch (e) {
      setBackendStatus('disconnected');
    }
  }, []);

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

  useEffect(() => {
    checkBackendStatus();
  }, [checkBackendStatus]);

  useEffect(() => {
    const unlistenStart = listen('backend_started', () => {
      setBackendStatus('connected');
      fetchApiData();
    });
    const unlistenStop = listen<'string'>('backend_stopped', () => {
      setBackendStatus('disconnected');
      setApiData(null);
    });

    return () => {
      unlistenStart.then((f) => f());
      unlistenStop.then((f) => f());
    };
  }, [fetchApiData]);

  return (
    <div className={`h-screen w-screen bg-slate-900 text-slate-100 transition-colors duration-300 ${theme === 'light' ? 'bg-slate-50 text-slate-900' : ''}`}>
      <div className="flex h-full w-full overflow-hidden">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-20 transform transition-transform duration-300 ${sidebarCollapsed ? '-translate-x-full' : 'translate-x-0'} bg-slate-950 border-r border-slate-800 w-64 ${theme === 'light' ? 'bg-slate-100 border-slate-200 text-slate-900' : ''}`}
        >
          <div className="flex items-center justify-between h-12 px-4 border-b border-slate-800">
            <span className="font-semibold text-lg tracking-tight">NEXUS AI</span>
            <button onClick={toggleSidebar} className="text-slate-400 hover:text-white">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {sidebarCollapsed ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                )}
              </svg>
            </button>
          </div>
          <nav className="mt-4 px-3 space-y-1">
            <a href="#" className="flex items-center px-3 py-2 text-sm font-medium rounded-lg bg-slate-800 text-slate-300">
              <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>
              Home
            </a>
            <a href="#" className="flex items-center px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white">
              <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Chat
            </a>
            <a href="#" className="flex items-center px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white">
              <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
              Companion
            </a>
            <a href="#" className="flex items-center px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white">
              <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
              Coding Agent
            </a>
            <a href="#" className="flex items-center px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white">
              <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935v5.266l2 1.6V5.535a2 2 0 00-2-1.6M15 8.847V7a2 2 0 00-2-2h-1.172M15 11.847l2-1.6V5.535a2 2 0 00-2-1.6M21 12a9 9 0 11-18 0 9 9 0 0018 0z" /></svg>
              Computer Agent
            </a>
            <a href="#" className="flex items-center px-3 py-2 text-sm font-medium rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white">
              <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C18.832 18.477 17.246 18 15.5 18S12.332 18.477 11 6.253z" /></svg>
              Life Management
            </a>
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

        {/* Main content */}
        <main
          className={`flex-1 h-full overflow-hidden relative ${sidebarCollapsed ? 'ml-0' : 'ml-64'}`}
        >
          {/* Top bar */}
          <header className="h-16 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-900/80 backdrop-blur z-10 ${theme === 'light' ? 'bg-slate-200/80 border-slate-300 text-slate-900' : ''}">
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-semibold">Home</h1>
              <span className="h-5 w-px bg-slate-700 mx-2"></span>
              <span className="text-sm text-slate-400">Dashboard</span>
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

          {/* Dashboard content */}
          <div className="flex-1 overflow-y-auto p-8">
            <div className="max-w-6xl mx-auto">
              <h2 className="text-2xl font-bold mb-8">Welcome to NEXUS AI</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Agent Availability</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Companion</span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span className="text-xs font-medium text-emerald-400">Online</span>
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Coding Agent</span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span className="text-xs font-medium text-emerald-400">Online</span>
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Computer Agent</span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span className="text-xs font-medium text-emerald-400">Online</span>
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Life Management</span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <span className="text-xs font-medium text-emerald-400">Online</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
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

                <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Weather & Time</h3>
                  <div className="flex items-center gap-4">
                    <div className="text-2xl">☀️</div>
                    <div>
                      <p className="text-sm font-medium">Arch Linux Desktop</p>
                      <p className="text-xl font-mono font-bold" id="clock">--:--:--</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
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

              <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
                <h3 className="text-sm font-medium text-slate-400 mb-4">Quick Actions</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button className="flex items-center gap-3 px-4 py-3 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-left">
                    <span className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center">💬</span>
                    <div>
                      <p className="text-sm font-medium">New Conversation</p>
                      <p className="text-xs text-slate-400">Start chatting with the companion</p>
                    </div>
                  </button>
                  <button className="flex items-center gap-3 px-4 py-3 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-left">
                    <span className="w-8 h-8 rounded bg-emerald-600 flex items-center justify-center">🤖</span>
                    <div>
                      <p className="text-sm font-medium">New Coding Task</p>
                      <p className="text-xs text-slate-400">Create a development project</p>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
