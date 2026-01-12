import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ExecutionStreamContainer } from '../ExecutionStreamContainer'
import { ExecutionStep } from '../types'

describe('ExecutionStreamContainer', () => {
  const mockSteps: ExecutionStep[] = [
    {
      id: '1',
      type: 'thought',
      content: 'Planning the next move...',
      agentName: 'Researcher',
      timestamp: '10:00:00'
    },
    {
      id: '2',
      type: 'tool_call',
      toolName: 'GoogleSearch',
      input: '{"q": "crewai"}',
      timestamp: '10:00:05'
    },
    {
      id: '3',
      type: 'observation',
      content: 'Search results found...',
      timestamp: '10:00:10'
    },
    {
      id: '4',
      type: 'final_answer',
      content: 'The definitive guide to CrewAI.',
      timestamp: '10:00:15'
    }
  ]

  it('renders empty state when no steps', () => {
    render(<ExecutionStreamContainer steps={[]} />)
    expect(screen.getByText(/Waiting for execution/i)).toBeDefined()
  })

  it('renders a list of steps', () => {
    render(<ExecutionStreamContainer steps={mockSteps} />)
    expect(screen.getByText('Planning the next move...')).toBeDefined()
    expect(screen.getByText('GoogleSearch')).toBeDefined()
    expect(screen.getByText('Search results found...')).toBeDefined()
    expect(screen.getByText('The definitive guide to CrewAI.')).toBeDefined()
  })
})
