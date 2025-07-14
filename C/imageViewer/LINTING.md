# C Language Linter Setup for imageViewer Project

This directory contains a comprehensive linting setup for the imageViewer C project.

## Tools Included

### 1. **clang-tidy** - Static Analysis
- Configuration: `.clang-tidy`
- Checks for bugs, performance issues, and style violations
- Enforces modern C coding standards

### 2. **clang-format** - Code Formatting  
- Configuration: `.clang-format`
- Automatically formats code to consistent style
- 100-character line limit, 4-space indentation

### 3. **cppcheck** - Additional Static Analysis
- Detects memory leaks, null pointer dereferences
- Checks for undefined behavior

### 4. **gcc with warnings** - Compiler Analysis
- Comprehensive warning flags
- Standards compliance checking

## Usage

### Quick Start
```bash
# Install dependencies (Arch Linux)
make deps-arch

# Run all lint checks
make lint

# Format code
make format

# Run all checks
make check

# Check for memory leaks
make memcheck
```

### Individual Commands
```bash
# Manual linting
./lint.sh

# Format specific file
clang-format -i main.c

# Run clang-tidy
clang-tidy main.c -- -I/usr/include/SDL2 -D_REENTRANT

# Run cppcheck
cppcheck --enable=all main.c
```

## VS Code Integration

The `.vscode/settings.json` file provides:
- Automatic formatting on save
- C99 standard compliance
- IntelliSense configuration for SDL2
- Integrated linting with clang-tidy and cppcheck

## Recommended Extensions for VS Code
- C/C++ (Microsoft)
- clang-tidy (mine-cetinkaya-fianso)
- cppcheck (unixwrapped)

## Linting Rules

### Enabled Checks
- **clang-diagnostic-***: Compiler diagnostics
- **clang-analyzer-***: Static analysis
- **bugprone-***: Bug-prone patterns
- **cert-***: CERT secure coding standards
- **misc-***: Miscellaneous checks
- **performance-***: Performance improvements
- **portability-***: Cross-platform issues
- **readability-***: Code readability

### Disabled Checks
- `readability-magic-numbers`: Allows constants like window dimensions
- `cert-err33-c`: Allows ignoring some function return values
- `misc-unused-parameters`: Common in callback functions

## Code Quality Workflow

1. **Write Code**: Develop features in `main.c`
2. **Lint**: Run `make lint` to check for issues
3. **Format**: Run `make format` to fix formatting
4. **Build**: Run `make` to compile
5. **Test**: Run `make test` with sample images
6. **Memory Check**: Run `make memcheck` for leak detection

## Configuration Files

- `.clang-tidy`: Static analysis rules
- `.clang-format`: Code formatting style
- `.vscode/settings.json`: VS Code integration
- `lint.sh`: Comprehensive linting script
- `Makefile`: Build and quality targets

## Installation on Different Systems

### Arch Linux
```bash
sudo pacman -S clang cppcheck valgrind
```

### Ubuntu/Debian
```bash
sudo apt install clang-tidy cppcheck clang-format valgrind
```

### Fedora/RHEL
```bash
sudo dnf install clang-tools-extra cppcheck clang valgrind
```

This setup ensures high code quality, consistency, and helps catch potential issues early in development.
