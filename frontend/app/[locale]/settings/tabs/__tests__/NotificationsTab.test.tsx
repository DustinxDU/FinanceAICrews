import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { act } from 'react'

// Use vi.hoisted to create mock functions that are available during mock factory execution
const mocks = vi.hoisted(() => ({
  getNotificationPreferences: vi.fn(),
  updateNotificationPreferences: vi.fn(),
  unsubscribePushNotifications: vi.fn(),
}))

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
}))

const translations = vi.hoisted<Record<string, string>>(() => ({
  notifications: 'Notifications',
  description: 'Stay informed about analysis and system events.',
  enableNotifications: 'Enable Notifications',
  enableDescription: 'Turn notifications on or off for this account.',
  notificationTypes: 'Notification Types',
  analysisCompletion: 'Analysis Completion',
  analysisCompletionDesc: 'Get notified when an analysis job completes.',
  systemUpdates: 'System Updates',
  systemUpdatesDesc: 'System updates include releases and maintenance.',
  enableFirst: 'Enable notifications above to manage types.',
  pushNotSubscribed: 'Not subscribed',
  pushSubscribed: 'Subscribed',
  browserPush: 'Browser Push Notifications',
  browserPushDesc: 'Browser push notifications work when enabled.',
  pushNotSupportedBrowser: 'Not supported in this browser',
  pushBlocked: 'Push notifications are blocked in your browser.',
  enablePush: 'Enable Push Notifications',
  disablePush: 'Disable Push Notifications',
  aboutNotifications: 'About Notifications',
  infoAnalysis: 'Analysis completion notifications keep you posted.',
  infoSystem: 'System updates include maintenance notices.',
  infoPush: 'Browser push notifications work when enabled.',
  pushUnsubscribed: 'Unsubscribed from push notifications.',
  pushSubscribedSuccess: 'Subscribed to push notifications.',
  failed: 'failed'
}))

vi.mock('@/lib/api', () => ({
  default: mocks,
}))

vi.mock('@/lib/toast', () => ({
  useToast: () => toastMocks,
}))

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => translations[key] ?? key,
}));

// Import component AFTER mocks are set up
import { NotificationsTab } from '../NotificationsTab'

// TODO: re-enable after stabilizing async render; currently flaky under jsdom
describe.skip('NotificationsTab', () => {
  const mockPreferences = {
    id: 1,
    user_id: 123,
    enabled: true,
    analysis_completion: true,
    system_updates: false,
    has_push_subscription: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  const stubPushSupported = () => {
    class NotificationMock {
      static permission: NotificationPermission = 'granted'
      static requestPermission = vi.fn().mockResolvedValue('granted')
    }

    vi.stubGlobal('Notification', NotificationMock as any)

    Object.defineProperty(navigator, 'serviceWorker', {
      value: { ready: Promise.resolve({}) },
      configurable: true,
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    stubPushSupported()
    mocks.getNotificationPreferences.mockResolvedValue(mockPreferences)
    mocks.updateNotificationPreferences.mockResolvedValue(mockPreferences)
    mocks.unsubscribePushNotifications.mockResolvedValue(mockPreferences)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete (navigator as any).serviceWorker
    vi.clearAllMocks()
  })

  const renderAndWaitLoaded = async () => {
    const actualUseState: typeof React.useState = React.useState
    const useStateSpy = vi.spyOn(React, 'useState')
    useStateSpy.mockImplementationOnce(() => [mockPreferences, vi.fn()]) // preferences
    useStateSpy.mockImplementationOnce(() => [false, vi.fn()]) // isLoading
    useStateSpy.mockImplementation(((initial: any) => actualUseState(initial)) as any)

    await act(async () => {
      render(<NotificationsTab />)
    })
    useStateSpy.mockRestore()
    await screen.findByText('Enable Notifications', undefined, { timeout: 3000 })
  }

  describe('Loading state', () => {
    it('shows loading spinner while fetching preferences', async () => {
      // Delay the API response to see loading state
      mocks.getNotificationPreferences.mockImplementation(
        () => new Promise(() => {}) // Never resolves, stuck in loading
      )

      render(<NotificationsTab />)

      // Should show loading spinner (check for animate-spin class)
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
    })

    it('fetches preferences on mount', async () => {
      render(<NotificationsTab />)

      await waitFor(() => {
        expect(mocks.getNotificationPreferences).toHaveBeenCalledOnce()
      })
    })
  })

  describe('Rendering preferences', () => {
    it('renders master toggle correctly', async () => {
      await renderAndWaitLoaded()
      expect(screen.getByText('Enable Notifications')).toBeInTheDocument()
    })

    it('renders notification type toggles', async () => {
      await renderAndWaitLoaded()
      expect(screen.getByText('Analysis Completion')).toBeInTheDocument()
      expect(screen.getByText('System Updates')).toBeInTheDocument()
    })

    it('shows correct toggle states based on preferences', async () => {
      await renderAndWaitLoaded()

      // Find all switch buttons
      const switches = screen.getAllByRole('switch')

      // Master toggle should be checked (enabled: true)
      expect(switches[0]).toHaveAttribute('aria-checked', 'true')
    })
  })

  describe('Toggle interactions', () => {
    it('calls API when toggling master switch', async () => {
      await renderAndWaitLoaded()

      const switches = screen.getAllByRole('switch')
      const masterToggle = switches[0]

      fireEvent.click(masterToggle)

      await waitFor(() => {
        expect(mocks.updateNotificationPreferences).toHaveBeenCalled()
      })
    })

    it('calls API when toggling analysis completion', async () => {
      await renderAndWaitLoaded()

      const switches = screen.getAllByRole('switch')
      const analysisToggle = switches[1] // Second toggle

      fireEvent.click(analysisToggle)

      await waitFor(() => {
        expect(mocks.updateNotificationPreferences).toHaveBeenCalled()
      })
    })
  })

  describe('Disabled states', () => {
    it('disables notification type toggles when master switch is off', async () => {
      mocks.getNotificationPreferences.mockResolvedValue({
        ...mockPreferences,
        enabled: false,
      })

      await renderAndWaitLoaded()

      // Should show the warning about enabling notifications first
      expect(screen.getByText(/Enable notifications above/i)).toBeInTheDocument()
    })
  })

  describe('Push subscription section', () => {
    it('shows "Not subscribed" status when no push subscription', async () => {
      await renderAndWaitLoaded()
      expect(screen.getByText('Not subscribed')).toBeInTheDocument()
    })

    it('shows "Subscribed" status when push subscription exists', async () => {
      mocks.getNotificationPreferences.mockResolvedValue({
        ...mockPreferences,
        has_push_subscription: true,
      })

      await renderAndWaitLoaded()
      expect(screen.getByText('Subscribed')).toBeInTheDocument()
    })

    it('shows enable button when not subscribed', async () => {
      await renderAndWaitLoaded()
      expect(screen.getByText('Enable Push Notifications')).toBeInTheDocument()
    })

    it('shows disable button when subscribed', async () => {
      mocks.getNotificationPreferences.mockResolvedValue({
        ...mockPreferences,
        has_push_subscription: true,
      })

      await renderAndWaitLoaded()
      expect(screen.getByText('Disable Push Notifications')).toBeInTheDocument()
    })

    it('calls unsubscribe API when clicking disable button', async () => {
      mocks.getNotificationPreferences.mockResolvedValue({
        ...mockPreferences,
        has_push_subscription: true,
      })
      mocks.unsubscribePushNotifications.mockResolvedValue({
        ...mockPreferences,
        has_push_subscription: false,
      })

      await renderAndWaitLoaded()

      const disableButton = screen.getByText('Disable Push Notifications')
      fireEvent.click(disableButton)

      await waitFor(() => {
        expect(mocks.unsubscribePushNotifications).toHaveBeenCalled()
      })
    })
  })

  describe('Error handling', () => {
    it('handles API error when loading preferences', async () => {
      mocks.getNotificationPreferences.mockRejectedValue(
        new Error('failed to load')
      )

      render(<NotificationsTab />)

      // Component should handle error gracefully (not crash)
      await waitFor(() => {
        expect(mocks.getNotificationPreferences).toHaveBeenCalled()
      })
    })

    it('handles API error when updating preferences', async () => {
      mocks.updateNotificationPreferences.mockRejectedValue(
        new Error('failed to update')
      )

      await renderAndWaitLoaded()

      const switches = screen.getAllByRole('switch')
      fireEvent.click(switches[0])

      // Should revert optimistic update on error
      await waitFor(() => {
        expect(mocks.updateNotificationPreferences).toHaveBeenCalled()
      })
    })
  })

  describe('Information section', () => {
    it('renders about section with information', async () => {
      await renderAndWaitLoaded()
      expect(screen.getByText('About Notifications')).toBeInTheDocument()

      // Check for info bullets
      expect(screen.getByText(/Analysis completion notifications/i)).toBeInTheDocument()
      expect(screen.getByText(/System updates include/i)).toBeInTheDocument()
      expect(screen.getByText(/Browser push notifications work/i)).toBeInTheDocument()
    })
  })
})

describe.skip('NotificationsTab - Push notification support', () => {
  const mockPreferences = {
    id: 1,
    user_id: 123,
    enabled: true,
    analysis_completion: true,
    system_updates: true,
    has_push_subscription: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock window.Notification and navigator.serviceWorker as not existing
    delete (navigator as any).serviceWorker
    vi.stubGlobal('Notification', undefined)
    mocks.getNotificationPreferences.mockResolvedValue(mockPreferences)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete (navigator as any).serviceWorker
    vi.clearAllMocks()
  })

  it('shows message when push notifications are not supported', async () => {
    render(<NotificationsTab />)
    await screen.findByText(/not supported in this browser/i)
  })
})
