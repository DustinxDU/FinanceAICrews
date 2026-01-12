"use client";

import React, { useState, useEffect, useRef, ReactNode } from "react";
import { Link, usePathname } from "@/i18n/routing";
import {
  LayoutDashboard, Workflow, Library, Store, Settings, Zap,
  ChevronRight, ChevronDown, PanelRightOpen, LogOut, Loader2, Radar, X,
  Bot, SendHorizontal, Sparkles, User, Bell, Gauge, Trash2, Search,
  MessageSquare, ExternalLink, Send, Brain
} from "lucide-react";
import { CommandPalette } from "./CommandPalette";
import { useAuth } from "@/contexts/AuthContext";
import { MarketTicker } from "@/components/MarketTicker";
import apiClient, { CopilotMessage } from "@/lib/api";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface NavItem {
  icon: React.ElementType;
  label: string;
  path: string;
}

const navItems: NavItem[] = [
  { icon: Gauge, label: "Cockpit", path: "/cockpit" },
  { icon: LayoutDashboard, label: "Workbench", path: "/dashboard" },
  { icon: Workflow, label: "Crew Builder", path: "/crew-builder" },
  { icon: Library, label: "Library", path: "/library" },
  { icon: Store, label: "Extensions", path: "/mcp" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isTaskDrawerOpen, setIsTaskDrawerOpen] = useState(false);

  const activeTasks = [
    { id: 1, name: "NVDA Deep Dive", progress: "Step 3/12", status: "working" },
  ];

  const handleLogout = () => {
    logout();
  };

  return (
    <>
      <aside className="w-16 hover:w-64 transition-all duration-300 h-screen bg-[var(--bg-panel)] border-r border-[var(--border-color)] flex flex-col items-center hover:items-start group z-40 fixed left-0 top-0 overflow-visible">
        <div className="h-14 flex items-center justify-center w-full border-b border-[var(--border-color)] group-hover:justify-start group-hover:px-4">
          {/* Professional Financial Logo */}
          <div className="relative shrink-0">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Background gradient circle */}
              <defs>
                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
                <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              {/* Outer ring */}
              <circle cx="16" cy="16" r="15" stroke="url(#logoGradient)" strokeWidth="1.5" fill="none" opacity="0.6"/>
              {/* Chart bars - financial symbol */}
              <rect x="8" y="18" width="3" height="8" rx="1" fill="url(#logoGradient)" opacity="0.9"/>
              <rect x="12.5" y="14" width="3" height="12" rx="1" fill="url(#logoGradient)" opacity="0.9"/>
              <rect x="17" y="10" width="3" height="16" rx="1" fill="url(#logoGradient)" opacity="0.9"/>
              <rect x="21.5" y="6" width="3" height="20" rx="1" fill="url(#logoGradient)" opacity="0.9"/>
              {/* Trend line */}
              <path d="M6 22 L10 17 L14.5 20 L18 15 L23 17 L28 11" stroke="url(#logoGradient)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" filter="url(#glow)"/>
              {/* Target indicator */}
              <circle cx="23" cy="17" r="2" fill="#3b82f6"/>
            </svg>
          </div>
          <span className="ml-3 font-bold text-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-blue)] bg-clip-text text-transparent">
            FinanceAI
          </span>
        </div>

        <nav className="flex-1 w-full py-4 flex flex-col gap-2">
          {navItems.map((item) => {
            const isActive = pathname === item.path;
            const Icon = item.icon;
            return (
              <Link key={item.path} href={item.path}
                className={`w-full flex items-center h-12 px-0 group-hover:px-4 justify-center group-hover:justify-start hover:bg-[var(--bg-card)] transition-colors relative ${isActive ? "text-[var(--accent-blue)]" : "text-[var(--text-secondary)]"}`}
                title={item.label}>
                {isActive && <div className="absolute left-0 top-2 bottom-2 w-1 bg-[var(--accent-blue)] rounded-r" />}
                <Icon className="w-5 h-5 shrink-0" />
                <span className="ml-3 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap duration-200">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="w-full px-2 pb-2">
          <button onClick={() => setIsTaskDrawerOpen(!isTaskDrawerOpen)}
            className="w-full h-12 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] flex items-center justify-center group-hover:justify-start group-hover:px-3 hover:border-[var(--accent-green)] transition-all relative overflow-hidden">
            <div className="absolute inset-0 bg-[var(--accent-green)] opacity-5 animate-pulse" />
            <Radar className="w-5 h-5 text-[var(--accent-green)] shrink-0" />
            <div className="ml-3 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap overflow-hidden flex flex-col items-start">
              <span className="text-xs font-bold text-[var(--text-primary)]">{activeTasks.length} Active Tasks</span>
              <span className="text-[10px] text-[var(--text-secondary)]">Click to view</span>
            </div>
          </button>
        </div>

        <div className="w-full p-4 border-t border-[var(--border-color)] flex items-center justify-center group-hover:justify-start">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 shrink-0 cursor-pointer hover:ring-2 hover:ring-[var(--border-color)] transition-all flex items-center justify-center text-white text-xs font-bold" title="User Profile">
            {user?.email?.substring(0, 2).toUpperCase() || "U"}
          </div>
          <div className="ml-3 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap overflow-hidden flex-1">
            <p className="text-sm font-medium">{user?.email?.split("@")[0] || "User"}</p>
            <button onClick={handleLogout} className="text-xs text-[var(--text-secondary)] hover:text-red-400 flex items-center gap-1 mt-0.5">
              <LogOut className="w-3 h-3" /> Sign Out
            </button>
          </div>
        </div>
      </aside>

      {isTaskDrawerOpen && (
        <div className="fixed left-16 bottom-20 w-72 bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl shadow-2xl z-50">
          <div className="p-3 border-b border-[var(--border-color)] flex justify-between items-center">
            <h3 className="font-bold text-sm">Running Tasks</h3>
            <button onClick={() => setIsTaskDrawerOpen(false)} className="text-[var(--text-secondary)] hover:text-white"><X className="w-4 h-4" /></button>
          </div>
          <div className="p-2 space-y-1">
            {activeTasks.map((task) => (
              <Link key={task.id} href="/" className="block p-3 rounded-lg hover:bg-[var(--bg-card)] transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{task.name}</span>
                  <span className="text-[10px] bg-green-900/30 text-green-400 px-1.5 py-0.5 rounded border border-green-900/50">Running</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                  <Loader2 className="w-3 h-3 animate-spin" />{task.progress}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function TopBar({ onToggleCopilot, activeTaskName }: { onToggleCopilot: () => void; activeTaskName?: string | null }) {
  const [notifications] = React.useState([
    { id: 1, message: "New MCP connector available: SEC Edgar", type: "info", time: "2m ago" },
    { id: 2, message: "DeepSeek-V3 model updated with improved reasoning", type: "success", time: "1h ago" },
    { id: 3, message: "Scheduled maintenance: Dec 25, 02:00 UTC", type: "warning", time: "3h ago" }
  ]);
  const [showNotifications, setShowNotifications] = React.useState(false);

  return (
    <header className="h-14 bg-[var(--bg-panel)] border-b border-[var(--border-color)] flex items-center justify-between px-4 ml-16 fixed top-0 right-0 left-0 z-30">
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          {/* Compact Logo for Header */}
          <div className="relative">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="logoGradientHeader" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
                <filter id="glowHeader" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              <circle cx="16" cy="16" r="15" stroke="url(#logoGradientHeader)" strokeWidth="1.5" fill="none" opacity="0.6"/>
              <rect x="8" y="18" width="3" height="8" rx="1" fill="url(#logoGradientHeader)" opacity="0.9"/>
              <rect x="12.5" y="14" width="3" height="12" rx="1" fill="url(#logoGradientHeader)" opacity="0.9"/>
              <rect x="17" y="10" width="3" height="16" rx="1" fill="url(#logoGradientHeader)" opacity="0.9"/>
              <rect x="21.5" y="6" width="3" height="20" rx="1" fill="url(#logoGradientHeader)" opacity="0.9"/>
              <path d="M6 22 L10 17 L14.5 20 L18 15 L23 17 L28 11" stroke="url(#logoGradientHeader)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" filter="url(#glowHeader)"/>
              <circle cx="23" cy="17" r="2" fill="#3b82f6"/>
            </svg>
          </div>
          <span className="font-bold text-lg bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-blue)] bg-clip-text text-transparent">
            FinanceAI
          </span>
        </Link>
        <div className="h-4 w-[1px] bg-[var(--border-color)]" />
        <MarketTicker intervalMs={30000} />
      </div>
      {activeTaskName && (
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-3 bg-blue-900/10 border border-blue-900/30 px-4 py-1.5 rounded-full">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
          </div>
          <span className="text-xs font-medium text-blue-200">Processing: {activeTaskName}...</span>
        </div>
      )}
      <div className="flex items-center gap-4">
        <div className="relative">
          <button 
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 hover:bg-[var(--bg-card)] rounded-lg transition-colors"
          >
            <Bell className="w-5 h-5 text-[var(--text-secondary)]" />
            {notifications.length > 0 && (
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-[var(--accent-green)] rounded-full text-[10px] text-black font-bold flex items-center justify-center">
                {notifications.length}
              </span>
            )}
          </button>
          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl shadow-xl z-50">
              <div className="p-4 border-b border-[var(--border-color)]">
                <h3 className="font-bold text-sm">Notifications</h3>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {notifications.map(notif => (
                  <div key={notif.id} className="p-3 border-b border-[var(--border-color)] last:border-b-0 hover:bg-[var(--bg-panel)] transition-colors">
                    <div className="flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        notif.type === 'success' ? 'bg-green-500' : 
                        notif.type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                      }`} />
                      <div className="flex-1">
                        <p className="text-sm text-[var(--text-primary)]">{notif.message}</p>
                        <p className="text-xs text-[var(--text-secondary)] mt-1">{notif.time}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="h-8 w-[1px] bg-[var(--border-color)]" />
        <button className="btn-icon" onClick={onToggleCopilot} title="Toggle Copilot (Cmd+\)">
          <PanelRightOpen className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}

function CopilotPanel({ isOpen }: { isOpen: boolean }) {
  const pathname = usePathname();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      loadHistory();
    }
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const loadHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const history = await apiClient.getCopilotHistory();
      setMessages(history.messages);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    const userMessage = message.trim();
    setMessage("");
    
    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    
    // 立即添加一个空的助手消息，用于流式更新
    setMessages(prev => [...prev, { role: 'assistant', content: '', thinking: undefined }]);

    setIsLoading(true);
    let fullContent = '';
    let fullThinking = '';

    try {
      await apiClient.streamCopilotMessage(
        userMessage,
        (data) => {
          // 流式接收内容（支持 thinking 模式）
          if (data.type === 'thinking') {
            fullThinking += data.content;
          } else {
            fullContent += data.content;
          }
          setMessages(prev => {
            const updated = [...prev];
            // 更新最后一条助手消息
            updated[updated.length - 1] = {
              role: 'assistant',
              content: fullContent,
              thinking: fullThinking || undefined
            };
            return updated;
          });
        },
        `Current page: ${pathname}`
      );
    } catch (error: any) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { 
          role: 'assistant', 
          content: `Sorry, I encountered an error: ${error.message || 'Unknown error'}` 
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await apiClient.clearCopilotHistory();
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

  const handleQuickQuestion = (question: string) => {
    setMessage(question);
    inputRef.current?.focus();
  };

  return (
    <div className={`fixed right-0 top-14 bottom-0 w-96 bg-[var(--bg-panel)] border-l border-[var(--border-color)] transform transition-transform duration-300 z-20 flex flex-col ${isOpen ? "translate-x-0" : "translate-x-full"}`}>
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)] flex justify-between items-center bg-gradient-to-r from-purple-900/20 to-blue-900/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-sm">FinanceAI Copilot</h3>
            <p className="text-[10px] text-[var(--text-secondary)]">Your AI Financial Assistant</p>
          </div>
        </div>
        <button 
          onClick={handleClearHistory}
          className="p-2 hover:bg-[var(--bg-card)] rounded-lg text-[var(--text-secondary)] hover:text-red-400 transition-colors"
          title="Clear history"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {isLoadingHistory ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-[var(--text-secondary)]" />
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-purple-900/30 to-blue-900/30 flex items-center justify-center">
              <Sparkles className="h-8 w-8 text-purple-400" />
            </div>
            <h4 className="font-bold mb-2">Hi! I'm your AI Copilot</h4>
            <p className="text-sm text-[var(--text-secondary)] mb-6">
              I can help you analyze stocks, explain market trends, and navigate the platform.
            </p>
            <div className="space-y-2">
              <button
                onClick={() => handleQuickQuestion("What's the latest news on AAPL?")}
                className="w-full p-3 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm text-left hover:border-purple-500/50 transition-colors flex items-center gap-2"
              >
                <Search className="w-4 h-4 text-purple-400" />
                What's the latest news on AAPL?
              </button>
              <button
                onClick={() => handleQuickQuestion("How do I use Quick Scan?")}
                className="w-full p-3 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm text-left hover:border-blue-500/50 transition-colors flex items-center gap-2"
              >
                <MessageSquare className="w-4 h-4 text-blue-400" />
                How do I use Quick Scan?
              </button>
              <button
                onClick={() => handleQuickQuestion("Explain RSI indicator")}
                className="w-full p-3 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg text-sm text-left hover:border-green-500/50 transition-colors flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4 text-green-400" />
                Explain RSI indicator
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center shrink-0">
                  <Bot className="h-4 w-4 text-white" />
                </div>
              )}
              <div
                className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                  msg.role === 'user'
                    ? 'bg-[var(--accent-blue)] text-white rounded-br-sm'
                    : 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-bl-sm'
                }`}
              >
                {/* Thinking section (collapsible, default collapsed) */}
                {msg.role === 'assistant' && msg.thinking && (
                  <Collapsible defaultOpen={false} className="mb-2">
                    <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors group">
                      <Brain className="h-3 w-3" />
                      <span>Thinking</span>
                      <ChevronDown className="h-3 w-3 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 p-2 bg-[var(--bg-panel)] rounded-lg text-xs text-[var(--text-secondary)] border-l-2 border-purple-500/50">
                      <div className="whitespace-pre-wrap max-h-32 overflow-y-auto custom-scrollbar">{msg.thinking}</div>
                    </CollapsibleContent>
                  </Collapsible>
                )}
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-[var(--bg-card)] border border-[var(--border-color)] flex items-center justify-center shrink-0">
                  <User className="h-4 w-4 text-[var(--text-secondary)]" />
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] p-3 rounded-2xl rounded-bl-sm">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-[var(--text-secondary)]">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-[var(--border-color)]">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask me anything..."
            className="flex-1 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500/50 transition-colors"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!message.trim() || isLoading}
            className="px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl hover:from-purple-500 hover:to-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}

export function AppLayout({ children, activeTaskName }: { children: ReactNode; activeTaskName?: string | null }) {
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [isCmdKOpen, setIsCmdKOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCmdKOpen((prev) => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
        e.preventDefault();
        setIsCopilotOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setIsCmdKOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)]">
      <Sidebar />
      <TopBar onToggleCopilot={() => setIsCopilotOpen(!isCopilotOpen)} activeTaskName={activeTaskName} />
      <CommandPalette isOpen={isCmdKOpen} onClose={() => setIsCmdKOpen(false)} />
      <main className={`pt-14 pl-16 transition-all duration-300 ${isCopilotOpen ? "pr-96" : ""}`}>
        {children}
      </main>
      <CopilotPanel isOpen={isCopilotOpen} />
    </div>
  );
}
