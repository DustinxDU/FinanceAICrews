'use client';

import React, { useMemo, useState } from 'react';
import { MappedEvent } from './eventMapper';

interface TimelineNavProps {
  events: MappedEvent[];
  onEventClick: (eventId: string) => void;
  startTime?: string;
  totalDurationMs?: number;
}

type MarkerType = 'thought' | 'tool' | 'agent_output' | 'final';

interface TimelineMarker {
  id: string;
  type: MarkerType;
  position: number; // 0-100 percentage
  label: string;
  color: string;
  timestamp: string;
}

export const TimelineNav = ({ events, onEventClick }: TimelineNavProps) => {
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);

  const markers = useMemo(() => {
    if (events.length === 0) return [];

    const firstTime = new Date(events[0].timestamp).getTime();
    const lastTime = new Date(events[events.length - 1].timestamp).getTime();
    const duration = Math.max(lastTime - firstTime, 1000); // Avoid div by zero

    return events
      .map(event => {
        const time = new Date(event.timestamp).getTime();
        const position = ((time - firstTime) / duration) * 100;
        
        let type: MarkerType = 'thought';
        let color = '#60A5FA'; // blue
        let label = 'Thinking';

        switch (event.type) {
          case 'tool_call':
            type = 'tool';
            color = '#FBBF24'; // yellow
            label = 'Tool Call';
            break;
          case 'agent_output':
            type = 'agent_output';
            color = '#22D3EE'; // cyan
            label = 'Output';
            break;
          case 'status':
            if ((event.content as any).status === 'completed') {
              type = 'final';
              color = '#34D399'; // green
              label = 'Completed';
            }
            break;
        }

        // Filter out less important events to avoid clutter?
        // For now, keep thought, tool, output
        if (!['thought', 'tool_call', 'agent_output', 'status'].includes(event.type)) {
          return null;
        }

        return {
          id: event.id,
          type,
          position,
          label,
          color,
          timestamp: event.timestamp
        } as TimelineMarker;
      })
      .filter((m): m is TimelineMarker => m !== null);
  }, [events]);

  return (
    <div className="relative h-8 w-full bg-gray-900/50 border-b border-gray-800 flex items-center px-4 overflow-hidden group">
      {/* Timeline Line */}
      <div className="absolute left-4 right-4 h-0.5 bg-gray-800" />

      {/* Markers */}
      <div className="relative w-full h-full">
        {markers.map((marker) => (
          <button
            key={marker.id}
            onClick={() => onEventClick(marker.id)}
            onMouseEnter={() => setHoveredEventId(marker.id)}
            onMouseLeave={() => setHoveredEventId(null)}
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full hover:w-3 hover:h-3 hover:z-10 transition-all cursor-pointer"
            style={{ 
              left: `${marker.position}%`, 
              backgroundColor: marker.color,
              zIndex: hoveredEventId === marker.id ? 20 : 1
            }}
          >
            {/* Tooltip */}
            <div className={`absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-800 text-xs px-2 py-1 rounded border border-gray-700 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity ${hoveredEventId === marker.id ? 'visible' : 'invisible'}`}>
              <div className="font-semibold text-gray-200">{marker.label}</div>
              <div className="text-[10px] text-gray-500">{new Date(marker.timestamp).toLocaleTimeString()}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
