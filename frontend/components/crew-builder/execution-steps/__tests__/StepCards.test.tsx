import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ThoughtCard, ToolCallCard, ObservationCard, FinalResultCard } from '../index'

describe('Execution Step Cards', () => {
  it('renders ThoughtCard with content', () => {
    render(<ThoughtCard content="Thinking about the market..." agentName="Analyst" />)
    expect(screen.getByText('Thinking about the market...')).toBeDefined()
    expect(screen.getByText('Agent: Analyst')).toBeDefined()
    // Check for "Thought" label or icon presence implied by design
    expect(screen.getByText('THOUGHT')).toBeDefined() 
  })

  it('renders ToolCallCard with tool name and input', () => {
    render(<ToolCallCard toolName="SearchNews" input="{ 'query': 'AAPL' }" />)
    expect(screen.getByText('SearchNews')).toBeDefined()
    expect(screen.getByText("{ 'query': 'AAPL' }")).toBeDefined()
    expect(screen.getByText('TOOL CALL')).toBeDefined()
  })

  it('renders ObservationCard with output', () => {
    render(<ObservationCard content="Stock price is $150" />)
    expect(screen.getByText('Stock price is $150')).toBeDefined()
    expect(screen.getByText('OBSERVATION')).toBeDefined()
  })

  it('renders FinalResultCard with result', () => {
    render(<FinalResultCard content="Buy AAPL" />)
    expect(screen.getByText('Buy AAPL')).toBeDefined()
    expect(screen.getByText('FINAL ANSWER')).toBeDefined()
  })
})
