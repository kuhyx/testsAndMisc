## Part 2: Language Considerations

### Shell (Bash) Limitations

**Pros:**

- Native to the system, no dependencies
- Direct access to systemd, chattr, filesystem
- Fast for simple operations

**Cons:**

- No persistent daemon capability (need systemd for that)
- Race conditions in file operations
- Complex state management is fragile
- No proper event loop for window monitoring
- Cannot easily monitor process list in real-time

### Python Advantages for Certain Tasks

**Where Python would be better:**

1. **Process monitoring daemon** - Watch for Steam/browsers in real-time with proper event loop
2. **Window management** - Using `python-xlib` for proper X11 interaction
3. **Complex state machines** - Like the screen locker
4. **Cross-repo integration** - The screen_lock.py already shows good patterns

### Recommendation

| Component         | Keep Bash | Move to Python | Reason                               |
| ----------------- | --------- | -------------- | ------------------------------------ |
| hosts guard       | ✅        |                | Simple file ops, systemd integration |
| shutdown schedule | ✅        |                | Systemd timers, config files         |
| screen locker     |           | ✅ Already     | Complex UI, state machine            |
| pacman wrapper    | ✅        |                | Must intercept pacman                |
| compulsive block  |           | ✅             | Needs daemon for auto-close          |
| music wrapper     |           | ✅             | Needs real-time process monitoring   |

**New Python Daemon Needed:** A single "digital wellbeing daemon" that:

1. Monitors running processes
2. Auto-closes apps after timeout
3. Enforces Steam/browser mutual exclusion
4. Can be controlled via DBus
