"use client";

import React from "react";
import { Users, Bot, Clock, Plus } from "lucide-react";
import { SavedCrew } from "./types";

interface CrewListProps {
  crews: SavedCrew[];
  onSelectCrew: (id: number | 'new') => void;
  isLoading?: boolean;
}

export function CrewList({ crews, onSelectCrew, isLoading }: CrewListProps) {
  return (
    <div className="p-8 max-w-6xl mx-auto h-[calc(100vh-3.5rem)] animate-in fade-in duration-300">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">My Crews</h1>
          <p className="text-[var(--text-secondary)]">Manage your autonomous agent workflows.</p>
        </div>
        <button 
          onClick={() => onSelectCrew('new')}
          className="px-6 py-3 bg-[var(--accent-green)] text-black font-bold rounded-xl hover:bg-emerald-400 transition-all flex items-center gap-2 shadow-lg shadow-green-900/20"
        >
          <Plus className="w-5 h-5" /> Create New Crew
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {crews.map(crew => (
          <div 
            key={crew.id} 
            onClick={() => onSelectCrew(crew.id)}
            className="group bg-[var(--bg-panel)] border border-[var(--border-color)] rounded-xl p-6 hover:border-[var(--accent-blue)] transition-all cursor-pointer hover:shadow-lg relative overflow-hidden"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 rounded-xl bg-[var(--bg-card)] flex items-center justify-center border border-[var(--border-color)] group-hover:border-[var(--accent-blue)] transition-colors">
                <Users className="w-6 h-6 group-hover:text-[var(--accent-blue)] transition-colors" />
              </div>
              <div className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                crew.status === 'active' 
                  ? 'bg-green-900/30 text-green-400' 
                  : 'bg-zinc-800 text-zinc-500'
              }`}>
                {crew.status}
              </div>
            </div>
            
            <h3 className="text-lg font-bold mb-2 group-hover:text-[var(--accent-blue)] transition-colors">{crew.name}</h3>
            <p className="text-sm text-[var(--text-secondary)] line-clamp-2 mb-6 h-10">{crew.description}</p>
            
            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)] border-t border-[var(--border-color)] pt-4">
              <div className="flex items-center gap-1.5">
                <Bot className="w-4 h-4" />
                {crew.agents} Agents
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                {crew.lastRun}
              </div>
            </div>
          </div>
        ))}

        {/* Create New Card (Placeholder style) */}
        <div 
          onClick={() => onSelectCrew('new')}
          className="border-2 border-dashed border-[var(--border-color)] rounded-xl p-6 flex flex-col items-center justify-center text-[var(--text-secondary)] hover:border-[var(--text-primary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] transition-all cursor-pointer group min-h-[200px]"
        >
          <div className="w-16 h-16 rounded-full bg-[var(--bg-panel)] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <Plus className="w-8 h-8" />
          </div>
          <span className="font-bold">Build from Scratch</span>
        </div>
      </div>

      {crews.length === 0 && !isLoading && (
        <div className="text-center py-16">
          <Users className="w-16 h-16 mx-auto mb-4 text-zinc-700" />
          <h3 className="text-xl font-bold text-zinc-400 mb-2">No Crews Yet</h3>
          <p className="text-zinc-500 mb-6">Create your first AI agent crew to get started.</p>
          <button 
            onClick={() => onSelectCrew('new')}
            className="px-6 py-3 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 transition-all"
          >
            Create Your First Crew
          </button>
        </div>
      )}
    </div>
  );
}
