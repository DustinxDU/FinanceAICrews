// frontend/components/crew-builder/execution-stream/core/ChartDataDetector.ts
/**
 * ChartDataDetector - Smart data type detection for visualization routing
 *
 * Detects 15+ financial data types from MCP tool outputs and routes
 * to appropriate visualization components.
 */

export type DataType =
  | 'stock_info'    // Company profile + key metrics
  | 'kline'         // OHLCV candlestick data
  | 'financial'     // Income/Balance/Cashflow statements
  | 'quote'         // Real-time price quote
  | 'metrics'       // PE/PB/ROE indicators
  | 'fund_flow'     // Money flow data
  | 'macro'         // Macroeconomic indicators
  | 'ranking'       // Leaderboard data
  | 'news'          // News articles
  | 'holders'       // Shareholder distribution
  | 'search'        // Search results
  | 'web_content'   // Scraped web content
  | 'summary'       // AI-generated summary
  | 'time_series'   // Generic time series
  | 'comparison'    // Multi-column comparison
  | 'table';        // Fallback table

export interface DetectionResult {
  type: DataType;
  confidence: number;
  data: any;
  metadata?: {
    symbol?: string;
    title?: string;
    rowCount?: number;
    columns?: string[];
  };
}

// ============ Detection Functions ============

function detectStockInfo(data: any): number {
  // Pattern: { symbol, info: { shortName, sector, currentPrice, ... } }
  if (data.symbol && data.info && typeof data.info === 'object') {
    const info = data.info;
    if (info.shortName || info.longName || info.sector || info.industry) {
      return 0.95;
    }
  }
  // Pattern: { symbol, company_name, sector, industry }
  if (data.symbol && (data.company_name || data.companyName) && (data.sector || data.industry)) {
    return 0.9;
  }
  return 0;
}

function detectKline(data: any): number {
  // Pattern: { data: [...], columns: ['Date', 'Open', 'High', 'Low', 'Close', ...] }
  if (!Array.isArray(data.data) || !Array.isArray(data.columns)) return 0;

  const cols = new Set(data.columns.map((c: string) => c.toLowerCase()));
  const hasOHLC = cols.has('open') && cols.has('high') && cols.has('low') && cols.has('close');

  if (hasOHLC) {
    return 0.95;
  }
  return 0;
}

function detectFinancial(data: any): number {
  // Pattern: { data: [...], columns: [...], statement_type: 'income' | 'balance' | 'cashflow' }
  if (!Array.isArray(data.data) || !Array.isArray(data.columns)) return 0;

  const cols = new Set(data.columns);

  // Check for income statement fields
  const incomeFields = ['Total Revenue', 'Net Income', 'Gross Profit', 'Operating Income'];
  const hasIncome = incomeFields.some(f => cols.has(f));

  // Check for balance sheet fields
  const balanceFields = ['Total Assets', 'Total Liabilities', 'Total Equity'];
  const hasBalance = balanceFields.some(f => cols.has(f));

  // Check for cash flow fields
  const cashflowFields = ['Operating Cash Flow', 'Free Cash Flow', 'Capital Expenditure'];
  const hasCashflow = cashflowFields.some(f => cols.has(f));

  if (data.statement_type === 'income' || data.statement_type === 'balance' ||
      data.statement_type === 'cashflow' || data.statement_type === 'cash_flow') {
    return 0.9;
  }

  if (hasIncome || hasBalance || hasCashflow) {
    return 0.85;
  }

  return 0;
}

function detectQuote(data: any): number {
  // Pattern: { symbol, price, change, volume }
  if (data.symbol && typeof data.price === 'number' && typeof data.change === 'number') {
    return 0.9;
  }
  // Pattern: { regularMarketPrice, regularMarketChange }
  if (typeof data.regularMarketPrice === 'number') {
    return 0.85;
  }
  return 0;
}

function detectNews(data: any): number {
  // Pattern: { news: [{ title, summary, provider }] }
  if (Array.isArray(data.news) && data.news.length > 0) {
    const first = data.news[0];
    if (first.title || first.content?.title) {
      return 0.9;
    }
  }
  return 0;
}

function detectSearch(data: any): number {
  // Pattern: [{ title, snippet, url }] or { results: [{ title, snippet, url }] }
  const results = Array.isArray(data) ? data : data.results;

  if (Array.isArray(results) && results.length > 0) {
    const first = results[0];
    if (first.title && (first.snippet || first.description) && first.url) {
      return 0.85;
    }
  }
  return 0;
}

function detectFundFlow(data: any): number {
  // Pattern: has fields like 主力净流入, 超大单净流入, etc. (Chinese fund flow)
  const fundFlowFields = ['主力净流入', '超大单净流入', '大单净流入', '净流入', 'net_inflow'];
  const keys = Object.keys(data);

  const hasFields = fundFlowFields.some(f => keys.includes(f));
  if (hasFields) return 0.85;

  // English pattern
  if (data.net_inflow !== undefined || data.main_force_inflow !== undefined) {
    return 0.8;
  }

  return 0;
}

function detectRanking(data: any): number {
  // Pattern: has 排名/rank field, or is array with ranking indicators
  if (Array.isArray(data.data)) {
    const first = data.data[0];
    if (first && (first.rank !== undefined || first['排名'] !== undefined)) {
      return 0.8;
    }
  }
  // Check for LHB (龙虎榜) data
  if (data.lhb || data.top_list) {
    return 0.8;
  }
  return 0;
}

function detectHolders(data: any): number {
  // Pattern: shareholder data with 持股比例 or holding_percent
  if (Array.isArray(data.holders) || Array.isArray(data.top_holders)) {
    return 0.8;
  }
  if (data.institutional_holders || data.insider_holders) {
    return 0.75;
  }
  return 0;
}

function detectMacro(data: any): number {
  // Pattern: tool name contains 'macro' or specific macro indicators
  if (data._tool_name && data._tool_name.includes('macro')) {
    return 0.8;
  }
  // Check for common macro fields
  const macroFields = ['gdp', 'cpi', 'pmi', 'unemployment', 'interest_rate'];
  const keys = Object.keys(data).map(k => k.toLowerCase());
  if (macroFields.some(f => keys.includes(f))) {
    return 0.75;
  }
  return 0;
}

function detectMetrics(data: any): number {
  // Pattern: PE/PB/ROE metrics
  const metricFields = ['pe', 'pb', 'roe', 'roa', 'eps', 'pe_ratio', 'pb_ratio'];
  const keys = Object.keys(data).map(k => k.toLowerCase());

  const matchCount = metricFields.filter(f => keys.includes(f)).length;
  if (matchCount >= 2) return 0.75;
  if (matchCount >= 1) return 0.6;
  return 0;
}

function detectWebContent(data: any): number {
  // Pattern: { url, content, markdown } or { text, html }
  if (data.url && (data.content || data.markdown || data.text)) {
    return 0.75;
  }
  return 0;
}

function detectTimeSeries(data: any): number {
  // Pattern: array with date and value columns
  if (!Array.isArray(data.data) || data.data.length === 0) return 0;

  const first = data.data[0];
  const keys = Object.keys(first);

  // Check for date column
  const hasDate = keys.some(k =>
    k.toLowerCase().includes('date') ||
    k.toLowerCase().includes('time') ||
    k === 'x'
  );

  // Check for numeric value columns
  const hasValue = keys.some(k => typeof first[k] === 'number');

  if (hasDate && hasValue) {
    return 0.7;
  }
  return 0;
}

function detectComparison(data: any): number {
  // Pattern: multiple numeric columns for comparison
  if (!Array.isArray(data.data) || data.data.length === 0) return 0;

  const first = data.data[0];
  const numericCols = Object.keys(first).filter(k => typeof first[k] === 'number');

  if (numericCols.length >= 2) {
    return 0.6;
  }
  return 0;
}

function detectTable(data: any): number {
  // Fallback: any structured data with rows
  // Use 0.51 to pass the > 0.5 threshold
  if (Array.isArray(data.data) && data.data.length > 0) {
    return 0.51;
  }
  if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
    return 0.51;
  }
  return 0;
}

// ============ Metadata Extraction ============

function extractMetadata(data: any, type: DataType): DetectionResult['metadata'] {
  const metadata: DetectionResult['metadata'] = {};

  // Symbol
  if (data.symbol) metadata.symbol = data.symbol;
  if (data.ticker) metadata.symbol = data.ticker;

  // Row count
  if (Array.isArray(data.data)) {
    metadata.rowCount = data.data.length;
  } else if (Array.isArray(data)) {
    metadata.rowCount = data.length;
  }

  // Columns
  if (Array.isArray(data.columns)) {
    metadata.columns = data.columns;
  }

  // Title based on type
  switch (type) {
    case 'stock_info':
      metadata.title = data.info?.shortName || data.company_name || `${data.symbol} Info`;
      break;
    case 'kline':
      metadata.title = `${data.symbol || ''} Price History`;
      break;
    case 'financial':
      metadata.title = `${data.symbol || ''} ${data.statement_type || 'Financial'} Statement`;
      break;
    case 'quote':
      metadata.title = `${data.symbol || ''} Quote`;
      break;
    case 'news':
      metadata.title = `${data.symbol || ''} News`;
      break;
  }

  return metadata;
}

// Detection priority order (higher confidence types first)
const DETECTION_ORDER: Array<{ type: DataType; detect: (data: any) => number }> = [
  { type: 'stock_info', detect: detectStockInfo },
  { type: 'kline', detect: detectKline },
  { type: 'financial', detect: detectFinancial },
  { type: 'quote', detect: detectQuote },
  { type: 'news', detect: detectNews },
  { type: 'search', detect: detectSearch },
  { type: 'fund_flow', detect: detectFundFlow },
  { type: 'ranking', detect: detectRanking },
  { type: 'holders', detect: detectHolders },
  { type: 'macro', detect: detectMacro },
  { type: 'metrics', detect: detectMetrics },
  { type: 'web_content', detect: detectWebContent },
  { type: 'time_series', detect: detectTimeSeries },
  { type: 'comparison', detect: detectComparison },
  { type: 'table', detect: detectTable },
];

/**
 * Main detection function
 */
export function detectDataType(payload: any): DetectionResult | null {
  if (!payload) return null;

  // Handle JSON string input
  let data = payload;
  if (typeof payload === 'string') {
    try {
      data = JSON.parse(payload);
    } catch {
      return null;
    }
  }

  if (typeof data !== 'object') return null;

  // Try each detector in priority order
  for (const { type, detect } of DETECTION_ORDER) {
    const confidence = detect(data);
    if (confidence > 0.5) {
      return {
        type,
        confidence,
        data,
        metadata: extractMetadata(data, type),
      };
    }
  }

  return null;
}

export default detectDataType;
