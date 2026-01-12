"use client";

import React from "react";
import { Check, Sparkles, TrendingUp, Zap } from "lucide-react";

interface ToolCardProps {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: string;
  serverName?: string;  // MCP server name for display
  icon: React.ReactNode;
  color: string;
  selected: boolean;
  recommended?: boolean;
  trending?: boolean;
  onClick: () => void;
}

export function ToolCard({
  id,
  name,
  displayName,
  description,
  category,
  serverName,
  icon,
  color,
  selected,
  recommended = false,
  trending = false,
  onClick,
}: ToolCardProps) {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-xl border transition-all duration-200 group relative ${
        selected
          ? `${color} border-current bg-opacity-20`
          : 'bg-zinc-900 border-zinc-700 hover:border-zinc-500'
      }`}
    >
      {/* 推荐标签 */}
      {recommended && !selected && (
        <div className="absolute top-2 right-2">
          <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
            color.includes('emerald') 
              ? 'bg-emerald-900/50 text-emerald-400' 
              : color.includes('blue')
              ? 'bg-blue-900/50 text-blue-400'
              : 'bg-purple-900/50 text-purple-400'
          }`}>
            <Sparkles className="w-3 h-3" />
            Recommended
          </div>
        </div>
      )}

      {/* 热门标签 */}
      {trending && !selected && !recommended && (
        <div className="absolute top-2 right-2">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-orange-900/50 text-orange-400">
            <TrendingUp className="w-3 h-3" />
            Popular
          </div>
        </div>
      )}

      <div className="flex items-start gap-3">
        {/* 图标 */}
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
          selected ? `${color} bg-opacity-30` : 'bg-zinc-800'
        }`}>
          {icon}
        </div>

        {/* 内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-sm text-white truncate">
              {displayName}
            </h4>
            {selected && (
              <Check className="w-4 h-4 text-emerald-400 shrink-0" />
            )}
          </div>
          
          <p className="text-xs text-zinc-500 line-clamp-2 mt-1">
            {description}
          </p>

          {/* 标签 */}
          <div className="flex items-center gap-2 mt-2">
            <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">
              {category}
            </span>

            {/* Server name for MCP tools */}
            {serverName && (
              <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-blue-900/30 text-blue-400">
                {serverName}
              </span>
            )}

            {selected && (
              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-emerald-900/30 text-emerald-400">
                <Check className="w-3 h-3" />
                Selected
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 悬停效果 - 快捷提示 */}
      <div className={`absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none ${
        selected ? 'hidden' : ''
      }`} />
    </button>
  );
}
