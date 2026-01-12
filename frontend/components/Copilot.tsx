"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, X, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/lib/api";

interface CopilotProps {
  jobId: string | null;
  chatHistory: ChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  isOpen: boolean;
  onToggle: () => void;
}

export function Copilot({
  jobId,
  chatHistory,
  onSendMessage,
  isLoading,
  isOpen,
  onToggle,
}: CopilotProps) {
  const [message, setMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && jobId) {
      onSendMessage(message.trim());
      setMessage("");
    }
  };

  if (!isOpen) {
    return (
      <Button
        onClick={onToggle}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg"
        size="icon"
      >
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-background border rounded-lg shadow-xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">AI Assistant</h3>
        </div>
        <Button variant="ghost" size="icon" onClick={onToggle}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!jobId ? (
          <div className="text-center text-muted-foreground py-8">
            <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-sm">Select a completed analysis task to discuss the report with AI Assistant</p>
          </div>
        ) : chatHistory.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <p className="text-sm mb-4">You can ask questions about the analysis report, such as:</p>
            <div className="space-y-2 text-xs">
              <button
                onClick={() => onSendMessage("Why are you bullish on this stock?")}
                className="block w-full p-2 bg-muted rounded hover:bg-muted/80 transition-colors"
                disabled={isLoading}
              >
                &quot;Why are you bullish on this stock?&quot;
              </button>
              <button
                onClick={() => onSendMessage("What are the main risks?")}
                className="block w-full p-2 bg-muted rounded hover:bg-muted/80 transition-colors"
                disabled={isLoading}
              >
                &quot;What are the main risks?&quot;
              </button>
              <button
                onClick={() => onSendMessage("What signals do technical indicators show?")}
                className="block w-full p-2 bg-muted rounded hover:bg-muted/80 transition-colors"
                disabled={isLoading}
              >
                &quot;What signals do technical indicators show?&quot;
              </button>
            </div>
          </div>
        ) : (
          chatHistory.map((msg, index) => (
            <div
              key={index}
              className={cn(
                "flex gap-3",
                msg.role === "user" ? "flex-row-reverse" : ""
              )}
            >
              <div
                className={cn(
                  "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                {msg.role === "user" ? (
                  <User className="h-4 w-4" />
                ) : (
                  <Bot className="h-4 w-4" />
                )}
              </div>
              <div
                className={cn(
                  "rounded-lg p-3 max-w-[80%] text-sm",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
              <Bot className="h-4 w-4" />
            </div>
            <div className="bg-muted rounded-lg p-3">
              <div className="flex gap-1">
                <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce" />
                <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.2s]" />
                <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            placeholder={jobId ? "输入您的问题..." : "请先选择分析任务"}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!jobId || isLoading}
          />
          <Button type="submit" size="icon" disabled={!jobId || isLoading || !message.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
