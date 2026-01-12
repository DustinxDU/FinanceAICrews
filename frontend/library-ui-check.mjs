/**
 * Playwright script to check Library page UI
 */

import { chromium } from 'playwright';

async function checkLibraryUI() {
  console.log('🚀 Launching browser...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });
  const page = await context.newPage();

  // Capture console messages
  const consoleMessages = [];
  page.on('console', (msg) => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text(),
    });
  });

  // Capture page errors
  const pageErrors = [];
  page.on('pageerror', (error) => {
    pageErrors.push(error.message);
  });

  try {
    // Navigate to Library page
    console.log('📄 Navigating to /library...');
    await page.goto('http://localhost:3000/library', {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Wait for page to fully render
    await page.waitForTimeout(3000);

    // Check if page loaded successfully
    const title = await page.title();
    console.log(`✅ Page title: ${title}`);

    // Check for Library-specific elements using more reliable selectors
    const checks = await page.evaluate(() => {
      const text = document.body.innerText;
      return {
        // Layout
        hasSidebar: text.includes('FinanceAI') && text.includes('Cockpit'),
        hasHeader: text.includes('FinanceAI') && (text.includes('Active') || text.includes('AAPL')),
        hasLibrary: text.includes('Library'),

        // Components
        hasAssetBookshelf: text.includes('资产书架') || text.includes('书架'),
        hasSignalTimeline: text.includes('信号时间轴') || text.includes('时间轴'),
        hasInvestigationRoom: text.includes('资产情报局') || text.includes('情报局'),

        // Filters
        hasAllFilter: text.includes('全部'),
        hasFavoritesFilter: text.includes('收藏'),
        hasRecentFilter: text.includes('最近'),
        hasSourceFilter: text.includes('来源'),
        hasSentimentFilter: text.includes('情绪'),

        // Assets
        hasAssets: text.includes('AAPL') || text.includes('MSFT') || text.includes('NVDA'),

        // Other elements
        hasSearch: text.includes('搜索') || text.includes('Search'),
        hasScrollable: document.querySelectorAll('[class*="overflow-y-auto"]').length > 0,
        hasButtons: document.querySelectorAll('button').length > 0,
        hasInputs: document.querySelectorAll('input').length > 0,
      };
    });

    console.log(`\n📊 Layout Check:`);
    console.log(`   - Sidebar: ${checks.hasSidebar ? '✅' : '❌'}`);
    console.log(`   - Header: ${checks.hasHeader ? '✅' : '❌'}`);
    console.log(`   - Library Page: ${checks.hasLibrary ? '✅' : '❌'}`);

    console.log(`\n📚 Library Components:`);
    console.log(`   - Asset Bookshelf: ${checks.hasAssetBookshelf ? '✅' : '❌'}`);
    console.log(`   - Signal Timeline: ${checks.hasSignalTimeline ? '✅' : '❌'}`);
    console.log(`   - Investigation Room: ${checks.hasInvestigationRoom ? '✅' : '❌'}`);

    console.log(`\n🔍 Filters:`);
    console.log(`   - 全部: ${checks.hasAllFilter ? '✅' : '❌'}`);
    console.log(`   - 收藏: ${checks.hasFavoritesFilter ? '✅' : '❌'}`);
    console.log(`   - 最近: ${checks.hasRecentFilter ? '✅' : '❌'}`);
    console.log(`   - 来源: ${checks.hasSourceFilter ? '✅' : '❌'}`);
    console.log(`   - 情绪: ${checks.hasSentimentFilter ? '✅' : '❌'}`);

    console.log(`\n📝 Page Structure:`);
    console.log(`   - Assets visible: ${checks.hasAssets ? '✅' : '❌'}`);
    console.log(`   - Search box: ${checks.hasSearch ? '✅' : '❌'}`);
    console.log(`   - Scrollable areas: ${checks.hasScrollable ? '✅' : '❌'}`);
    console.log(`   - Buttons: ${checks.hasButtons ? '✅' : '❌'}`);
    console.log(`   - Input fields: ${checks.hasInputs ? '✅' : '❌'}`);

    // Check for errors in console (filter out auth errors which are expected when not logged in)
    const authErrors = consoleMessages.filter(m =>
      m.text.includes('401') || m.text.includes('Unauthorized') || m.text.includes('Authentication')
    );
    const realErrors = consoleMessages.filter(m =>
      m.type === 'error' && !m.text.includes('401') && !m.text.includes('Unauthorized') && !m.text.includes('Authentication')
    );

    console.log(`\n🔍 Console Status:`);
    console.log(`   - Auth Errors (expected when not logged in): ${authErrors.length}`);
    console.log(`   - Real Errors: ${realErrors.length}`);

    if (realErrors.length > 0) {
      console.log(`\n❌ Real Console Errors:`);
      realErrors.forEach((e, i) => console.log(`   ${i + 1}. ${e.text.substring(0, 200)}`));
    }

    if (pageErrors.length > 0) {
      const realPageErrors = pageErrors.filter(e =>
        !e.includes('401') && !e.includes('Unauthorized') && !e.includes('Authentication')
      );
      if (realPageErrors.length > 0) {
        console.log(`\n❌ Page Errors:`);
        realPageErrors.forEach((e, i) => console.log(`   ${i + 1}. ${e.substring(0, 200)}`));
      }
    }

    // Take screenshot for visual reference
    await page.screenshot({
      path: '/tmp/library-page-screenshot-v2.png',
      fullPage: true,
    });
    console.log(`\n📸 Screenshot saved to /tmp/library-page-screenshot-v2.png`);

    // Print summary
    console.log(`\n========================================`);
    console.log(`          UI CHECK SUMMARY`);
    console.log(`========================================`);

    const hasRealErrors = realErrors.length > 0 ||
      pageErrors.filter(e => !e.includes('401') && !e.includes('Unauthorized') && !e.includes('Authentication')).length > 0;

    const uiComplete = checks.hasAssetBookshelf && checks.hasSignalTimeline && checks.hasInvestigationRoom;

    if (hasRealErrors) {
      console.log(`⚠️  Found real error(s) - see above`);
    } else if (!uiComplete) {
      console.log(`⚠️  UI not fully loaded (likely due to auth)`);
    } else {
      console.log(`✅ UI loaded successfully (auth errors are expected when not logged in)`);
    }

    console.log(`========================================`);

  } catch (error) {
    console.error(`❌ Error during check: ${error.message}`);
  } finally {
    await browser.close();
    console.log(`\n🔒 Browser closed`);
  }
}

checkLibraryUI();
