import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Button } from '@/components/common/Button'

describe('Button Component', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>)
    const button = screen.getByRole('button', { name: /click me/i })
    expect(button).toBeInTheDocument()
  })

  it('applies primary variant styles', () => {
    render(<Button variant="primary">Primary</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-primary-500')
  })

  it('handles click events', () => {
    let clicked = false
    const handleClick = () => {
      clicked = true
    }
    render(<Button onClick={handleClick}>Click</Button>)
    screen.getByRole('button').click()
    expect(clicked).toBe(true)
  })
})
