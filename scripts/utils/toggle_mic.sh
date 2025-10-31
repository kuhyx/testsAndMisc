#!/bin/bash

# Check if amixer is installed, if not, install it
if ! command -v amixer &> /dev/null; then
    echo "amixer could not be found, installing..."
    sudo pacman -S --noconfirm alsa-utils
fi

# Ensure dbus is running
if ! pgrep -x "dbus-daemon" > /dev/null; then
    echo "Starting dbus..."
    sudo systemctl start dbus
fi

# Ensure dbus is properly initialized for the user session
export $(dbus-launch)

# Ensure notification-daemon is installed
if ! pacman -Qs notification-daemon > /dev/null; then
    echo "Installing notification-daemon..."
    sudo pacman -S --noconfirm notification-daemon
fi

# Ensure dunst is installed and running
if ! pacman -Qs dunst > /dev/null; then
    echo "Installing dunst..."
    sudo pacman -S --noconfirm dunst
fi

if ! pgrep -x "dunst" > /dev/null; then
    echo "Starting dunst..."
    dunst &
fi

# Get the current state of the microphone
MIC_STATE=$(amixer get Capture | grep '\[on\]')

if [ -z "$MIC_STATE" ]; then
    # If the microphone is off, turn it on
    amixer set Capture cap
    sleep 1  # Add a delay to ensure notify-send works correctly
    notify-send "Microphone" "Microphone is now ON"
else
    # If the microphone is on, turn it off
    amixer set Capture nocap
    sleep 1  # Add a delay to ensure notify-send works correctly
    notify-send "Microphone" "Microphone is now OFF"
fi
