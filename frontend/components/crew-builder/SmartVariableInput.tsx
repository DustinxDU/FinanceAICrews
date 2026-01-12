"use client";

import React, { useState, useMemo, useRef } from "react";
import { 
  Variable, AlertCircle, Lightbulb, Copy 
} from "lucide-react";

interface Variable {
  name: string;
  type: string;
  source?: string;
  description?: string;
  options?: string[];
}

interface SmartVariableInputProps {
  value: string;
  onChange: (value: string) => void;
  availableVars: Variable[];
  placeholder?: string;
  label?: string;
  helpText?: string;
  rows?: number;
  disabled?: boolean;
  required?: boolean;
}

export function SmartVariableInput({
  value,
  onChange,
  availableVars,
  placeholder = "",
  label,
  helpText,
  rows = 3,
  disabled = false,
  required = false,
}: SmartVariableInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // 检测当前输入的变量前缀
  const currentPrefix = useMemo(() => {
    const beforeCursor = value.substring(0, cursorPosition);
    const lastOpenBrace = beforeCursor.lastIndexOf('{{');
    const lastCloseBrace = beforeCursor.lastIndexOf('}}');
    
    // 只有在未闭合的 {{ 之后才显示建议
    if (lastOpenBrace > lastCloseBrace) {
      return beforeCursor.substring(lastOpenBrace + 2, cursorPosition);
    }
    return null;
  }, [value, cursorPosition]);

  // 过滤匹配的变量
  const filteredVars = useMemo(() => {
    if (!currentPrefix || !showSuggestions) return [];
    
    const prefix = currentPrefix.toLowerCase();
    return availableVars
      .filter(v => v.name.toLowerCase().includes(prefix))
      .slice(0, 10); // 限制显示 10 个结果
  }, [currentPrefix, availableVars, showSuggestions]);

  // 处理光标位置变化
  const handleCursorChange = () => {
    if (textareaRef.current) {
      setCursorPosition(textareaRef.current.selectionStart);
    }
  };

  // 插入变量
  const insertVariable = (variableName: string) => {
    if (!currentPrefix) return;
    
    const beforeCursor = value.substring(0, cursorPosition);
    const afterCursor = value.substring(cursorPosition);
    const lastOpenBrace = beforeCursor.lastIndexOf('{{');
    
    const newValue = 
      beforeCursor.substring(0, lastOpenBrace + 2) +
      variableName +
      '}}' +
      afterCursor;
    
    onChange(newValue);
    setShowSuggestions(false);
    
    // 恢复焦点
    setTimeout(() => {
      if (textareaRef.current) {
        const newCursorPos = lastOpenBrace + 2 + variableName.length + 2;
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        setCursorPosition(newCursorPos);
      }
    }, 0);
  };

  // 复制变量名
  const copyVariableName = (variableName: string) => {
    navigator.clipboard.writeText(`{{${variableName}}}`);
  };

  // 键盘导航
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showSuggestions || filteredVars.length === 0) return;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % filteredVars.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredVars.length) % filteredVars.length);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      if (filteredVars[selectedIndex]) {
        insertVariable(filteredVars[selectedIndex].name);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setShowSuggestions(false);
    }
  };

  // 检测变量使用
  const usedVars = useMemo(() => {
    const regex = /\{\{(\w+)\}\}/g;
    const matches = value.match(regex);
    return matches ? Array.from(new Set(matches.map(m => m.replace(/\{\{|\}\}/g, '')))) : [];
  }, [value]);

  // 验证变量
  const validation = useMemo(() => {
    const usedVarNames = usedVars;
    const availableVarNames = availableVars.map(v => v.name);
    const missingVars = usedVarNames.filter(name => !availableVarNames.includes(name));
    
    return {
      isValid: missingVars.length === 0,
      missingVars,
      usedCount: usedVars.length,
    };
  }, [usedVars, availableVars]);

  return (
    <div className="relative">
      {label && (
        <div className="flex items-center gap-2 mb-2">
          <label className="text-xs font-bold uppercase text-zinc-400">
            {label}
            {required && <span className="text-red-400 ml-1">*</span>}
          </label>
          {!validation.isValid && (
            <div className="flex items-center gap-1 text-xs text-red-400">
              <AlertCircle className="w-3 h-3" />
              <span>{validation.missingVars.length} missing</span>
            </div>
          )}
        </div>
      )}

      <div className="relative">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onClick={handleCursorChange}
          onKeyUp={handleCursorChange}
          onSelect={handleCursorChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={rows}
          disabled={disabled}
          className={`w-full bg-zinc-900 border rounded-lg px-3 py-2 text-sm outline-none resize-none transition-colors ${
            !validation.isValid
              ? 'border-red-500 focus:border-red-500'
              : 'border-zinc-700 focus:border-emerald-500'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          style={{ fontFamily: 'monospace' }}
        />
        
        {/* 变量建议下拉框 */}
        {showSuggestions && filteredVars.length > 0 && (
          <div 
            className="absolute left-0 right-0 top-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-50 overflow-hidden max-h-60 overflow-y-auto"
            onMouseDown={(e) => e.preventDefault()}
          >
            {filteredVars.map((variable, index) => (
              <button
                key={variable.name}
                onClick={(e) => {
                  e.preventDefault();
                  insertVariable(variable.name);
                }}
                onMouseEnter={() => setSelectedIndex(index)}
                className={`w-full text-left px-4 py-2 flex items-center gap-3 transition-colors ${
                  index === selectedIndex
                    ? 'bg-emerald-600 text-white'
                    : 'hover:bg-zinc-800 text-zinc-300'
                }`}
              >
                <div className="flex items-center gap-2 flex-1">
                  <Variable className="w-4 h-4 text-emerald-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {`{${variable.name}}`}
                    </div>
                    {variable.description && (
                      <div className="text-xs text-zinc-500 truncate">
                        {variable.description}
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    copyVariableName(variable.name);
                  }}
                  className="p-1 text-zinc-500 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Copy variable name"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </button>
            ))}
          </div>
        )}

        {/* 无匹配变量提示 */}
        {showSuggestions && currentPrefix && filteredVars.length === 0 && (
          <div className="absolute left-0 right-0 top-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl z-50 p-4">
            <div className="flex items-center gap-2 text-sm text-zinc-400">
              <Lightbulb className="w-4 h-4 text-yellow-500" />
              <span>
                No variables match <strong>{currentPrefix}</strong>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 帮助文本 */}
      {helpText && (
        <div className="mt-2 flex items-start gap-2 text-xs text-zinc-500">
          <Lightbulb className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
          <p>{helpText}</p>
        </div>
      )}

      {/* 已使用的变量显示 */}
      {usedVars.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-xs uppercase text-zinc-500">
            Used variables:
          </span>
          {usedVars.map(varName => {
            const isAvailable = availableVars.some(v => v.name === varName);
            return (
              <span
                key={varName}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                  isAvailable
                    ? 'bg-blue-900/30 text-blue-300'
                    : 'bg-red-900/30 text-red-300'
                }`}
              >
                {isAvailable ? (
                  <Variable className="w-3 h-3" />
                ) : (
                  <AlertCircle className="w-3 h-3" />
                )}
                {varName}
              </span>
            );
          })}
        </div>
      )}

      {/* 缺失变量提示 */}
      {!validation.isValid && (
        <div className="mt-3 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-red-300">
                Undefined variables detected
              </div>
              <div className="text-xs text-red-400 mt-1">
                {validation.missingVars.map(v => `{${v}}`).join(', ')} are not defined. 
                Define them in the Start node or fix the references.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 快速变量提示 */}
      {usedVars.length === 0 && availableVars.length > 0 && (
        <div className="mt-3 p-3 bg-emerald-900/10 border border-emerald-500/30 rounded-lg">
          <div className="flex items-start gap-2">
            <Lightbulb className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
            <div className="text-xs text-emerald-400">
              <p className="font-medium mb-1">Quick Tip</p>
              <p>
                Type <code className="bg-zinc-900 px-1 rounded">{`{ { }`}</code> to see available variables. 
                Use arrow keys to navigate, Enter to select.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
