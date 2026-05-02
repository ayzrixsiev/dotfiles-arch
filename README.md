# Omarchy OS Dotfiles

Personal configuration files for Omarchy OS (Arch Linux-based Hyprland distribution).

## Overview

These dotfiles contain customizations made from the default Omarchy OS configuration. Omarchy uses a system where defaults are sourced from `~/.local/share/omarchy/default/` and user customizations override them.

## Contents

- **Waybar**: Custom top bar configuration with modules for workspaces, clock, weather, system info, and notifications.
- **Hyprland**: Window manager configurations including keybindings, monitor settings, idle management, and visual effects.
- **Starship**: Shell prompt customization for a clean and informative terminal experience.

## Screenshot

![Main Window](vibe.png)

*Representation of the lovely Waybar and wallpaper setup.*

## Installation

To apply these configurations to your system:

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/dotfiles-arch.git
   cd dotfiles-arch
   ```

2. Run the install script:
   ```bash
   ./install.sh
   ```

The script will copy the configuration files to their appropriate locations. You may need to restart Hyprland or reload configurations for changes to take effect.
