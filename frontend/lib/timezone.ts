/**
 * Timezone Utility
 * Provides timezone detection and formatting based on user location
 */

// Common timezone mappings by region
const REGION_TIMEZONES: Record<string, string> = {
  // China
  'CN': 'Asia/Shanghai',
  'HK': 'Asia/Hong_Kong',
  
  // United States
  'US': 'America/New_York',
  
  // Europe
  'GB': 'Europe/London',
  'DE': 'Europe/Berlin',
  'FR': 'Europe/Paris',
  'JP': 'Asia/Tokyo',
  'KR': 'Asia/Seoul',
  
  // Default fallback
  'DEFAULT': 'UTC',
};

/**
 * Detect timezone from country code
 */
export function getTimezoneFromCountry(countryCode: string): string {
  return REGION_TIMEZONES[countryCode] || REGION_TIMEZONES['DEFAULT'];
}

/**
 * Detect user's timezone based on browser Intl API
 */
export function detectUserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * Format date/time in user's local timezone
 */
export function formatLocalTime(
  date: Date | string,
  timezone?: string,
  options?: Intl.DateTimeFormatOptions
): string {
  const tz = timezone || detectUserTimezone();
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    ...options,
  };
  
  return new Intl.DateTimeFormat('en-US', {
    ...defaultOptions,
    timeZone: tz,
  }).format(dateObj);
}

/**
 * Format date in user's local timezone
 */
export function formatLocalDate(
  date: Date | string,
  timezone?: string
): string {
  const tz = timezone || detectUserTimezone();
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: tz,
  }).format(dateObj);
}

/**
 * Format full datetime in user's local timezone
 */
export function formatLocalDateTime(
  date: Date | string,
  timezone?: string
): string {
  const tz = timezone || detectUserTimezone();
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: tz,
  }).format(dateObj);
}

/**
 * Format timestamp for display (compact format)
 */
export function formatTimestamp(
  date: Date | string,
  timezone?: string
): string {
  const tz = timezone || detectUserTimezone();
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - dateObj.getTime();
  
  // Less than 1 minute
  if (diff < 60000) {
    return 'Just now';
  }
  
  // Less than 1 hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}m ago`;
  }
  
  // Less than 24 hours
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }
  
  // Otherwise show local time
  return formatLocalTime(dateObj, tz, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Get market hours for a specific timezone
 */
export function getMarketHours(timezone: string = 'UTC'): {
  isOpen: boolean;
  sessionInfo: string;
} {
  const tz = timezone || detectUserTimezone();
  const now = new Date();
  
  // Get current time in the target timezone
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    weekday: 'short',
  });
  
  const [weekday, time] = formatter.format(now).split(' ');
  const [hours, minutes] = time.split(':').map(Number);
  const currentMinutes = hours * 60 + minutes;
  
  // Market session definitions (in minutes from midnight)
  // US Equities: 9:30 AM - 4:00 PM ET
  // China: 9:30 AM - 3:00 PM CST
  // Hong Kong: 9:30 AM - 4:00 PM HKT
  const sessions: Record<string, { open: number; close: number; label: string }> = {
    'America/New_York': { open: 570, close: 960, label: 'US Equities' },
    'Asia/Shanghai': { open: 570, close: 900, label: 'China A-Share' },
    'Asia/Hong_Kong': { open: 570, close: 960, label: 'Hong Kong' },
    'Asia/Tokyo': { open: 540, close: 900, label: 'Japan' },
    'Europe/London': { open: 480, close: 960, label: 'London' },
  };
  
  const session = sessions[tz] || sessions['America/New_York'];
  const isWeekday = weekday !== 'Sat' && weekday !== 'Sun';
  const isOpen = isWeekday && currentMinutes >= session.open && currentMinutes < session.close;
  
  return {
    isOpen,
    sessionInfo: isOpen 
      ? `${session.label} • Open`
      : `${session.label} • Closed`,
  };
}

export default {
  getTimezoneFromCountry,
  detectUserTimezone,
  formatLocalTime,
  formatLocalDate,
  formatLocalDateTime,
  formatTimestamp,
  getMarketHours,
};
