import { useState, useCallback, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/Modal';

interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  created_at: string;
  metadata?: any;
}

interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadConversations = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/chat');
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
        if (data.length > 0 && !selectedConversation) {
          setSelectedConversation(data[0]);
        }
      }
    } catch (e) {
      console.warn('Failed to load conversations:', e);
    }
  }, [selectedConversation]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id);
    }
  }, [selectedConversation]);

  const loadMessages = useCallback(async (conversationId: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/${conversationId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.warn('Failed to load messages:', e);
    }
  }, []);

  const createConversation = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Conversation' }),
      });
      if (res.ok) {
        const conv = await res.json();
        setConversations((prev) => [conv, ...prev]);
        setSelectedConversation(conv);
      }
    } catch (e) {
      console.warn('Failed to create conversation:', e);
    }
  }, []);

  const sendMessage = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !selectedConversation) return;

    const userMessage: Message = {
      id: 'temp-' + Date.now(),
      conversation_id: selectedConversation.id,
      role: 'user',
      content: inputValue,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = inputValue;
    setInputValue('');
    setIsLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/chat/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: selectedConversation.id, content: currentInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [...prev, data.message]);
        // Refresh conversation list to update timestamp
        await loadConversations();
      }
    } catch (e) {
      console.warn('Failed to send message:', e);
    } finally {
      setIsLoading(false);
    }
  }, [inputValue, selectedConversation, loadConversations]);

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-900">
      {/* Conversation list sidebar */}
      <div className="hidden lg:flex flex-col w-80 border-r border-slate-800 bg-slate-950">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-lg font-semibold">Conversations</h2>
          <Button variant="outline" size="sm" onClick={createConversation} className="w-full mt-3">
            New Conversation
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.length === 0 ? (
            <div className="text-center py-10 text-sm text-slate-400">
              No conversations yet. Create one to start chatting.
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => setSelectedConversation(conv)}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedConversation?.id === conv.id
                      ? 'bg-slate-800 text-slate-100'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                  }`}
                >
                  <div className="flex-1 truncate">{conv.title}</div>
                  <span className="text-xs text-slate-500">{new Date(conv.updated_at).toLocaleDateString()}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {!selectedConversation ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <EmptyState title="Select a conversation" description="Choose a conversation from the list or create a new one." />
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">{selectedConversation.title}</h2>
                <p className="text-xs text-slate-400">{selectedConversation.id}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="success">Connected</Badge>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-20 text-sm text-slate-400">
                  No messages yet. Send a message to start the conversation.
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${
                        msg.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[80%] p-3 rounded-lg ${
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground rounded-tr-none rounded-tl-none'
                            : 'bg-slate-800 text-slate-100 rounded-bl-none rounded-tr-none'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        <span className="text-[10px] text-slate-500 mt-1 block">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            <div className="p-3 border-t border-slate-800 bg-slate-950">
              <form onSubmit={sendMessage} className="flex gap-2">
                <Input
                  placeholder="Type a message..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={isLoading}
                  className="flex-1"
                />
                <Button type="submit" disabled={isLoading || !inputValue.trim()}>
                  {isLoading ? 'Sending…' : 'Send'}
                </Button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
