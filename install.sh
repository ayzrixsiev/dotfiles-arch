#!/bin/bash

# Install script for Omarchy OS dotfiles
# This script copies the configuration files to their appropriate locations

set -e

echo "Installing Omarchy OS dotfiles..."

# Copy .config files
if [ -d ".config" ]; then
    cp -r .config/* ~/.config/
    echo "Copied .config files"
fi

# Copy home files
if [ -d "home" ]; then
    cp -r home/* ~/
    echo "Copied home files"
fi

echo "Dotfiles installed successfully!"
echo "You may need to restart Hyprland or reload configurations for changes to take effect."