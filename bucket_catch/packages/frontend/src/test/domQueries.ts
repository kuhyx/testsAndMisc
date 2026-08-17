/**
 * DOM query helpers shared by the component tests.
 *
 * Lives under src/test/ because the coverage config excludes that path — a
 * helper placed beside a component would be counted as production code and
 * break the 100% gate.
 */

/**
 * Query one element and narrow it, failing the test if it is absent.
 *
 * Both `as HTMLElement` and `!` are rejected here — the former by
 * non-nullable-type-assertion-style, the latter by no-non-null-assertion — so
 * the narrowing is done with a real check that also gives a useful message.
 */
export const must = (el: Element | null, what: string): HTMLElement => {
  if (!(el instanceof HTMLElement)) {
    throw new Error(`expected to find ${what}`);
  }
  return el;
};
