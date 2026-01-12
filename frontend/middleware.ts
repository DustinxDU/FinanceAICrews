import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'zh-CN', 'zh-TW', 'ja', 'ko', 'ms', 'id', 'vi', 'th', 'es', 'fr', 'de', 'ru', 'ar', 'hi', 'pt'],
  defaultLocale: 'en',
  localePrefix: 'always'
});

export const config = {
  // Exclude auth routes (login, register, etc.) from locale prefix
  // These pages are in (auth) route group and don't need locale
  matcher: [
    '/((?!api|_next|_vercel|login|register|forgot-password|reset-password|.*\\..*).*)'
  ]
};
