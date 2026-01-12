"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send, Bot, User, X, MessageSquare, Loader2,
  Sparkles, Trash2, Search, ExternalLink, Brain, ChevronDown
} from "lucide-react";
import apiClient, { CopilotMessage } from "@/lib/api";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface GlobalCopilotProps {
  context?: string;  // 当前页面上下文
}

export function GlobalCopilot({ context }: GlobalCopilotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  // Streaming state for thinking mode
  const [currentThinking, setCurrentThinking] = useState("");
  const [currentContent, setCurrentContent] = useState("");
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

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    setIsLoading(true);
    // Reset streaming state
    setCurrentThinking("");
    setCurrentContent("");

    try {
      // Add a placeholder for assistant message
      setMessages(prev => [...prev, { role: 'assistant', content: '', thinking: undefined }]);

      let fullContent = '';
      let fullThinking = '';

      await apiClient.streamCopilotMessage(
        userMessage,
        (data) => {
          if (data.type === 'thinking') {
            fullThinking += data.content;
            setCurrentThinking(fullThinking);
          } else {
            fullContent += data.content;
            setCurrentContent(fullContent);
          }
          // Update the last message with current state
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              lastMsg.content = fullContent;
              lastMsg.thinking = fullThinking || undefined;
            }
            return newMessages;
          });
        },
        context
      );

      // Clear streaming state after completion
      setCurrentThinking("");
      setCurrentContent("");
    } catch (error: any) {
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = `Sorry, I encountered an error: ${error.message || 'Unknown error'}`;
        }
        return newMessages;
      });
      setCurrentThinking("");
      setCurrentContent("");
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

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 transition-all flex items-center justify-center z-50 group"
        title="Open Copilot"
      >
        <Sparkles className="h-6 w-6 text-white group-hover:scale-110 transition-transform" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-[400px] h-[600px] bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-2xl shadow-2xl flex flex-col z-50 animate-in slide-in-from-bottom-4 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)] bg-gradient-to-r from-purple-900/20 to-blue-900/20 rounded-t-2xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-sm">FinanceAI Copilot</h3>
            <p className="text-[10px] text-[var(--text-secondary)]">Your AI Financial Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button 
            onClick={handleClearHistory}
            className="p-2 hover:bg-[var(--bg-card)] rounded-lg text-[var(--text-secondary)] hover:text-red-400 transition-colors"
            title="Clear history"
          >
            <Trash2 className="h-4 w-4" />
          </button>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-2 hover:bg-[var(--bg-card)] rounded-lg text-[var(--text-secondary)] hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
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

        {/* Streaming thinking indicator */}
        {isLoading && currentThinking && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="max-w-[80%] bg-[var(--bg-card)] border border-[var(--border-color)] p-3 rounded-2xl rounded-bl-sm">
              <Collapsible defaultOpen={false}>
                <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors group">
                  <Brain className="h-3 w-3 animate-pulse text-purple-400" />
                  <span>Thinking...</span>
                  <ChevronDown className="h-3 w-3 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 p-2 bg-[var(--bg-panel)] rounded-lg text-xs text-[var(--text-secondary)] border-l-2 border-purple-500/50">
                  <div className="whitespace-pre-wrap max-h-32 overflow-y-auto custom-scrollbar">{currentThinking}</div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          </div>
        )}

        {isLoading && !currentThinking && (
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

export default GlobalCopilot;
