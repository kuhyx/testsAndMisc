/**
 * Drives the solver worker from React.
 *
 * Two things this has to get right:
 *
 *   Stale replies. Requests are tagged with an incrementing id and a reply whose
 *   id is not the current one is dropped, so a slow solve for an inventory you
 *   have since changed can never overwrite the answer for the one on screen.
 *
 *   No cascading renders. The effect does external work only — post a message —
 *   and every piece of state is either written from the worker's own callback or
 *   derived during render. Nothing calls setState synchronously in an effect
 *   body.
 */

import { useEffect, useRef, useState } from "react";
import type { SolveRequest, SolveResponse } from "../core/solve.ts";
import type { WorkerReply, WorkerRequest } from "../worker/solver.worker.ts";

export interface SolverState {
  /** The latest completed solve, or null before the first one lands. */
  readonly result: SolveResponse | null;
  /** Why the last request could not be solved, e.g. too few dice. */
  readonly error: string | null;
  /** True while a request is outstanding. */
  readonly solving: boolean;
}

/** Anything that can accept solve requests and reply — the worker, or a fake. */
export interface SolverPort {
  postMessage: (message: WorkerRequest) => void;
  addEventListener: (
    type: "message",
    listener: (event: MessageEvent<WorkerReply>) => void,
  ) => void;
  removeEventListener: (
    type: "message",
    listener: (event: MessageEvent<WorkerReply>) => void,
  ) => void;
  terminate?: () => void;
}

/**
 * Build the real worker. Injectable so tests can drive a fake port instead of
 * relying on jsdom's worker support.
 *
 * @returns A port backed by a fresh Web Worker.
 */
export function createSolverWorker(): SolverPort {
  return new Worker(new URL("../worker/solver.worker.ts", import.meta.url), {
    type: "module",
  });
}

/** The last answer received, tagged with the request that produced it. */
interface Answer {
  readonly request: SolveRequest;
  readonly result: SolveResponse | null;
  readonly error: string | null;
}

/**
 * Solve an inventory in the background, re-solving whenever it changes.
 *
 * @param request - The current solve request, or null when there is nothing to
 *   solve yet (fewer than six dice owned).
 * @param createPort - Factory for the worker port; overridden in tests. Only the
 *   value passed on the first render is used.
 * @returns The latest result, any error, and whether a solve is in flight.
 */
export function useSolver(
  request: SolveRequest | null,
  createPort: () => SolverPort = createSolverWorker,
): SolverState {
  const [answer, setAnswer] = useState<Answer | null>(null);
  // The port lives in state, not a ref, so the request effect can depend on it
  // and re-run once it exists. On the very first render there is no port yet.
  const [port, setPort] = useState<SolverPort | null>(null);

  const latestId = useRef(0);
  const latestRequest = useRef<SolveRequest | null>(null);
  // Only the first factory is ever used. Holding it in a ref means an inline
  // arrow at the call site cannot tear the worker down and rebuild it on every
  // render — building a worker is expensive, and any solve in flight would be
  // discarded with it.
  const factory = useRef(createPort);

  useEffect(() => {
    const created = factory.current();
    setPort(created);

    const onMessage = (event: MessageEvent<WorkerReply>): void => {
      const reply = event.data;
      const asked = latestRequest.current;
      // Drop answers to questions we are no longer asking.
      if (reply.id !== latestId.current || !asked) {
        return;
      }
      setAnswer(
        reply.ok
          ? { request: asked, result: reply.response, error: null }
          : { request: asked, result: null, error: reply.error },
      );
    };

    created.addEventListener("message", onMessage);
    return () => {
      created.removeEventListener("message", onMessage);
      created.terminate?.();
      setPort(null);
    };
  }, []);

  useEffect(() => {
    if (!port) {
      return;
    }
    // Bump the id even when there is nothing to ask, so a reply already on its
    // way for the previous inventory is discarded rather than applied.
    latestId.current += 1;
    latestRequest.current = request;
    if (request) {
      port.postMessage({ id: latestId.current, request });
    }
  }, [port, request]);

  if (!request) {
    return { result: null, error: null, solving: false };
  }
  if (!answer) {
    return { result: null, error: null, solving: true };
  }
  const solving = answer.request !== request;
  return {
    // The previous answer stays on screen while a new one is computed, so the
    // panel dims rather than blanking out.
    result: answer.result,
    error: solving ? null : answer.error,
    solving,
  };
}
