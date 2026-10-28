import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ConfidenceMeter, { ConfidencePill } from '../components/ConfidenceMeter'
import RiskScoreCard, { getRiskSummary } from '../components/RiskScoreCard'
import { issue, review } from './fixtures'

describe('RiskScoreCard (Stage 8)', () => {
  it('shows the score, level and category breakdown', () => {
    render(<RiskScoreCard review={review()} />)
    expect(screen.getByText('72/100')).toBeInTheDocument()
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
    expect(screen.getByText('Security')).toBeInTheDocument()
    expect(screen.getByText('60/100')).toBeInTheDocument()
    expect(screen.getByText(/does not\s+represent the probability of a failed merge/)).toBeInTheDocument()
  })

  it('clamps the score and derives a missing level', () => {
    expect(getRiskSummary(review({ risk_score: 150 }))).toEqual({ score: 100, level: 'high' })
    expect(getRiskSummary(review({ risk_score: 45, risk_level: null }))).toEqual({ score: 45, level: 'medium' })
    expect(getRiskSummary(review({ risk_score: 10, risk_level: 'bogus' }))).toEqual({ score: 10, level: 'low' })
  })

  it('explains when no assessment exists', () => {
    const { rerender } = render(<RiskScoreCard review={review({ risk_score: null, risk_breakdown: null })} />)
    expect(screen.getByText('Risk assessment is not available for this review.')).toBeInTheDocument()

    rerender(<RiskScoreCard review={review({ review_status: 'pending' })} />)
    expect(screen.getByText('Risk assessment unavailable because the review is not completed.')).toBeInTheDocument()
  })
})

describe('ConfidenceMeter (Stage 7)', () => {
  it('shows score, level, evidence and the interpretation note', () => {
    render(<ConfidenceMeter issue={issue({ confidence_score: 45, confidence_level: 'medium', confidence_evidence: { ai: true, semgrep: true, bandit: false } })} />)
    expect(screen.getByText('45 / 100')).toBeInTheDocument()
    expect(screen.getByText('medium confidence')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Confidence score' })).toHaveAttribute('aria-valuenow', '45')
    expect(screen.getByText('Supporting evidence:').closest('p')).toHaveTextContent('Supporting evidence: AI analysis, Semgrep')
    expect(screen.getByText(/not the\s+probability that a finding is correct/)).toBeInTheDocument()
  })

  it('handles missing evidence and unscored findings', () => {
    const { rerender } = render(<ConfidenceMeter issue={issue({ confidence_evidence: {} })} />)
    expect(screen.getByText('Supporting evidence:').closest('p')).toHaveTextContent('No evidence sources recorded')

    rerender(<ConfidenceMeter issue={issue({ confidence_score: null })} />)
    expect(screen.getByText(/Not scored — this review may have been created before/)).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('renders the compact header pill', () => {
    const { rerender } = render(<ConfidencePill issue={issue()} />)
    expect(screen.getByText('Confidence 20')).toBeInTheDocument()
    expect(screen.getByText('Confidence score 20 out of 100')).toBeInTheDocument()

    rerender(<ConfidencePill issue={issue({ confidence_score: null })} />)
    expect(screen.getByText('Not scored')).toBeInTheDocument()
  })
})
