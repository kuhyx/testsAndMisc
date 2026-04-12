import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MatchCard, type Match } from './MatchCard';

function makeMatch(overrides: Partial<Match> = {}): Match {
  return {
    id: 1,
    utcDate: '2024-09-17T20:00:00Z',
    status: 'FINISHED',
    homeTeam: 'Real Madrid',
    awayTeam: 'Bayern Munich',
    score: { fullTime: { home: 2, away: 1 }, halfTime: { home: 1, away: 0 } },
    ...overrides,
  };
}

describe('MatchCard', () => {
  it('renders home and away teams', () => {
    render(<MatchCard m={makeMatch()} />);
    expect(screen.getByText('Real Madrid')).toBeInTheDocument();
    expect(screen.getByText('Bayern Munich')).toBeInTheDocument();
  });

  it('renders full-time score', () => {
    render(<MatchCard m={makeMatch()} />);
    expect(screen.getByText('2 : 1')).toBeInTheDocument();
  });

  it('renders dash for null scores', () => {
    render(<MatchCard m={makeMatch({ score: { fullTime: { home: null, away: null } } })} />);
    expect(screen.getByText('- : -')).toBeInTheDocument();
  });

  it('renders dash for undefined fullTime', () => {
    render(<MatchCard m={makeMatch({ score: {} })} />);
    expect(screen.getByText('- : -')).toBeInTheDocument();
  });

  it('renders status with underscore replaced', () => {
    render(<MatchCard m={makeMatch({ status: 'IN_PLAY' })} />);
    expect(screen.getByText('IN PLAY')).toBeInTheDocument();
  });

  it('renders group and stage when present', () => {
    render(<MatchCard m={makeMatch({ group: 'Group A', stage: 'GROUP_STAGE' })} />);
    expect(screen.getByText('Group A')).toBeInTheDocument();
    expect(screen.getByText('GROUP_STAGE')).toBeInTheDocument();
  });

  it('does not render group/stage when absent', () => {
    const { container } = render(<MatchCard m={makeMatch({ group: undefined, stage: undefined })} />);
    const metaSpans = container.querySelectorAll('.meta span');
    // Should have exactly 2: status and date/time
    expect(metaSpans.length).toBe(2);
  });

  it('renders date and time from utcDate', () => {
    const { container } = render(<MatchCard m={makeMatch()} />);
    const metaSpans = container.querySelectorAll('.meta span');
    // Second span should contain date/time text (locale-dependent)
    expect(metaSpans[1].textContent).toBeTruthy();
  });
});
