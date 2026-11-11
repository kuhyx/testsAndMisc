"""Rotate the i3 desktop background among six dark, text-free styles.

A systemd timer ticks every 15 minutes. Every three hours each monitor gets a
random style different from its previous one and from the other monitor's;
between rotations the data-driven styles (shutdown clock, habit heatmap,
Earth day/night) redraw so they stay current.
"""
