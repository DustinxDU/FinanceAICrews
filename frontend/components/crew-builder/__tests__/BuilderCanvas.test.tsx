import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BuilderCanvas } from '../BuilderCanvas'
import * as api from '@/lib/api'

// Mock dependencies
vi.mock('@/lib/api', () => ({
  default: {
    getCrewDefinition: vi.fn(),
    getAgentDefinition: vi.fn(),
    getTaskDefinition: vi.fn(),
    getSkillCatalog: vi.fn().mockResolvedValue({
      capabilities: [],
      presets: [],
      strategies: [],
      skillsets: [],
    }),
    startAnalysisV2: vi.fn()
  }
}))

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn()

vi.mock('../execution-steps/ExecutionStreamContainer', () => ({
  ExecutionStreamContainer: ({ steps }: any) => (
    <div data-testid="execution-stream-container">
      Steps: {steps.length}
    </div>
  )
}))

vi.mock('../execution-steps/useExecutionStream', () => ({
  useExecutionStream: (runId: string | null) => ({
    steps: runId ? [{ id: '1', type: 'thought', content: 'thinking' }] : [],
    isConnected: !!runId,
    clearSteps: vi.fn()
  })
}))

describe('BuilderCanvas Integration', () => {
  const defaultProps = {
    onBack: vi.fn(),
    onSave: vi.fn(),
    mcpTools: [],
    crewId: 1
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // @ts-ignore
    api.default.getCrewDefinition.mockResolvedValue({
      id: 1,
      name: 'Test Crew',
      ui_state: { nodes: [], edges: [] }
    })
  })

  it('shows execution panel when run starts', async () => {
    // @ts-ignore
    api.default.startAnalysisV2.mockResolvedValue({ job_id: 'job-123' })

    render(<BuilderCanvas {...defaultProps} />)

    // Wait for crew to load
    await waitFor(() => expect(screen.queryByText('Loading crew configuration...')).not.toBeInTheDocument())

    // 1. Find and click the "Run Crew" button (Checking if it exists)
    const runButton = screen.getByText('Run Crew')
    expect(runButton).toBeInTheDocument()
    fireEvent.click(runButton)

    // 2. Run Modal should appear
    expect(screen.getByText('Start Execution')).toBeInTheDocument()

    // 3. Click "Run" in the modal
    // Note: there are two "Run" buttons (one in toolbar, one in modal). 
    // We need to be specific.
    const modalRunButton = screen.getAllByText('Run').find(el => el.closest('.fixed')) // rudimentary check
    // Better to use getByRole or test-id in real impl, but for now:
    // The modal button has 'Run' text and PlayCircle icon.
    // Let's assume we can click the one in the modal.
    // Actually, in the modal code: <button ...> <PlayCircle .../> Run </button>
    
    // Let's trigger the run action directly if UI is complex to query, 
    // but integration tests should interact with UI.
    
    // Simulate clicking the "Run" confirm button in modal
    // We need to target it precisely.
    // The modal is: <div className="fixed inset-0 ..."> ... <button>Run</button> ... </div>
    const buttons = screen.getAllByRole('button', { name: /Run/i })
    const confirmButton = buttons[buttons.length - 1] // Assuming it's the last one
    fireEvent.click(confirmButton)

    // 4. Expect startAnalysisV2 to be called
    await waitFor(() => {
        expect(api.default.startAnalysisV2).toHaveBeenCalled()
    })

    // 5. Expect Execution Panel to appear
    expect(screen.getByTestId('execution-stream-container')).toBeInTheDocument()
  })

  it('hydrates crew structure when ui_state is missing (shows agent skills)', async () => {
    // Crew from DB template: no ui_state, but has structure references.
    // @ts-ignore
    api.default.getCrewDefinition.mockResolvedValue({
      id: 1,
      name: 'Template Crew',
      ui_state: null,
      input_schema: null,
      structure: [{ agent_id: 10, tasks: [20] }]
    })

    // @ts-ignore
    api.default.getAgentDefinition.mockResolvedValue({
      id: 10,
      name: 'Fund Analyst',
      role: 'Fund Analyst',
      goal: 'Analyze fundamentals',
      backstory: 'Experienced analyst',
      loadout_data: { skill_keys: ['skillset:analysis'] }
    })

    // @ts-ignore
    api.default.getTaskDefinition.mockResolvedValue({
      id: 20,
      name: 'Fundamental Analysis',
      description: 'Do fundamental analysis',
      expected_output: 'Markdown'
    })

    render(<BuilderCanvas {...defaultProps} />)

    await waitFor(() => expect(screen.queryByText('Loading crew configuration...')).not.toBeInTheDocument())

    // Agent node hydrated from AgentDefinition
    expect(await screen.findByText('Fund Analyst')).toBeInTheDocument()

    // Select agent node to open properties panel, then verify skill binding is visible
    fireEvent.mouseDown(screen.getByText('Fund Analyst'))
    expect(await screen.findByText('skillset:analysis')).toBeInTheDocument()
  })
})
