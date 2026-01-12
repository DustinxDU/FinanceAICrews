/**
 * Report DSL Generator
 *
 * Converts analysis results to AntV Infographic DSL format.
 * Uses valid template IDs from @antv/infographic library.
 *
 * Available templates:
 * - list-grid-simple: Grid layout for metrics/stats
 * - list-row-simple-horizontal-arrow: Horizontal list with arrows
 * - sequence-steps-simple: Step-by-step process
 * - sequence-timeline-plain-text: Timeline layout
 * - compare-swot: SWOT analysis layout
 * - chart-column-simple: Simple column chart
 *
 * @see https://github.com/antvis/Infographic
 */

import { RunSummary } from '@/lib/types';

export interface ReportData {
  ticker?: string;
  crewName?: string;
  content: string;
  summary?: RunSummary;
  metrics?: Record<string, number | string>;
  insights?: string[];
  recommendation?: 'buy' | 'sell' | 'hold' | 'neutral';
}

/**
 * Generates a complete analysis report DSL using a single valid template
 */
export function generateReportDSL(data: ReportData): string {
  const { ticker, crewName, content, summary, metrics, insights, recommendation } = data;

  // Parse key metrics from content if not provided
  const parsedData = parseAnalysisContent(content);
  const finalMetrics = metrics || parsedData.metrics;
  const finalInsights = insights || parsedData.insights;
  const finalRecommendation = recommendation || parsedData.recommendation;

  // Build items array for the infographic
  const items: Array<{ label: string; value?: string; desc?: string }> = [];

  // Add title item
  const title = ticker ? `${ticker} Analysis Report` : 'Analysis Report';

  // Add metrics as items
  if (finalMetrics && Object.keys(finalMetrics).length > 0) {
    Object.entries(finalMetrics).slice(0, 4).forEach(([label, value]) => {
      items.push({ label, value: String(value) });
    });
  }

  // Add summary stats if available
  if (summary) {
    items.push({ 
      label: 'Duration', 
      value: formatDuration(summary.total_duration_ms) 
    });
    if (summary.total_tokens) {
      items.push({ 
        label: 'Tokens', 
        value: summary.total_tokens.toLocaleString() 
      });
    }
    if (summary.tool_calls_count) {
      items.push({ 
        label: 'Tool Calls', 
        value: String(summary.tool_calls_count) 
      });
    }
  }

  // Add recommendation if available
  if (finalRecommendation) {
    const recommendLabels: Record<string, string> = {
      buy: 'BUY - Positive outlook',
      sell: 'SELL - Consider exit',
      hold: 'HOLD - Monitor position',
      neutral: 'NEUTRAL - Wait for signals',
    };
    items.push({
      label: 'Recommendation',
      value: recommendLabels[finalRecommendation] || finalRecommendation.toUpperCase(),
    });
  }

  // Add insights as items with descriptions
  if (finalInsights && finalInsights.length > 0) {
    finalInsights.slice(0, 3).forEach((insight, i) => {
      items.push({
        label: `Insight ${i + 1}`,
        desc: insight.substring(0, 100),
      });
    });
  }

  // Generate DSL with valid template
  const itemsDSL = items
    .map(item => {
      let itemStr = `    - label ${escapeValue(item.label)}`;
      if (item.value) {
        itemStr += `\n      value ${escapeValue(item.value)}`;
      }
      if (item.desc) {
        itemStr += `\n      desc ${escapeValue(item.desc)}`;
      }
      return itemStr;
    })
    .join('\n');

  // Use list-grid-simple for a clean grid layout
  return `infographic list-grid-simple
data
  title ${escapeValue(title)}
  items
${itemsDSL}
theme dark`.trim();
}

/**
 * Escape special characters in DSL values
 */
function escapeValue(value: string): string {
  // Remove newlines and excessive whitespace
  return value.replace(/[\n\r]+/g, ' ').replace(/\s+/g, ' ').trim();
}

/**
 * Parse analysis content to extract structured data
 */
function parseAnalysisContent(content: string): {
  metrics: Record<string, number | string>;
  insights: string[];
  recommendation?: 'buy' | 'sell' | 'hold' | 'neutral';
} {
  const metrics: Record<string, number | string> = {};
  const insights: string[] = [];
  let recommendation: 'buy' | 'sell' | 'hold' | 'neutral' | undefined;

  // Extract price-related metrics
  const priceMatch = content.match(/price[:\s]+\$?([\d,.]+)/i);
  if (priceMatch) {
    metrics['Price'] = `$${priceMatch[1]}`;
  }

  // Extract P/E ratio
  const peMatch = content.match(/P\/E[:\s]*([\d.]+)/i);
  if (peMatch) {
    metrics['P/E'] = parseFloat(peMatch[1]);
  }

  // Extract market cap
  const mcMatch = content.match(/market\s*cap[:\s]*\$?([\d.]+[BMT]?)/i);
  if (mcMatch) {
    metrics['Mkt Cap'] = mcMatch[1];
  }

  // Extract growth metrics
  const growthMatch = content.match(/growth[:\s]*([\d.+-]+)%/i);
  if (growthMatch) {
    metrics['Growth'] = `${growthMatch[1]}%`;
  }

  // Extract bullet points as insights
  const bulletPoints = content.match(/[-•]\s*([^\n]+)/g);
  if (bulletPoints) {
    bulletPoints.slice(0, 5).forEach(point => {
      const cleaned = point.replace(/^[-•]\s*/, '').trim();
      if (cleaned.length > 10 && cleaned.length < 200) {
        insights.push(cleaned);
      }
    });
  }

  // Detect recommendation
  const contentLower = content.toLowerCase();
  if (contentLower.includes('strong buy') || contentLower.includes('strongly recommend buying')) {
    recommendation = 'buy';
  } else if (contentLower.includes('recommend buying') || contentLower.includes('bullish')) {
    recommendation = 'buy';
  } else if (contentLower.includes('recommend selling') || contentLower.includes('bearish') || contentLower.includes('sell')) {
    recommendation = 'sell';
  } else if (contentLower.includes('hold') || contentLower.includes('maintain position')) {
    recommendation = 'hold';
  } else if (contentLower.includes('neutral') || contentLower.includes('wait')) {
    recommendation = 'neutral';
  }

  return { metrics, insights, recommendation };
}

/**
 * Generate a simple summary card DSL (for quick reports)
 */
export function generateSimpleSummaryDSL(ticker: string, summary: string): string {
  // Truncate summary if too long
  const truncatedSummary = summary.length > 200
    ? summary.substring(0, 197) + '...'
    : summary;

  return `infographic list-grid-simple
data
  title ${ticker} Summary
  items
    - label Summary
      desc ${escapeValue(truncatedSummary)}
theme dark`.trim();
}

/**
 * Generate process flow DSL (for showing analysis steps)
 */
export function generateProcessFlowDSL(steps: Array<{ label: string; description: string }>): string {
  const items = steps
    .slice(0, 5)
    .map(s => `    - label ${escapeValue(s.label)}\n      desc ${escapeValue(s.description)}`)
    .join('\n');

  return `infographic list-row-simple-horizontal-arrow
data
  title Analysis Process
  items
${items}
theme dark`.trim();
}

/**
 * Format duration from milliseconds to human-readable
 */
function formatDuration(ms?: number): string {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = ((ms % 60000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}

export default generateReportDSL;
