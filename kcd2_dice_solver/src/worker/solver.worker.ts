/**
 * Web Worker wrapper around the solver.
 *
 * A full solve runs tens of thousands of exact evaluations plus a Monte Carlo
 * run, which takes a couple of seconds on a large inventory. Off the main thread
 * the search box and the steppers stay responsive while it runs.
 */

import { solve } from "../core/solve.ts";
import type { SolveRequest, SolveResponse } from "../core/solve.ts";

/** A solve request tagged so stale replies can be discarded. */
export interface WorkerRequest {
  readonly id: number;
  readonly request: SolveRequest;
}

/** Either a completed solve or the reason it could not run. */
export type WorkerReply =
  | { readonly id: number; readonly ok: true; readonly response: SolveResponse }
  | { readonly id: number; readonly ok: false; readonly error: string };

self.addEventListener("message", (event: MessageEvent<WorkerRequest>) => {
  const { id, request } = event.data;
  try {
    const response = solve(request);
    const reply: WorkerReply = { id, ok: true, response };
    self.postMessage(reply);
  } catch (error) {
    const reply: WorkerReply = {
      id,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
    self.postMessage(reply);
  }
});
