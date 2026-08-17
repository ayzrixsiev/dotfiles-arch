#!/bin/bash

# Install script for Omarchy OS dotfiles
# This script copies the configuration files to their appropriate locations

set -e

echo "Installing Omarchy OS dotfiles..."

# Copy .config files
if [ -d ".config" ]; then
    mkdir -p ~/.config
    cp -a .config/. ~/.config/
    echo "Copied .config files"
fi

# Copy home files. Uses "home/." rather than "home/*" so dotfiles and the
# .local tree (which carries the Do task manager) come along too.
if [ -d "home" ]; then
    cp -a home/. ~/
    chmod +x ~/.local/bin/do
    echo "Copied home files"
fi

# Do (task popup) needs GTK4 + the layer-shell binding to draw itself as an
# overlay. Warn rather than install, since that needs sudo.
missing=()
for pkg in gtk4 gtk4-layer-shell python-gobject; do
    pacman -Q "$pkg" &>/dev/null || missing+=("$pkg")
done
if [ ${#missing[@]} -gt 0 ]; then
    echo
    echo "Do (Super + D) needs these packages: ${missing[*]}"
    echo "  sudo pacman -S --needed ${missing[*]}"
fi

echo
echo "Dotfiles installed successfully!"
echo "You may need to restart Hyprland or reload configurations for changes to take effect."
