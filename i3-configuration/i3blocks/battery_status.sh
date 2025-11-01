#!/bin/bash

acpi -b | awk -F', ' '
    /Battery/ {
        split($2, percent, "%")
        split($3, time, " ")
        printf "  %d%%", percent[1]
        if (time[1] != "") printf ", %s", time[1]
        if ($1 ~ /Charging/) printf ", "
        printf "\n"
    }'
