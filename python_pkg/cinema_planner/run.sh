#!/bin/bash
# Run cinema planner with Cinema City schedule from Downloads

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
DOWNLOADS="$HOME/Downloads"

# Show help if requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Automatically finds Cinema City HTML schedule in ~/Downloads"
    echo ""
    echo "Options:"
    echo "  -l, --list          List all movies without scheduling"
    echo "  -x, --exclude       Exclude movies by name (comma-separated)"
    echo "  -g, --exclude-genre Exclude additional genres (comma-separated)"
    echo "  --all-genres        Include all genres (disable Horror auto-exclusion)"
    echo "  -b, --buffer N      Buffer time between movies (default: 0)"
    echo "  -m, --must-watch    Only show schedules containing this movie"
    echo "  -n, --max-schedules Max number of schedule options to show (default: 5)"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                           # Plan optimal schedule"
    echo "  ./run.sh -x 'Avatar,Sonic'         # Exclude specific movies"
    echo "  ./run.sh -g 'Thriller,Dramat'      # Also exclude Thriller and Drama"
    echo "  ./run.sh --all-genres              # Include Horror movies"
    echo "  ./run.sh -m 'Hamnet'               # Only schedules with Hamnet"
    exit 0
fi

# Find the most recent Cinema City HTML file
HTML_FILE=$(find "$DOWNLOADS" -maxdepth 1 -name "Repertuar*.html" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

if [ -z "$HTML_FILE" ]; then
    echo "No Cinema City schedule found in $DOWNLOADS"
    echo "Download the schedule from cinema-city.pl first"
    exit 1
fi

echo "Using: $HTML_FILE"
echo ""

# Run the planner with any additional arguments passed to this script
"$SCRIPT_DIR/cinema_planner.py" "$HTML_FILE" "$@"
