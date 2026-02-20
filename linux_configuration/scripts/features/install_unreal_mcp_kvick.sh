#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Unreal MCP Installer for Arch Linux ===${NC}"

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
for cmd in git python pip; do
	if ! command -v $cmd &>/dev/null; then
		echo -e "${RED}Error: $cmd is not installed. Please install it (e.g., sudo pacman -S $cmd)${NC}"
		exit 1
	fi
done

# Get Unreal Project Path
PROJECT_PATH="$1"
if [ -z "$PROJECT_PATH" ]; then
	echo -e "${YELLOW}Please enter the path to your Unreal Engine Project (the folder containing .uproject file):${NC}"
	read -r -e -p "> " PROJECT_PATH
fi

# Validate path
# Expand tilde if present
PROJECT_PATH="${PROJECT_PATH/#\~/$HOME}"
PROJECT_PATH=$(realpath "$PROJECT_PATH" 2>/dev/null || echo "")

if [ -z "$PROJECT_PATH" ] || [ ! -d "$PROJECT_PATH" ]; then
	echo -e "${RED}Error: Invalid directory: $PROJECT_PATH${NC}"
	exit 1
fi

UPROJECT_FILES=("$PROJECT_PATH"/*.uproject)
if [ ! -e "${UPROJECT_FILES[0]}" ]; then
	echo -e "${RED}Error: No .uproject file found in $PROJECT_PATH${NC}"
	exit 1
fi

echo -e "${GREEN}Target Project: $PROJECT_PATH${NC}"

# Create Plugins directory if it doesn't exist
PLUGINS_DIR="$PROJECT_PATH/Plugins"
mkdir -p "$PLUGINS_DIR"

# Clone UnrealMCP
MCP_PLUGIN_DIR="$PLUGINS_DIR/UnrealMCP"
if [ -d "$MCP_PLUGIN_DIR" ]; then
	echo -e "${BLUE}UnrealMCP already exists. Updating...${NC}"
	cd "$MCP_PLUGIN_DIR"
	git pull
else
	echo -e "${BLUE}Cloning UnrealMCP...${NC}"
	git clone https://github.com/kvick-games/UnrealMCP.git "$MCP_PLUGIN_DIR"
fi

# Setup Python Environment
echo -e "${BLUE}Setting up Python environment...${NC}"
MCP_DIR="$MCP_PLUGIN_DIR/MCP"

if [ ! -f "$MCP_DIR/unreal_mcp_bridge.py" ]; then
	echo -e "${RED}Error: unreal_mcp_bridge.py not found in $MCP_DIR. Repository structure might have changed.${NC}"
	exit 1
fi

VENV_DIR="$MCP_DIR/python_env"

if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtual environment..."
	python -m venv "$VENV_DIR"
fi

# Install requirements
echo "Installing dependencies in virtual environment..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip >/dev/null
pip install "mcp>=0.1.0" >/dev/null

# Patch unreal_mcp_bridge.py for newer mcp package compatibility
# The newer mcp package (1.x) renamed 'description' parameter to 'instructions'
BRIDGE_SCRIPT="$MCP_DIR/unreal_mcp_bridge.py"
if grep -q 'description="Unreal Engine integration' "$BRIDGE_SCRIPT" 2>/dev/null; then
	echo "Patching unreal_mcp_bridge.py for mcp package compatibility..."
	sed -i 's/description="Unreal Engine integration through the Model Context Protocol"/instructions="Unreal Engine integration through the Model Context Protocol"/' "$BRIDGE_SCRIPT"
fi

# Fix case-sensitive includes for Linux (Windows is case-insensitive, Linux is not)
echo "Fixing case-sensitive includes for Linux..."
find "$MCP_PLUGIN_DIR/Source/" \( -name "*.cpp" -o -name "*.h" \) -exec sed -i 's/HAL\/PlatformFilemanager\.h/HAL\/PlatformFileManager.h/g' {} + 2>/dev/null || true

# Create Linux Run Script
RUN_SCRIPT="$MCP_DIR/run_unreal_mcp.sh"
echo -e "${BLUE}Creating run script at $RUN_SCRIPT...${NC}"

cat <<EOF >"$RUN_SCRIPT"
#!/bin/bash
set -e
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
source "\$SCRIPT_DIR/python_env/bin/activate"
# Run the bridge script, passing any arguments
exec python "\$SCRIPT_DIR/unreal_mcp_bridge.py" "\$@"
EOF

chmod +x "$RUN_SCRIPT"
echo -e "${GREEN}Run script created successfully.${NC}"

# VS Code / MCP Configuration Helper
echo -e "${BLUE}=== Configuration Setup ===${NC}"

# Python script to update JSON configs
CONFIG_UPDATER_SCRIPT=$(mktemp)
cat <<EOF >"$CONFIG_UPDATER_SCRIPT"
import json
import os
import sys

config_path = sys.argv[1]
run_script = sys.argv[2]
config_type = sys.argv[3] # 'claude' or 'vscode_settings' or 'roo_code'

print(f"Updating {config_path}...")

data = {}
if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse {config_path}. Starting with empty config.")

if config_type == 'claude' or config_type == 'roo_code':
    # Standard MCP config format
    if 'mcpServers' not in data:
        data['mcpServers'] = {}

    data['mcpServers']['unreal'] = {
        'command': run_script,
        'args': []
    }
elif config_type == 'vscode_settings':
    # VS Code settings.json format (example for some extensions)
    # This varies by extension, but we'll add a generic mcp.servers key if it exists
    # or just print instructions.
    pass

# Ensure directory exists
os.makedirs(os.path.dirname(config_path), exist_ok=True)

with open(config_path, 'w') as f:
    json.dump(data, f, indent=4)

print("Config updated successfully.")
EOF

# Detect and offer to update configurations
ROO_CODE_CONFIG="$HOME/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcpSettings.json"
CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"

# Function to ask and update
update_config() {
	local path="$1"
	local type="$2"
	local name="$3"

	if [ -f "$path" ] || [ -d "$(dirname "$path")" ]; then
		echo -e "Found $name configuration at: $path"
		read -p "Do you want to add UnrealMCP to this config? (y/n) " -n 1 -r
		echo
		if [[ $REPLY =~ ^[Yy]$ ]]; then
			python "$CONFIG_UPDATER_SCRIPT" "$path" "$RUN_SCRIPT" "$type"
		fi
	fi
}

update_config "$ROO_CODE_CONFIG" "roo_code" "Roo Code (VS Code Extension)"
update_config "$CLAUDE_CONFIG" "claude" "Claude Desktop"

rm "$CONFIG_UPDATER_SCRIPT"

# Create .vscode/mcp.json in the project (Workspace-specific config)
VSCODE_DIR="$PROJECT_PATH/.vscode"
mkdir -p "$VSCODE_DIR"
MCP_JSON="$VSCODE_DIR/mcp.json"

if [ ! -f "$MCP_JSON" ]; then
	echo -e "${BLUE}Creating workspace MCP config at $MCP_JSON...${NC}"
	cat <<EOF >"$MCP_JSON"
{
    "mcpServers": {
        "unreal": {
            "command": "$RUN_SCRIPT",
            "args": []
        }
    }
}
EOF
else
	echo -e "${YELLOW}Workspace MCP config already exists at $MCP_JSON. Skipping overwrite.${NC}"
	echo "Ensure it contains the following configuration:"
	echo "\"unreal\": { \"command\": \"$RUN_SCRIPT\", \"args\": [] }"
fi

echo -e "${BLUE}=== Build Instructions ===${NC}"
echo "1. You need to regenerate project files."
if [ -f "$PROJECT_PATH/GenerateProjectFiles.sh" ]; then
	echo "   Found GenerateProjectFiles.sh in project root."
	read -p "   Do you want to run it now? (y/n) " -n 1 -r
	echo
	if [[ $REPLY =~ ^[Yy]$ ]]; then
		cd "$PROJECT_PATH"
		./GenerateProjectFiles.sh
	fi
else
	echo "   Run your engine's GenerateProjectFiles.sh or right-click .uproject -> Generate Project Files."
fi

echo "2. Build the project (e.g., run 'make' in the project root)."
echo "3. Open your project in Unreal Engine."
echo "4. Go to Edit > Plugins and enable 'UnrealMCP'."
echo "5. Also ensure 'Python Editor Script Plugin' is enabled."
echo "6. Restart the editor if prompted."

echo -e "${GREEN}Installation Complete!${NC}"
echo "If you need to manually configure an MCP client, use this command:"
echo -e "${YELLOW}$RUN_SCRIPT${NC}"
echo
echo "For VS Code (User Settings), add this to your settings.json:"
echo -e "${GREEN}"
cat <<EOF
"mcpServers": {
    "unreal": {
        "command": "$RUN_SCRIPT",
        "args": []
    }
}
EOF
echo -e "${NC}"
