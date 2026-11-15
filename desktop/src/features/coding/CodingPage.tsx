import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';

interface FileItem {
  name: string;
  type: 'file' | 'directory';
  size: string;
  modified: string;
}

const MOCK_FILES: FileItem[] = [
  { name: 'src/', type: 'directory', size: '-', modified: '2 hours ago' },
  { name: 'main.py', type: 'file', size: '2.4 KB', modified: '1 hour ago' },
  { name: 'requirements.txt', type: 'file', size: '450 B', modified: '3 hours ago' },
  { name: 'README.md', type: 'file', size: '3.1 KB', modified: '5 hours ago' },
  { name: 'tests/', type: 'directory', size: '-', modified: '4 hours ago' },
  { name: 'config.yaml', type: 'file', size: '1.2 KB', modified: '6 hours ago' },
];

export function CodingPage() {
  const [projectPath, setProjectPath] = useState('/home/user/projects/my-app');
  const [copiedFiles, setCopiedFiles] = useState<{ original: string; copy: string }[]>([]);
  const [showSpecsMoved, setShowSpecsMoved] = useState<boolean>(false);

  const handleCopyFile = useCallback((fileName: string) => {
    const copyName = `copy_of_${fileName}`;
    setCopiedFiles((prev) => [...prev, { original: fileName, copy: copyName }]);
    setShowSpecsMoved(true);
    setTimeout(() => setShowSpecsMoved(false), 3000);
  }, []);

  const handleDeleteFile = useCallback((fileName: string) => {
    if (window.confirm(`Are you sure you want to delete "${fileName}"?`)) {
      console.log('Deleted:', fileName);
    }
  }, []);

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      {/* Left: File Explorer */}
      <div className="w-1/3 border-r border-slate-800 bg-slate-950 flex flex-col">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white text-sm font-bold">P</div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{projectPath.split('/').pop()}</p>
            <p className="text-[10px] text-slate-500 truncate">{projectPath}</p>
          </div>
          <Button size="sm" variant="outline" onClick={() => setProjectPath('/home/user/projects/new-project')}>
            Change
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          <div className="space-y-1">
            {MOCK_FILES.map((file) => (
              <div
                key={file.name}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800 cursor-pointer group"
              >
                <div className="w-6 h-6 flex-shrink-0">
                  {file.type === 'directory' ? '📁' : '📄'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 truncate">{file.name}</p>
                  <p className="text-[10px] text-slate-500">{file.size} • {file.modified}</p>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100">
                  <Button size="icon" variant="ghost" onClick={(e) => { e.stopPropagation(); handleCopyFile(file.name); }} title="Copy">
                    📋
                  </Button>
                  <Button size="icon" variant="ghost" onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.name); }} title="Delete">
                    🗑️
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {copiedFiles.length > 0 && (
          <div className="p-4 border-t border-slate-800 bg-slate-900/50">
            <h4 className="text-xs font-medium text-slate-400 mb-3 uppercase tracking-wider">Recent Copies</h4>
            <div className="space-y-2">
              {copiedFiles.map((cf, idx) => (
                <div key={idx} className="flex items-center gap-2 p-2 bg-slate-800/50 rounded border border-slate-800/30">
                  <div className="w-4 h-4 rounded bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[10px]">📋</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-300 truncate" title={cf.original}>{cf.original}</p>
                    <p className="text-[10px] text-emerald-400 truncate" title={cf.copy}>&rarr; {cf.copy}</p>
                  </div>
                  <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right: Code Editor & Comparison */}
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">File Editor</h2>
              <p className="text-xs text-slate-400">View and edit project files</p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline">Save</Button>
              <Button size="sm">Run</Button>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 bg-slate-950/50 border border-slate-800/50 rounded-xl overflow-hidden">
          {showSpecsMoved && (
            <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-300 text-sm">
              ✅ Specs moved from original to copied file. Both files verified.
            </div>
          )}
          <div className="flex h-full gap-4">
            {/* Original file panel */}
            <div className="flex-1 flex flex-col border-r border-slate-800/50">
              <div className="p-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Original: main.py</span>
                <span className="text-[10px] text-slate-500">2.4 KB</span>
              </div>
              <div className="flex-1 p-4 font-mono text-sm text-slate-300 overflow-auto">
`def hello_world():\n    """Greet the user with a friendly message."""\n    print("Hello, World!")\n    return "success"\n\nif __name__ == "__main__":\n    hello_world()`
              </div>
            </div>

            {/* Copied file panel */}
            <div className="flex-1 flex flex-col border-l border-slate-800/50">
              <div className="p-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Copy: copy_of_main.py</span>
                <span className="text-[10px] text-slate-500">2.4 KB</span>
              </div>
              <div className="flex-1 p-4 font-mono text-sm text-emerald-300 overflow-auto">
`def hello_world():\n    """Greet the user with a friendly message."""\n    print("Hello, World!")\n    return "success"\n\n# Specs moved here\nCONFIG_VERSION = "1.0.0"\n\nif __name__ == "__main__":\n    hello_world()`
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-slate-800/50 rounded border border-slate-800">
            <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Tool Activity</h4>
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span className="text-slate-300">File copied: main.py → copy_of_main.py</span>
                <span className="ml-auto text-[10px] text-slate-500">Just now</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                <span className="text-slate-300">Specs verified and moved</span>
                <span className="ml-auto text-[10px] text-slate-500">Just now</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
