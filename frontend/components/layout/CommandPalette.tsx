"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "@/i18n/routing";
import { Search, Plus, Cpu, Activity, X } from "lucide-react";

interface Command {
  id: number;
  label: string;
  shortcut?: string;
  icon: React.ElementType;
  action?: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const commands: Command[] = [
    { id: 1, label: "New Analysis", shortcut: "N", icon: Plus, action: () => router.push("/") },
    { id: 2, label: "Search Ticker", shortcut: "S", icon: Search, action: () => router.push("/") },
    { id: 3, label: "Switch to DeepSeek-V3", shortcut: "D", icon: Cpu, action: () => router.push("/settings") },
    { id: 4, label: "View System Status", shortcut: "V", icon: Activity, action: () => router.push("/settings") },
  ];

  const filteredCommands = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = useCallback((cmd: Command) => {
    cmd.action?.();
    onClose();
    setQuery("");
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) {
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredCommands.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
      } else if (e.key === "Enter" && filteredCommands[selectedIndex]) {
        e.preventDefault();
        handleSelect(filteredCommands[selectedIndex]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredCommands, selectedIndex, handleSelect]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-[15vh]">
      <div className="bg-[var(--bg-panel)] w-full max-w-xl border border-[var(--border-color)] rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center px-4 py-3 border-b border-[var(--border-color)]">
          <Search className="w-5 h-5 text-[var(--text-secondary)] mr-3" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or search..."
            className="bg-transparent border-none outline-none text-lg text-[var(--text-primary)] w-full placeholder-[var(--text-secondary)]"
          />
          <button
            onClick={onClose}
            className="text-xs bg-[var(--bg-card)] px-2 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            ESC
          </button>
        </div>

        <div className="py-2">
          <div className="px-4 py-2 text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
            Suggestions
          </div>
          {filteredCommands.map((cmd, index) => {
            const Icon = cmd.icon;
            return (
              <div
                key={cmd.id}
                onClick={() => handleSelect(cmd)}
                className={`px-4 py-3 cursor-pointer flex items-center justify-between group transition-colors ${
                  index === selectedIndex ? "bg-[var(--bg-card)]" : "hover:bg-[var(--bg-card)]"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${index === selectedIndex ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]"}`} />
                  <span className={`${index === selectedIndex ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]"}`}>
                    {cmd.label}
                  </span>
                </div>
                {cmd.shortcut && (
                  <span className="text-xs bg-[var(--bg-app)] px-2 py-1 rounded text-[var(--text-secondary)] border border-[var(--border-color)]">
                    {cmd.shortcut}
                  </span>
                )}
              </div>
            );
          })}
          {filteredCommands.length === 0 && (
            <div className="px-4 py-8 text-center text-[var(--text-secondary)]">
              No commands found
            </div>
          )}
        </div>

        <div className="bg-[var(--bg-card)] px-4 py-2 border-t border-[var(--border-color)] flex justify-between items-center text-xs text-[var(--text-secondary)]">
          <span>Use arrow keys to navigate</span>
          <span>FinanceAI Copilot</span>
        </div>
      </div>
      <div className="absolute inset-0 -z-10" onClick={onClose} />
    </div>
  );
}
