# The test pyramid and writing good tests

## The Test Pyramid

Invest testing effort according to the pyramid — most tests should be small and fast, with progressively fewer tests at higher levels:

```
          ╱╲
         ╱  ╲         E2E Tests (~5%)
        ╱    ╲        Full user flows, real browser
       ╱──────╲
      ╱        ╲      Integration Tests (~15%)
     ╱          ╲     Component interactions, API boundaries
    ╱────────────╲
   ╱              ╲   Unit Tests (~80%)
  ╱                ╲  Pure logic, isolated, milliseconds each
 ╱──────────────────╲
```

**The Beyonce Rule:** If you liked it, you should have put a test on it. Infrastructure changes, refactoring, and migrations are not responsible for catching your bugs — your tests are. If a change breaks your code and you didn't have a test for it, that's on you.

### Test Sizes (Resource Model)

Beyond the pyramid levels, classify tests by what resources they consume:

| Size       | Constraints                                            | Speed        | Example                                                |
| ---------- | ------------------------------------------------------ | ------------ | ------------------------------------------------------ |
| **Small**  | Single process, no I/O, no network, no database        | Milliseconds | Pure function tests, data transforms                   |
| **Medium** | Multi-process OK, localhost only, no external services | Seconds      | API tests with test DB, component tests                |
| **Large**  | Multi-machine OK, external services allowed            | Minutes      | E2E tests, performance benchmarks, staging integration |

Small tests should make up the vast majority of your suite. They're fast, reliable, and easy to debug when they fail.

### Decision Guide

```
Is it pure logic with no side effects?
  → Unit test (small)

Does it cross a boundary (API, database, file system)?
  → Integration test (medium)

Is it a critical user flow that must work end-to-end?
  → E2E test (large) — limit these to critical paths
```

## Writing Good Tests

### Test State, Not Interactions

Assert on the _outcome_ of an operation, not on which methods were called internally. Tests that verify method call sequences break when you refactor, even if the behavior is unchanged.

```typescript
// Good: Tests what the function does (state-based)
it("returns tasks sorted by creation date, newest first", async () => {
  const tasks = await listTasks({ sortBy: "createdAt", sortOrder: "desc" });
  expect(tasks[0].createdAt.getTime()).toBeGreaterThan(
    tasks[1].createdAt.getTime(),
  );
});

// Bad: Tests how the function works internally (interaction-based)
it("calls db.query with ORDER BY created_at DESC", async () => {
  await listTasks({ sortBy: "createdAt", sortOrder: "desc" });
  expect(db.query).toHaveBeenCalledWith(
    expect.stringContaining("ORDER BY created_at DESC"),
  );
});
```

### DAMP Over DRY in Tests

In production code, DRY (Don't Repeat Yourself) is usually right. In tests, **DAMP (Descriptive And Meaningful Phrases)** is better. A test should read like a specification — each test should tell a complete story without requiring the reader to trace through shared helpers.

```typescript
// DAMP: Each test is self-contained and readable
it("rejects tasks with empty titles", () => {
  const input = { title: "", assignee: "user-1" };
  expect(() => createTask(input)).toThrow("Title is required");
});

it("trims whitespace from titles", () => {
  const input = { title: "  Buy groceries  ", assignee: "user-1" };
  const task = createTask(input);
  expect(task.title).toBe("Buy groceries");
});

// Over-DRY: Shared setup obscures what each test actually verifies
// (Don't do this just to avoid repeating the input shape)
```

Duplication in tests is acceptable when it makes each test independently understandable.

### Prefer Real Implementations Over Mocks

Use the simplest test double that gets the job done. The more your tests use real code, the more confidence they provide.

```
Preference order (most to least preferred):
1. Real implementation  → Highest confidence, catches real bugs
2. Fake                 → In-memory version of a dependency (e.g., fake DB)
3. Stub                 → Returns canned data, no behavior
4. Mock (interaction)   → Verifies method calls — use sparingly
```

**Use mocks only when:** the real implementation is too slow, non-deterministic, or has side effects you can't control (external APIs, email sending). Over-mocking creates tests that pass while production breaks.

### Use the Arrange-Act-Assert Pattern

```typescript
it("marks overdue tasks when deadline has passed", () => {
  // Arrange: Set up the test scenario
  const task = createTask({
    title: "Test",
    deadline: new Date("2025-01-01"),
  });

  // Act: Perform the action being tested
  const result = checkOverdue(task, new Date("2025-01-02"));

  // Assert: Verify the outcome
  expect(result.isOverdue).toBe(true);
});
```

### One Assertion Per Concept

```typescript
// Good: Each test verifies one behavior
it('rejects empty titles', () => { ... });
it('trims whitespace from titles', () => { ... });
it('enforces maximum title length', () => { ... });

// Bad: Everything in one test
it('validates titles correctly', () => {
  expect(() => createTask({ title: '' })).toThrow();
  expect(createTask({ title: '  hello  ' }).title).toBe('hello');
  expect(() => createTask({ title: 'a'.repeat(256) })).toThrow();
});
```

### Name Tests Descriptively

```typescript
// Good: Reads like a specification
describe('TaskService.completeTask', () => {
  it('sets status to completed and records timestamp', ...);
  it('throws NotFoundError for non-existent task', ...);
  it('is idempotent — completing an already-completed task is a no-op', ...);
  it('sends notification to task assignee', ...);
});

// Bad: Vague names
describe('TaskService', () => {
  it('works', ...);
  it('handles errors', ...);
  it('test 3', ...);
});
```
