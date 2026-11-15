import { useState, useCallback } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

interface ConversationItem {
  id: string;
  content: string;
  role: 'user' | 'companion';
  timestamp: string;
}

interface MemoryItem {
  id: string;
  category: string;
  content: string;
  source: string;
  created_at: string;
}

interface UnresolvedItem {
  id: string;
  topic: string;
  status: 'open' | 'waiting_for_user' | 'completed';
  created_at: string;
}

interface GoalItem {
  id: string;
  title: string;
  progress: number;
  status: 'active' | 'completed';
}

const COMPANION_RESPONSES: Record<string, string[]> = {
  greeting: [
    "Hey! How are you doing?",
    "Good morning! Did you sleep well?",
    "Hey there! What's on your mind today?",
    "Hi! It's lovely to hear from you again.",
  ],
  how_are_you: [
    "I'm doing well, thank you for asking! How are you?",
    "I'm here and ready to help. How about you?",
    "Doing great! What can I do for you today?",
  ],
  bored: [
    "Want to talk about something interesting?",
    "I could tell you about a cool programming concept, or we could just chat.",
    "What kind of topics interest you these days?",
  ],
  tired: [
    "Long day? Have you had some time to rest?",
    "It's important to take breaks. Would you like to talk about something light?",
    "I hear you. Sometimes a good rest is the best thing.",
  ],
  default: [
    "That's interesting. Tell me more.",
    "I'm listening. What else would you like to share?",
    "Hmm, I see. How does that make you feel?",
  ],
};

function getCompanionResponse(userMessage: string): string {
  const msg = userMessage.toLowerCase();
  if (msg.includes('hey') || msg.includes('hi') || msg.includes('hello') || msg.includes('good morning') || msg.includes('goodnight')) {
    const responses = COMPANION_RESPONSES.greeting;
    return responses[Math.floor(Math.random() * responses.length)];
  }
  if (msg.includes('how are you')) {
    const responses = COMPANION_RESPONSES.how_are_you;
    return responses[Math.floor(Math.random() * responses.length)];
  }
  if (msg.includes('bored')) {
    const responses = COMPANION_RESPONSES.bored;
    return responses[Math.floor(Math.random() * responses.length)];
  }
  if (msg.includes('tired') || msg.includes('exhausted')) {
    const responses = COMPANION_RESPONSES.tired;
    return responses[Math.floor(Math.random() * responses.length)];
  }
  const responses = COMPANION_RESPONSES.default;
  return responses[Math.floor(Math.random() * responses.length)];
}

export function CompanionPage() {
  const [messages, setMessages] = useState<ConversationItem[]>([
    {
      id: '1',
      content: "Hey! How are you doing? I'm your personal companion. I'm here to chat, remember things with you, and help you get things done.",
      role: 'companion',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [memories] = useState<MemoryItem[]>([
    {
      id: 'm1',
      category: 'interests',
      content: 'User mentioned learning Python',
      source: 'conversation',
      created_at: new Date().toISOString(),
    },
    {
      id: 'm2',
      category: 'goals',
      content: 'User wants to build an e-commerce application',
      source: 'conversation',
      created_at: new Date().toISOString(),
    },
  ]);
  const [unresolved, setUnresolved] = useState<UnresolvedItem[]>([
    {
      id: 'u1',
      topic: 'Database assignment due Friday',
      status: 'open',
      created_at: new Date().toISOString(),
    },
  ]);
  const [goals] = useState<GoalItem[]>([
    { id: 'g1', title: 'Learn Python', progress: 30, status: 'active' },
    { id: 'g2', title: 'Build e-commerce app', progress: 10, status: 'active' },
  ]);

  const sendMessage = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMsg: ConversationItem = {
      id: Date.now().toString(),
      content: inputValue,
      role: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    const currentInput = inputValue;
    setInputValue('');
    setIsTyping(true);

    // Detect unresolved topics
    if (currentInput.toLowerCase().includes('assignment') || currentInput.toLowerCase().includes('due')) {
      setUnresolved((prev) => [
        ...prev.filter((u) => u.topic !== currentInput),
        { id: Date.now().toString(), topic: currentInput, status: 'open', created_at: new Date().toISOString() },
      ]);
    }

    setTimeout(() => {
      const response = getCompanionResponse(currentInput);
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), content: response, role: 'companion', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      setIsTyping(false);
    }, 1000);
  }, [inputValue]);

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      {/* Left: Conversation */}
      <div className="flex-1 flex flex-col border-r border-slate-800">
        <div className="p-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center text-white font-bold">C</div>
            <div>
              <h2 className="text-lg font-semibold">Companion</h2>
              <p className="text-xs text-slate-400">Personal conversational AI</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] p-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-none rounded-tl-none'
                  : 'bg-slate-800 text-slate-100 rounded-bl-none rounded-tr-none'
              }`}>
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                <span className="text-[10px] text-slate-500 mt-1 block">{msg.timestamp}</span>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="p-3 bg-slate-800 rounded-lg rounded-bl-none rounded-tr-none">
                <div className="flex gap-1">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-pulse" style={{ animationDelay: `${i * 0.2}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-slate-800 bg-slate-950">
          <form onSubmit={sendMessage} className="flex gap-2">
            <Input
              placeholder="Say something to your companion..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={!inputValue.trim()}>
              Send
            </Button>
          </form>
        </div>
      </div>

      {/* Right: Memory, Goals, Unresolved */}
      <div className="w-96 border-l border-slate-800 bg-slate-950 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Memory & Goals</h3>

          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Memories</h4>
              <div className="space-y-2">
                {memories.map((mem) => (
                  <div key={mem.id} className="p-2 bg-slate-900 rounded border border-slate-800/50">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-[10px] font-medium text-slate-500">{mem.category}</span>
                      <span className="text-[10px] text-slate-500">{new Date(mem.created_at).toLocaleDateString()}</span>
                    </div>
                    <p className="text-sm text-slate-200">{mem.content}</p>
                    <p className="text-[10px] text-slate-500 mt-1">Source: {mem.source}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Goals</h4>
              <div className="space-y-3">
                {goals.map((goal) => (
                  <div key={goal.id} className="p-2 bg-slate-900 rounded border border-slate-800/50">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs font-medium text-slate-300">{goal.title}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded ${goal.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-primary/20 text-primary'}`}>{goal.status}</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 mt-1">
                      <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${goal.progress}%` }} />
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">{goal.progress}% complete</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-slate-800 flex-1 overflow-y-auto">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Unresolved Topics</h3>
          <div className="space-y-3">
            {unresolved.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-4">No unresolved topics</p>
            ) : (
              unresolved.map((item) => (
                <div key={item.id} className="p-2 bg-slate-900 rounded border border-slate-800/50">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-medium text-slate-300">{item.topic}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded ${item.status === 'open' ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'}`}>{item.status.replace('_', ' ')}</span>
                  </div>
                  <p className="text-[10px] text-slate-500">{new Date(item.created_at).toLocaleDateString()}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
