import {defineRouting} from 'next-intl/routing';
import {createNavigation} from 'next-intl/navigation';

export const routing = defineRouting({
  locales: ['en', 'zh-CN', 'zh-TW', 'ja', 'ko', 'ms', 'id', 'vi', 'th', 'es', 'fr', 'de', 'ru', 'ar', 'hi', 'pt'],
  defaultLocale: 'en'
});

export const {Link, redirect, usePathname, useRouter} = createNavigation(routing);
