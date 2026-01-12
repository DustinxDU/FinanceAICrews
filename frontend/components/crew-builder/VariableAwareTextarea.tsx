"use client";

import React, { useRef, useState, useEffect } from "react";
import { Variable, ChevronDown, AlertTriangle } from "lucide-react";

interface VariableInfo {
  name: string;
  label?: string;
  type?: string;
}

interface VariableAwareTextareaProps {
  value: string;
  onChange: (value: string) => void;
  availableVars: VariableInfo[];
  placeholder?: string;
  className?: string;
  rows?: number;
  label?: string;
  helpText?: string;
}

/**
 * Extract all {{variable}} patterns from text
 */
export const extractUsedVariables = (text: string): string[] => {
  const matches = text.match(/\{\{(\w+)\}\}/g) || [];
  return [...new Set(matches.map(m => m.replace(/\{\{|\}\}/g, '')))];
};

/**
 * Check which variables are undefined (used but not in availableVars)
 */
export const getUndefinedVariables = (text: string, availableVars: VariableInfo[]): string[] => {
  const usedVars = extractUsedVariables(text);
  const availableNames = availableVars.map(v => v.name);
  return usedVars.filter(v => !availableNames.includes(v));
};

/**
 * Smart textarea component that supports variable insertion from Start node
 * - Dropdown to insert {{variable}} at cursor position
 * - Real-time validation for undefined variables
 * - Visual feedback (red border) for invalid state
 */
export const VariableAwareTextarea: React.FC<VariableAwareTextareaProps> = ({
  value,
  onChange,
  availableVars,
  placeholder,
  className = "",
  rows = 4,
  label,
  helpText
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Track undefined variables for validation
  const undefinedVars = getUndefinedVariables(value || '', availableVars);
  const hasError = undefinedVars.length > 0;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Insert variable at cursor position
  const insertVariable = (varName: string) => {
    const textarea = textareaRef.current;
    if (!textarea) {
      onChange((value || '') + `{{${varName}}}`);
      setIsDropdownOpen(false);
      return;
    }

    const start = cursorPosition ?? textarea.selectionStart ?? value?.length ?? 0;
    const end = textarea.selectionEnd ?? start;
    const before = (value || '').substring(0, start);
    const after = (value || '').substring(end);
    const newValue = `${before}{{${varName}}}${after}`;
    
    onChange(newValue);
    setIsDropdownOpen(false);

    // Restore focus and move cursor after inserted variable
    setTimeout(() => {
      textarea.focus();
      const newCursorPos = start + varName.length + 4; // 4 = length of {{ and }}
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  // Save cursor position before opening dropdown
  const handleOpenDropdown = () => {
    if (textareaRef.current) {
      setCursorPosition(textareaRef.current.selectionStart);
    }
    setIsDropdownOpen(!isDropdownOpen);
  };

  return (
    <div className="relative">
      {/* Label */}
      {label && (
        <label className="text-xs font-bold uppercase text-zinc-400 block mb-2">
          {label}
          {helpText && <span className="text-zinc-500 font-normal ml-2">{helpText}</span>}
        </label>
      )}

      {/* Textarea Container */}
      <div className="relative">
        {/* Insert Variable Button */}
        {availableVars.length > 0 && (
          <div className="absolute top-2 right-2 z-10" ref={dropdownRef}>
            <button
              type="button"
              onClick={handleOpenDropdown}
              className={`flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded border transition-all
                ${isDropdownOpen 
                  ? 'bg-emerald-900/50 border-emerald-500 text-emerald-300' 
                  : 'bg-zinc-800 border-zinc-600 text-zinc-400 hover:border-emerald-500 hover:text-emerald-400'
                }`}
              title="Insert variable from Start node"
            >
              <Variable className="w-3 h-3" />
              <span>{'{x}'}</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && (
              <div className="absolute right-0 mt-1 w-48 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="px-3 py-2 border-b border-zinc-700">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Available Variables</div>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {availableVars.map((v) => (
                    <button
                      key={v.name}
                      onClick={() => insertVariable(v.name)}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-zinc-800 flex items-center justify-between group transition-colors"
                    >
                      <span className="text-emerald-400 font-mono">{`{{${v.name}}}`}</span>
                      <span className="text-[10px] text-zinc-500 group-hover:text-zinc-400">
                        {v.type || 'text'}
                      </span>
                    </button>
                  ))}
                </div>
                {availableVars.length === 0 && (
                  <div className="px-3 py-4 text-center text-xs text-zinc-500">
                    No variables defined in Start node
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          className={`w-full bg-zinc-900 border rounded-lg px-3 py-2 pr-24 text-sm outline-none resize-none text-white transition-colors
            ${hasError 
              ? 'border-red-500/70 focus:border-red-500' 
              : 'border-zinc-700 focus:border-emerald-500'
            }
            ${className}`}
        />
      </div>

      {/* Validation Error */}
      {hasError && (
        <div className="mt-2 p-2 bg-red-900/20 border border-red-500/30 rounded-lg flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs text-red-300 font-medium">Undefined variable{undefinedVars.length > 1 ? 's' : ''}</p>
            <p className="text-xs text-red-200/70 mt-0.5">
              {undefinedVars.map(v => (
                <code key={v} className="bg-red-900/50 px-1 rounded mr-1">{`{{${v}}}`}</code>
              ))}
              <span className="text-red-300/60">not defined in Start node</span>
            </p>
          </div>
        </div>
      )}

      {/* Help text for empty vars */}
      {availableVars.length === 0 && (
        <div className="mt-2 text-xs text-zinc-500 italic">
          💡 Define variables in the Start node to use them here
        </div>
      )}
    </div>
  );
};

export default VariableAwareTextarea;
