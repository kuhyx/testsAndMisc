/**
 * Tests for the worker-driving hook, especially the parts that only matter when
 * things go slightly wrong: a reply arriving for a question no longer being
 * asked, and tearing the worker down on unmount.
 */

import { act, render, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { SolveRequest, SolveResponse } from "../core/solve.ts";
import type { WorkerReply, WorkerRequest } from "../worker/solver.worker.ts";
import { createSolverWorker, useSolver } from "./useSolver.ts";
import type { SolverPort } from "./useSolver.ts";

/** A controllable port: records requests, replies only when told to. */
function makePort(): SolverPort & {
  sent: WorkerRequest[];
  reply: (reply: WorkerReply) => void;
  terminated: () => number;
} {
  const listeners = new Set<(event: MessageEvent<WorkerReply>) => void>();
  const sent: WorkerRequest[] = [];
  let terminations = 0;
  return {
    sent,
    postMessage: (message) => sent.push(message),
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
    terminate: () => {
      terminations += 1;
    },
    reply: (reply) => {
      act(() => {
        for (const listener of listeners) {
          listener({ data: reply } as MessageEvent<WorkerReply>);
        }
      });
    },
    terminated: () => terminations,
  };
}

const request: SolveRequest = { diceCounts: { ordinary: 6 }, badgeIds: [] };
const response = { dice: [], inventorySize: 6 } as unknown as SolveResponse;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useSolver", () => {
  it("sends the request once the port exists", async () => {
    const port = makePort();
    renderHook(() => useSolver(request, () => port));
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });
    expect(port.sent[0].request).toEqual(request);
  });

  it("reports a successful solve", async () => {
    const port = makePort();
    const { result } = renderHook(() => useSolver(request, () => port));
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });
    expect(result.current.solving).toBe(true);

    port.reply({ id: port.sent[0].id, ok: true, response });
    expect(result.current.result).toBe(response);
    expect(result.current.solving).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("reports a failure", async () => {
    const port = makePort();
    const { result } = renderHook(() => useSolver(request, () => port));
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });

    port.reply({ id: port.sent[0].id, ok: false, error: "boom" });
    expect(result.current.error).toBe("boom");
    expect(result.current.result).toBeNull();
  });

  it("ignores a reply to a question it is no longer asking", async () => {
    const port = makePort();
    const { result } = renderHook(() => useSolver(request, () => port));
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });

    // A slow answer to an older inventory must not overwrite the current one.
    port.reply({ id: port.sent[0].id - 1, ok: true, response });
    expect(result.current.result).toBeNull();
    expect(result.current.solving).toBe(true);
  });

  it("clears the result when there is nothing to solve", async () => {
    const port = makePort();
    const initialProps: { current: SolveRequest | null } = { current: request };
    const { result, rerender } = renderHook(
      ({ current }: { current: SolveRequest | null }) => useSolver(current, () => port),
      { initialProps },
    );
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });
    port.reply({ id: port.sent[0].id, ok: true, response });
    expect(result.current.result).toBe(response);

    rerender({ current: null });
    expect(result.current.result).toBeNull();
    expect(result.current.solving).toBe(false);
    // And nothing new was asked of the worker.
    expect(port.sent).toHaveLength(1);
  });

  it("hides a stale error while the next solve is running", async () => {
    const port = makePort();
    const initialProps: { current: SolveRequest | null } = { current: request };
    const { result, rerender } = renderHook(
      ({ current }: { current: SolveRequest | null }) => useSolver(current, () => port),
      { initialProps },
    );
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });
    port.reply({ id: port.sent[0].id, ok: false, error: "boom" });
    expect(result.current.error).toBe("boom");

    // A new inventory is being solved: the old failure no longer describes it.
    rerender({ current: { diceCounts: { weighted: 6 }, badgeIds: [] } });
    expect(result.current.solving).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("terminates the worker on unmount", async () => {
    const port = makePort();
    const { unmount } = renderHook(() => useSolver(request, () => port));
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });
    unmount();
    expect(port.terminated()).toBe(1);
  });

  it("copes with a port that cannot be terminated", async () => {
    const port = makePort();
    const withoutTerminate: SolverPort = {
      postMessage: port.postMessage.bind(port),
      addEventListener: port.addEventListener.bind(port),
      removeEventListener: port.removeEventListener.bind(port),
    };
    const { unmount } = renderHook(() => useSolver(request, () => withoutTerminate));
    await waitFor(() => {
      expect(port.sent).toHaveLength(1);
    });
    expect(() => {
      unmount();
    }).not.toThrow();
  });
});

describe("createSolverWorker", () => {
  it("builds a module worker pointing at the solver", () => {
    const constructed: { url: string; options: unknown }[] = [];
    class FakeWorker {
      addEventListener = vi.fn();
      removeEventListener = vi.fn();
      postMessage = vi.fn();
      constructor(url: URL, options: unknown) {
        constructed.push({ url: url.href, options });
      }
    }
    vi.stubGlobal("Worker", FakeWorker);

    createSolverWorker();
    expect(constructed).toHaveLength(1);
    expect(constructed[0].url).toMatch(/solver\.worker/);
    expect(constructed[0].options).toEqual({ type: "module" });
  });
});

describe("useSolver default port", () => {
  it("falls back to a real worker when no factory is supplied", () => {
    const created: unknown[] = [];
    class FakeWorker {
      addEventListener = vi.fn();
      removeEventListener = vi.fn();
      postMessage = vi.fn();
      terminate = vi.fn();
      constructor() {
        created.push(this);
      }
    }
    vi.stubGlobal("Worker", FakeWorker);

    /**
     * Minimal probe component exercising the hook's default argument.
     *
     * @returns Nothing rendered; the hook is the point.
     */
    function Probe(): null {
      useSolver(request);
      return null;
    }
    render(<Probe />);
    expect(created).toHaveLength(1);
  });
});
