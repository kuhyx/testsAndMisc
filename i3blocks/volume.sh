
#!/bin/bash

# Get the current volume level and mute status
volume=$(pactl get-sink-volume @DEFAULT_SINK@ | awk '{print $5}' | tr -d '%')
mute=$(pactl get-sink-mute @DEFAULT_SINK@ | awk '{print $2}')

# Determine icon and color based on mute status
if [ "$mute" = "yes" ]; then
    icon="🔇"  # Muted
else
    icon="🔊"  # Volume icon
    color="#50FA7B"  # Green
fi

# Output the volume with icon and color
echo "$icon $volume%"
echo
echo $color

