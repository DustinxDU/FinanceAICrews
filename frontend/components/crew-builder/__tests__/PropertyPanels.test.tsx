import { render, screen, within } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AgentNodePanel, EndNodePanel } from '../PropertyPanels'

vi.mock('../SkillSelector/SkillSelector', () => ({
  SkillSelector: () => <div data-testid="skill-selector" />,
}))

vi.mock('@/lib/api', () => ({
  default: {
    getSkillCatalog: vi.fn().mockResolvedValue({
      capabilities: [],
      presets: [],
      strategies: [],
      skillsets: [],
    }),
  },
}))

describe('PropertyPanels routing tiers', () => {
  it('renders agent tier options', () => {
    render(
      <AgentNodePanel
        data={{ role: 'Analyst', model: 'agents_balanced' }}
        updateData={vi.fn()}
        availableVars={[]}
        connectedKnowledge={[]}
        mcpTools={[]}
      />
    )

    const tierSelect = screen.getByLabelText('Agent Routing Tier')
    const options = within(tierSelect).getAllByRole('option').map((opt) => opt.textContent)
    expect(options).toContain('agents_fast')
    expect(options).toContain('agents_balanced')
    expect(options).toContain('agents_best')
  })

  it('renders selected skill keys even when catalog is empty', async () => {
    render(
      <AgentNodePanel
        data={{ role: 'Analyst', loadout_data: { skill_keys: ['skillset:analysis', 'capability:fundamental'] } }}
        updateData={vi.fn()}
        availableVars={[]}
        connectedKnowledge={[]}
        mcpTools={[]}
      />
    )

    expect(await screen.findByText('skillset:analysis')).toBeInTheDocument()
    expect(await screen.findByText('capability:fundamental')).toBeInTheDocument()
  })

  it('renders summary tier options', () => {
    render(
      <EndNodePanel
        data={{ aggregationMethod: 'llm_summary', summaryModel: 'agents_balanced' }}
        updateData={vi.fn()}
      />
    )

    const summarySelect = screen.getByLabelText('Summary Routing Tier')
    const options = within(summarySelect).getAllByRole('option').map((opt) => opt.textContent)
    expect(options).toContain('agents_fast')
    expect(options).toContain('agents_balanced')
    expect(options).toContain('agents_best')
  })
})
