## How It Works

MCP for Unity connects your tools using two components:

1.  **MCP for Unity Bridge:** A Unity package running inside the Editor. (Installed via Package Manager).
2.  **MCP for Unity Server:** A Python server that runs locally, communicating between the Unity Bridge and your MCP Client. (Installed automatically by the package on first run or via Auto-Setup; manual setup is available as a fallback).

<img width="562" height="121" alt="image" src="https://github.com/user-attachments/assets/9abf9c66-70d1-4b82-9587-658e0d45dc3e" />

---

## Installation ⚙️

### Prerequisites

- **Python:** Version 3.12 or newer. [Download Python](https://www.python.org/downloads/)
- **Unity Hub & Editor:** Version 2021.3 LTS or newer. [Download Unity](https://unity.com/download)
- **uv (Python toolchain manager):**

  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  winget install --id=astral-sh.uv  -e

  # Docs: https://docs.astral.sh/uv/getting-started/installation/
  ```

- **An MCP Client:** : [Claude Desktop](https://claude.ai/download) | [Claude Code](https://github.com/anthropics/claude-code) | [Cursor](https://www.cursor.com/en/downloads) | [Visual Studio Code Copilot](https://code.visualstudio.com/docs/copilot/overview) | [Windsurf](https://windsurf.com) | Others work with manual config

- <details> <summary><strong>[Optional] Roslyn for Advanced Script Validation</strong></summary>

  For **Strict** validation level that catches undefined namespaces, types, and methods:

  **Method 1: NuGet for Unity (Recommended)**
  1. Install [NuGetForUnity](https://github.com/GlitchEnzo/NuGetForUnity)
  2. Go to `Window > NuGet Package Manager`
  3. Search for `Microsoft.CodeAnalysis`, select version 4.14.0, and install the package
  4. Also install package `SQLitePCLRaw.core` and `SQLitePCLRaw.bundle_e_sqlite3`.
  5. Go to `Player Settings > Scripting Define Symbols`
  6. Add `USE_ROSLYN`
  7. Restart Unity

  **Method 2: Manual DLL Installation**
  1. Download Microsoft.CodeAnalysis.CSharp.dll and dependencies from [NuGet](https://www.nuget.org/packages/Microsoft.CodeAnalysis.CSharp/)
  2. Place DLLs in `Assets/Plugins/` folder
  3. Ensure .NET compatibility settings are correct
  4. Add `USE_ROSLYN` to Scripting Define Symbols
  5. Restart Unity

  **Note:** Without Roslyn, script validation falls back to basic structural checks. Roslyn enables full C# compiler diagnostics with precise error reporting.</details>

---

### 🚀 Arch Linux Quick Setup Script

If you're on Arch Linux and use Visual Studio Code as your MCP client, run the helper script in `Bash/install_unity_mcp.sh` to install the MCP server dependencies, clone the latest `unity-mcp` repository, and configure `~/.config/Code/User/mcp.json` automatically:

```bash
chmod +x Bash/install_unity_mcp.sh
./Bash/install_unity_mcp.sh
```

The script requires `sudo` access for `pacman` and optionally uses `yay` or `flatpak` to install Unity Hub. After it finishes, continue with the Unity-side steps below to import the MCP for Unity Bridge package inside your project.

---

### 🌟 Step 1: Install the Unity Package

#### To install via Git URL

1.  Open your Unity project.
2.  Go to `Window > Package Manager`.
3.  Click `+` -> `Add package from git URL...`.
4.  Enter:
    ```
    https://github.com/CoplayDev/unity-mcp.git?path=/UnityMcpBridge
    ```
5.  Click `Add`.
6.  The MCP server is installed automatically by the package on first run or via Auto-Setup. If that fails, use Manual Configuration (below).

#### To install via OpenUPM

1.  Install the [OpenUPM CLI](https://openupm.com/docs/getting-started-cli.html)
2.  Open a terminal (PowerShell, Terminal, etc.) and navigate to your Unity project directory
3.  Run `openupm add com.coplaydev.unity-mcp`

**Note:** If you installed the MCP Server before Coplay's maintenance, you will need to uninstall the old package before re-installing the new one.

### 🛠️ Step 2: Configure Your MCP Client

Connect your MCP Client (Claude, Cursor, etc.) to the Python server set up in Step 1 (auto) or via Manual Configuration (below).

<img width="648" height="599" alt="MCPForUnity-Readme-Image" src="https://github.com/user-attachments/assets/b4a725da-5c43-4bd6-80d6-ee2e3cca9596" />

**Option A: Auto-Setup (Recommended for Claude/Cursor/VSC Copilot)**

1.  In Unity, go to `Window > MCP for Unity`.
2.  Click `Auto-Setup`.
3.  Look for a green status indicator 🟢 and "Connected ✓". _(This attempts to modify the MCP Client's config file automatically)._

<details><summary><strong>Client-specific troubleshooting</strong></summary>

- **VSCode**: uses `Code/User/mcp.json` with top-level `servers.unityMCP` and `"type": "stdio"`. On Windows, MCP for Unity writes an absolute `uv.exe` (prefers WinGet Links shim) to avoid PATH issues.
- **Cursor / Windsurf** [(**help link**)](https://github.com/CoplayDev/unity-mcp/wiki/1.-Fix-Unity-MCP-and-Cursor,-VSCode-&-Windsurf): if `uv` is missing, the MCP for Unity window shows "uv Not Found" with a quick [HELP] link and a "Choose `uv` Install Location" button.
- **Claude Code** [(**help link**)](https://github.com/CoplayDev/unity-mcp/wiki/2.-Fix-Unity-MCP-and-Claude-Code): if `claude` isn't found, the window shows "Claude Not Found" with [HELP] and a "Choose Claude Location" button. Unregister now updates the UI immediately.</details>

**Option B: Manual Configuration**

If Auto-Setup fails or you use a different client:

1.  **Find your MCP Client's configuration file.** (Check client documentation).
    - _Claude Example (macOS):_ `~/Library/Application Support/Claude/claude_desktop_config.json`
    - _Claude Example (Windows):_ `%APPDATA%\Claude\claude_desktop_config.json`
2.  **Edit the file** to add/update the `mcpServers` section, using the _exact_ paths from Step 1.

<details>
<summary><strong>Click for Client-Specific JSON Configuration Snippets...</strong></summary>

**VSCode (all OS)**

```json
{
  "servers": {
    "unityMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "<ABSOLUTE_PATH_TO>/UnityMcpServer/src",
        "run",
        "server.py"
      ],
      "type": "stdio"
    }
  }
}
```

**Linux:**

```json
{
  "mcpServers": {
    "UnityMCP": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/YOUR_USERNAME/.local/share/UnityMCP/UnityMcpServer/src",
        "server.py"
      ]
    }
    // ... other servers might be here ...
  }
}
```

(Replace YOUR_USERNAME)

</details>

---

## Usage ▶️

1. **Open your Unity Project.** The MCP for Unity package should connect automatically. Check status via Window > MCP for Unity.

2. **Start your MCP Client** (Claude, Cursor, etc.). It should automatically launch the MCP for Unity Server (Python) using the configuration from Installation Step 2.

3. **Interact!** Unity tools should now be available in your MCP Client.

   Example Prompt: `Create a 3D player controller`, `Create a tic-tac-toe game in 3D`, `Create a cool shader and apply to a cube`.

## Troubleshooting ❓

<details>  
<summary><strong>Click to view common issues and fixes...</strong></summary>

- **Unity Bridge Not Running/Connecting:**
  - Ensure Unity Editor is open.
  - Check the status window: Window > MCP for Unity.
  - Restart Unity.
- **MCP Client Not Connecting / Server Not Starting:**
  - **Verify Server Path:** Double-check the --directory path in your MCP Client's JSON config. It must exactly match the installation location:
    - **Windows:** `%USERPROFILE%\AppData\Local\UnityMCP\UnityMcpServer\src`
    - **macOS:** `~/Library/AppSupport/UnityMCP/UnityMcpServer\src`
    - **Linux:** `~/.local/share/UnityMCP/UnityMcpServer\src`
  - **Verify uv:** Make sure `uv` is installed and working (`uv --version`).
  - **Run Manually:** Try running the server directly from the terminal to see errors:
    ```bash
    cd /path/to/your/UnityMCP/UnityMcpServer/src
    uv run server.py
    ```
- **Auto-Configure Failed:**
  - Use the Manual Configuration steps. Auto-configure might lack permissions to write to the MCP client's config file.
