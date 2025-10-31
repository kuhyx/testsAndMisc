#!/bin/bash
# Visual PC Startup Monitor Status Display
# Shows a nice visual representation of the monitoring status and schedule

# Color codes for visual display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Unicode symbols for visual elements
CHECK="✓"
CROSS="✗"
WARNING="⚠️"
CLOCK="🕐"
CALENDAR="📅"
COMPUTER="💻"
BELL="🔔"

# Function to draw a box around text
draw_box() {
    local text="$1"
    local width=${#text}
    local padding=2
    local total_width=$((width + padding * 2))
    
    # Top border
    printf "┌"
    printf "─%.0s" $(seq 1 $total_width)
    printf "┐\n"
    
    # Content with padding
    printf "│%*s%s%*s│\n" $padding "" "$text" $padding ""
    
    # Bottom border
    printf "└"
    printf "─%.0s" $(seq 1 $total_width)
    printf "┘\n"
}

# Function to show current day status
show_day_status() {
    local day_of_week=$(date +%u)
    local day_name=$(date +%A)
    local today=$(date +%Y-%m-%d)
    
    printf "${BLUE}${CALENDAR} Day Status${NC}\n"
    printf "═══════════════\n"
    
    # Show all days with status
    local days=("Monday" "Tuesday" "Wednesday" "Thursday" "Friday" "Saturday" "Sunday")
    local monitored=(1 0 0 0 1 1 1)  # 1=monitored, 0=not monitored
    
    for i in {0..6}; do
        local day_num=$((i + 1))
        if [[ $day_num -eq 7 ]]; then day_num=0; fi  # Sunday is 0 in some contexts
        
        if [[ ${monitored[$i]} -eq 1 ]]; then
            if [[ $day_of_week -eq $((i + 1)) ]] || [[ $day_of_week -eq 7 && $i -eq 6 ]]; then
                printf "${GREEN}${CHECK} ${days[$i]} (TODAY - MONITORED)${NC}\n"
            else
                printf "${CYAN}${CHECK} ${days[$i]} (monitored)${NC}\n"
            fi
        else
            if [[ $day_of_week -eq $((i + 1)) ]]; then
                printf "${GRAY}○ ${days[$i]} (TODAY - not monitored)${NC}\n"
            else
                printf "${GRAY}○ ${days[$i]}${NC}\n"
            fi
        fi
    done
    
    printf "\n"
}

# Function to show time window status
show_time_status() {
    local current_hour=$(date +%H)
    local current_minute=$(date +%M)
    local current_hour_num=$((10#$current_hour))
    
    printf "${YELLOW}${CLOCK} Time Window Status${NC}\n"
    printf "═══════════════════════\n"
    
    # Show 24-hour timeline with window highlighted
    printf "Timeline (24-hour format):\n"
    printf "00 01 02 03 04 "
    printf "${GREEN}05 06 07${NC} "
    printf "08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23\n"
    printf "               "
    printf "${GREEN}▲─────▲${NC}\n"
    printf "               "
    printf "${GREEN}Expected Window${NC}\n"
    
    # Current time indicator
    printf "\nCurrent time: ${WHITE}%02d:%s${NC}\n" $current_hour_num "$current_minute"
    
    if [[ $current_hour_num -ge 5 && $current_hour_num -lt 8 ]]; then
        printf "Status: ${GREEN}${CHECK} Within expected window (5AM-8AM)${NC}\n"
    else
        printf "Status: ${YELLOW}○ Outside expected window${NC}\n"
    fi
    
    printf "\n"
}

# Function to show boot time analysis
show_boot_analysis() {
    printf "${PURPLE}${COMPUTER} Boot Time Analysis${NC}\n"
    printf "═══════════════════════\n"
    
    # Get boot time
    local uptime_seconds=$(awk '{print int($1)}' /proc/uptime 2>/dev/null || echo "0")
    local boot_time=$(date -d "@$(($(date +%s) - uptime_seconds))" +"%Y-%m-%d %H:%M:%S")
    local boot_date=$(echo "$boot_time" | cut -d' ' -f1)
    local boot_time_only=$(echo "$boot_time" | cut -d' ' -f2)
    local boot_hour=$(echo "$boot_time_only" | cut -d':' -f1)
    local boot_hour_num=$((10#$boot_hour))
    local today=$(date +%Y-%m-%d)
    
    printf "System boot time: ${WHITE}$boot_time${NC}\n"
    
    if [[ "$boot_date" == "$today" ]]; then
        printf "Boot date: ${GREEN}${CHECK} Today${NC}\n"
        
        if [[ $boot_hour_num -ge 5 && $boot_hour_num -lt 8 ]]; then
            printf "Boot window: ${GREEN}${CHECK} Within expected window (5AM-8AM)${NC}\n"
            printf "Status: ${GREEN}${CHECK} COMPLIANT${NC}\n"
        else
            printf "Boot window: ${RED}${CROSS} Outside expected window${NC}\n"
            printf "Status: ${RED}${WARNING} NON-COMPLIANT${NC}\n"
        fi
    else
        printf "Boot date: ${YELLOW}○ Not today ($boot_date)${NC}\n"
        printf "Status: ${YELLOW}○ System was not booted today${NC}\n"
    fi
    
    printf "\n"
}

# Function to show monitoring system status
show_system_status() {
    printf "${CYAN}${BELL} Monitoring System${NC}\n"
    printf "═══════════════════════\n"
    
    # Check if timer exists and is enabled
    if systemctl is-enabled pc-startup-monitor.timer &>/dev/null; then
        printf "Service: ${GREEN}${CHECK} ENABLED${NC}\n"
        
        if systemctl is-active pc-startup-monitor.timer &>/dev/null; then
            printf "Timer: ${GREEN}${CHECK} ACTIVE${NC}\n"
        else
            printf "Timer: ${RED}${CROSS} INACTIVE${NC}\n"
        fi
        
        # Show next check time
        local next_check=$(systemctl list-timers pc-startup-monitor.timer --no-pager 2>/dev/null | grep pc-startup-monitor | awk '{print $1, $2, $3}' || echo "Not scheduled")
        printf "Next check: ${WHITE}$next_check${NC}\n"
        
    else
        printf "Service: ${RED}${CROSS} NOT ENABLED${NC}\n"
        printf "Timer: ${RED}${CROSS} NOT ACTIVE${NC}\n"
    fi
    
    printf "\n"
}

# Function to show overall compliance status
show_compliance_overview() {
    local day_of_week=$(date +%u)
    local current_hour=$(date +%H)
    local current_hour_num=$((10#$current_hour))
    
    # Check if today is monitored
    local is_monitored=false
    if [[ "$day_of_week" == "1" ]] || [[ "$day_of_week" == "5" ]] || [[ "$day_of_week" == "6" ]] || [[ "$day_of_week" == "7" ]]; then
        is_monitored=true
    fi
    
    printf "${WHITE}"
    draw_box "COMPLIANCE OVERVIEW"
    printf "${NC}\n"
    
    if [[ "$is_monitored" == true ]]; then
        printf "Today: ${GREEN}${CHECK} Monitored day${NC}\n"
        
        # Check current compliance
        if [[ $current_hour_num -ge 5 && $current_hour_num -lt 8 ]]; then
            printf "Current status: ${GREEN}${CHECK} PC is on during expected window${NC}\n"
            printf "Action needed: ${GREEN}None - currently compliant${NC}\n"
        else
            # Check if booted in window
            local uptime_seconds=$(awk '{print int($1)}' /proc/uptime 2>/dev/null || echo "0")
            local boot_time=$(date -d "@$(($(date +%s) - uptime_seconds))" +"%Y-%m-%d %H:%M:%S")
            local boot_date=$(echo "$boot_time" | cut -d' ' -f1)
            local boot_hour=$(echo "$boot_time" | cut -d' ' -f2 | cut -d':' -f1)
            local boot_hour_num=$((10#$boot_hour))
            local today=$(date +%Y-%m-%d)
            
            if [[ "$boot_date" == "$today" ]] && [[ $boot_hour_num -ge 5 && $boot_hour_num -lt 8 ]]; then
                printf "Current status: ${GREEN}${CHECK} PC was booted in expected window${NC}\n"
                printf "Action needed: ${GREEN}None - compliant${NC}\n"
            else
                printf "Current status: ${RED}${WARNING} PC was NOT booted in expected window${NC}\n"
                printf "Action needed: ${YELLOW}Warning will be shown at 8:30 AM${NC}\n"
            fi
        fi
    else
        printf "Today: ${GRAY}○ Not a monitored day${NC}\n"
        printf "Current status: ${GRAY}No monitoring required${NC}\n"
        printf "Action needed: ${GRAY}None${NC}\n"
    fi
    
    printf "\n"
}

# Function to show recent activity
show_recent_activity() {
    printf "${GRAY}📋 Recent Activity${NC}\n"
    printf "════════════════\n"
    
    # Show last 5 log entries
    local logs=$(journalctl -t pc-startup-monitor --no-pager -n 5 --output=short 2>/dev/null || echo "No logs found")
    
    if [[ "$logs" == "No logs found" ]]; then
        printf "${GRAY}No recent monitoring activity${NC}\n"
    else
        echo "$logs" | while IFS= read -r line; do
            if [[ $line == *"WARNING"* ]]; then
                printf "${RED}$line${NC}\n"
            elif [[ $line == *"compliance OK"* ]]; then
                printf "${GREEN}$line${NC}\n"
            else
                printf "${GRAY}$line${NC}\n"
            fi
        done
    fi
    
    printf "\n"
}

# Main display function
main() {
    clear
    
    # Header
    printf "${BLUE}"
    draw_box "PC STARTUP MONITOR - VISUAL STATUS"
    printf "${NC}\n\n"
    
    printf "${WHITE}Current Date/Time: $(date)${NC}\n"
    printf "${WHITE}System Uptime: $(uptime -p)${NC}\n\n"
    
    # Show all status sections
    show_day_status
    show_time_status
    show_boot_analysis
    show_system_status
    show_compliance_overview
    show_recent_activity
    
    # Footer with commands
    printf "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
    printf "${WHITE}Commands:${NC}\n"
    printf "  ${CYAN}sudo pc-startup-monitor-manager.sh status${NC}  - Show system status\n"
    printf "  ${CYAN}sudo pc-startup-monitor-manager.sh test${NC}    - Test monitor now\n"
    printf "  ${CYAN}sudo pc-startup-monitor-manager.sh logs${NC}    - View detailed logs\n"
    printf "  ${CYAN}$0${NC}                                      - Show this visual status\n"
    printf "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

# Run main function
main "$@"
