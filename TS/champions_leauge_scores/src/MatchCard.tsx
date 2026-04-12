import { useMemo } from 'react';

export type Score = {
  fullTime?: { home?: number | null; away?: number | null };
  halfTime?: { home?: number | null; away?: number | null };
  winner?: string | null;
};

export type Match = {
  id: number;
  utcDate: string;
  status: string;
  stage?: string;
  group?: string;
  matchday?: number;
  homeTeam: string;
  awayTeam: string;
  score: Score;
  competition?: string;
  venue?: string;
  referees?: string[];
};

export function MatchCard({ m }: { m: Match }) {
  const kickoff = useMemo(() => new Date(m.utcDate), [m.utcDate]);
  const time = kickoff.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const date = kickoff.toLocaleDateString();
  const ftHome = m.score.fullTime?.home ?? '-';
  const ftAway = m.score.fullTime?.away ?? '-';
  const statusNice = m.status.replace('_', ' ');

  return (
    <div className="card">
      <div className="row teams">
        <span className="home">{m.homeTeam}</span>
        <span className="score">{ftHome} : {ftAway}</span>
        <span className="away">{m.awayTeam}</span>
      </div>
      <div className="row meta">
        <span>{statusNice}</span>
        <span>{date} {time}</span>
        {m.group && <span>{m.group}</span>}
        {m.stage && <span>{m.stage}</span>}
      </div>
    </div>
  );
}
