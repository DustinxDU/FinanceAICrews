/**
 * Chart Components Initializer
 *
 * This file imports all chart components that use registerChartComponent(),
 * ensuring their registration side effects execute at runtime.
 *
 * Import this file in ExecutionStreamPanel.tsx to activate all visualizations.
 *
 * IMPORTANT: This file must be imported AFTER chartRegistry.ts is loaded,
 * which happens automatically since chart components import from chartRegistry.
 */

// Import chart components to trigger their registerChartComponent() calls
import '../charts/KLineChart';
import '../charts/FinancialBarChart';
import '../cards/StockInfoCardV2';

// Future chart components should be added here:
// import '../cards/QuoteCardV2';
// import '../cards/NewsCardV2';
// import '../cards/SearchResultCard';
// import '../cards/SmartTable';
