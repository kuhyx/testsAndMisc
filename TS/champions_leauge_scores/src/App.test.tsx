import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import App from './App';

const mockApiResponse = {
  count: 1,
  matches: [
    {
      id: 1,
      utcDate: '2024-09-17T20:00:00Z',
      status: 'LIVE',
      stage: 'GROUP_STAGE',
      group: 'Group A',
      matchday: 1,
      homeTeam: 'Team A',
      awayTeam: 'Team B',
      score: { fullTime: { home: 2, away: 1 } },
    },
  ],
  fetchedAt: '2024-09-17T20:05:00Z',
};

const emptyApiResponse = {
  count: 0,
  matches: [],
  fetchedAt: '2024-09-17T20:05:00Z',
};

describe('App', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  it('renders heading and shows loading', async () => {
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));
    await act(async () => {
      render(<App />);
    });
    expect(screen.getByText('UEFA Champions League — Live Scores')).toBeInTheDocument();
    expect(screen.getByText('Live right now')).toBeInTheDocument();
    expect(screen.getByText('Today')).toBeInTheDocument();
    const loadingElements = screen.getAllByText('Loading…');
    expect(loadingElements.length).toBeGreaterThanOrEqual(2);
  });

  it('renders matches after fetch', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockApiResponse),
    });

    await act(async () => {
      render(<App />);
    });

    expect(screen.getAllByText('Team A').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Team B').length).toBeGreaterThanOrEqual(1);
  });

  it('shows "No live matches." when live data is empty', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(emptyApiResponse),
    });

    await act(async () => {
      render(<App />);
    });

    expect(screen.getByText('No live matches.')).toBeInTheDocument();
  });

  it('shows error on non-429 fetch failure', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue({ message: 'Network error', status: 500 });

    await act(async () => {
      render(<App />);
    });

    const errorElements = screen.getAllByText('Network error');
    expect(errorElements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows retryInSec countdown on 429', async () => {
    vi.useFakeTimers();
    globalThis.fetch = vi.fn().mockRejectedValue({ status: 429, waitSec: 5, message: 'Rate limited' });

    await act(async () => {
      render(<App />);
    });

    const errorElements = screen.getAllByText(/Rate limited/);
    expect(errorElements.length).toBeGreaterThanOrEqual(1);

    // Check the countdown display
    const countdown = screen.getAllByText(/\(\d+s\)/);
    expect(countdown.length).toBeGreaterThanOrEqual(1);
  });
});
