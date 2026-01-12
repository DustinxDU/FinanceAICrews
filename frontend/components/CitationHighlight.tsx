"use client";

import { useState, useMemo } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { BookOpen, FileText, Brain, TrendingDown, Sparkles } from "lucide-react";

interface Citation {
  source_name: string;
  display_name?: string;
  description?: string;
  category?: string;
  is_valid?: boolean;
}

interface CitationHighlightProps {
  text: string;
  citations?: Citation[];
  className?: string;
}

const CITATION_REGEX = /\[Source:\s*([^\]]+)\]/gi;

const getCategoryIcon = (category?: string) => {
  switch (category) {
    case "market_history":
      return <TrendingDown className="h-3 w-3" />;
    case "strategy":
      return <Brain className="h-3 w-3" />;
    case "macro":
      return <Sparkles className="h-3 w-3" />;
    case "sector":
      return <FileText className="h-3 w-3" />;
    default:
      return <FileText className="h-3 w-3" />;
  }
};

const getCategoryColor = (category?: string) => {
  switch (category) {
    case "market_history":
      return "bg-red-100 text-red-700 border-red-200";
    case "strategy":
      return "bg-purple-100 text-purple-700 border-purple-200";
    case "macro":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "sector":
      return "bg-green-100 text-green-700 border-green-200";
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
};

const getCategoryLabel = (category?: string) => {
  const labels: Record<string, string> = {
    market_history: "Market History",
    strategy: "Investment Strategy",
    macro: "Macroeconomics",
    sector: "Sector Research",
  };
  return category ? labels[category] || category : "Knowledge Source";
};

export function CitationHighlight({
  text,
  citations = [],
  className = "",
}: CitationHighlightProps) {
  const [hoveredCitation, setHoveredCitation] = useState<string | null>(null);

  // Build citation information mapping
  const citationMap = useMemo(() => {
    const map = new Map<string, Citation>();
    citations.forEach((c) => {
      map.set(c.source_name.toLowerCase(), c);
    });
    return map;
  }, [citations]);

  // Parse text and highlight citations
  const renderHighlightedText = () => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    const regex = new RegExp(CITATION_REGEX.source, "gi");

    while ((match = regex.exec(text)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(
          <span key={`text-${lastIndex}`}>
            {text.slice(lastIndex, match.index)}
          </span>
        );
      }

      const sourceName = match[1].trim();
      const citation = citationMap.get(sourceName.toLowerCase()) || {
        source_name: sourceName,
      };

      // Add highlighted citation
      parts.push(
        <CitationBadge
          key={`citation-${match.index}`}
          citation={citation}
          isHovered={hoveredCitation === sourceName}
          onHover={() => setHoveredCitation(sourceName)}
          onLeave={() => setHoveredCitation(null)}
        />
      );

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(<span key={`text-${lastIndex}`}>{text.slice(lastIndex)}</span>);
    }

    return parts;
  };

  return (
    <TooltipProvider>
      <div className={`citation-highlight ${className}`}>
        {renderHighlightedText()}
      </div>
    </TooltipProvider>
  );
}

interface CitationBadgeProps {
  citation: Citation;
  isHovered: boolean;
  onHover: () => void;
  onLeave: () => void;
}

function CitationBadge({
  citation,
  isHovered,
  onHover,
  onLeave,
}: CitationBadgeProps) {
  const categoryColor = getCategoryColor(citation.category);
  const isValid = citation.is_valid !== false;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={`
            inline-flex items-center gap-1 mx-0.5 cursor-pointer
            transition-all duration-200
            ${isValid ? categoryColor : "bg-yellow-100 text-yellow-700 border-yellow-200"}
            ${isHovered ? "ring-2 ring-offset-1 ring-purple-400" : ""}
          `}
          onMouseEnter={onHover}
          onMouseLeave={onLeave}
        >
          {getCategoryIcon(citation.category)}
          <span className="text-xs">
            {citation.display_name || citation.source_name}
          </span>
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-purple-500" />
            <span className="font-medium">
              {citation.display_name || citation.source_name}
            </span>
          </div>
          {citation.category && (
            <Badge variant="secondary" className="text-xs">
              {getCategoryLabel(citation.category)}
            </Badge>
          )}
          {citation.description && (
            <p className="text-xs text-muted-foreground">
              {citation.description}
            </p>
          )}
          <p className="text-xs text-muted-foreground italic">
            File: {citation.source_name}
          </p>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

// Utility function to extract citations
export function extractCitations(text: string): string[] {
  const citations: string[] = [];
  let match;
  const regex = new RegExp(CITATION_REGEX.source, "gi");

  while ((match = regex.exec(text)) !== null) {
    const sourceName = match[1].trim();
    if (!citations.includes(sourceName)) {
      citations.push(sourceName);
    }
  }

  return citations;
}

// Check if text contains citations
export function hasCitations(text: string): boolean {
  return CITATION_REGEX.test(text);
}

// Count number of citations
export function countCitations(text: string): number {
  const matches = text.match(new RegExp(CITATION_REGEX.source, "gi"));
  return matches ? new Set(matches.map((m) => m.toLowerCase())).size : 0;
}

export default CitationHighlight;
