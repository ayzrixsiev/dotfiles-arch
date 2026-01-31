# Omarchy OS Dotfiles

Personal configuration files for Omarchy OS (Arch Linux-based Hyprland distribution).

## Overview

These dotfiles contain customizations made from the default Omarchy OS configuration. Omarchy uses a system where defaults are sourced from `~/.local/share/omarchy/default/` and user customizations override them.

## System Information

- **OS**: Omarchy OS (Arch Linux)
- **Kernel**: 6.18.6-arch1-1
- **Window Manager**: Hyprland
- **Bar**: Waybar
- **Shell**: Bash with Starship prompt

## Changes from Default Configuration

### Hyprland (`~/.config/hypr/`)

#### `hyprland.conf`
- Added NVIDIA environment variables:
  - `NVD_BACKEND=direct`
  - `LIBVA_DRIVER_NAME=nvidia`
  - `__GLX_VENDOR_LIBRARY_NAME=nvidia`

#### `input.conf`
**Keyboard:**
- Changed keyboard layout from `us` to `us, ru` (US + Russian)
- Added keyboard layout switching with `Alt+Shift`
- Set `kb_options = compose:caps, grp:alt_shift_toggle`
- Modified keyboard repeat: `repeat_rate = 40`, `repeat_delay = 600`
- Enabled `numlock_by_default = true`

**Touchpad:**
- Changed `natural_scroll = false` to `true` (inverse scrolling)
- Set `scroll_factor = 0.4`
- Added custom scroll speeds for terminals:
  - Alacritty/kitty: `scroll_touchpad 1.5`
  - Ghostty: `scroll_touchpad 0.2`

#### `monitors.conf`
- Configured for 1920x1080@144Hz display
- Set scaling: `monitor=eDP-1,1920x1080@144,auto,1.2`
- Environment: `GDK_SCALE=2` (for retina-class displays)

#### `hypridle.conf`
- Screen lock timeout: 15 minutes (900s)
- Screen off timeout: 16 minutes (1080s)
- Uses `omarchy-lock-screen` for locking

#### `hyprlock.conf`
- Custom lock screen configuration with:
  - Background blur and effects
  - Centered input field with rounded corners
  - Clock and date display
  - Authentication field styling
  - Fingerprint authentication enabled

### Waybar (`~/.config/waybar/`)

#### `config.jsonc`
- **Weather widget**: Customized location to "Delhi"
  ```json
  "exec": "wttrbar --nerd --location Delhi"
  ```
- **Persistent workspaces**: Set to 5 workspaces on main display
- **Modules layout**: Clock, weather, workspaces on left; system info on right
- All default Omarchy modules retained (CPU, audio, network, battery, Bluetooth, notifications)

#### `style.css`
- Uses theme from `~/.config/omarchy/current/theme/waybar.css`
- Custom styling for all waybar modules
- Font: JetBrainsMono Nerd Font (12px, bold)
- Custom colors and spacing for workspaces, tray, and system indicators

### Shell Configuration

#### `.bashrc` (home directory)
- Sources Omarchy defaults: `source ~/.local/share/omarchy/default/bash/rc`
- Minimal customization (uses Omarchy's default aliases and functions)

#### `starship.toml` (`~/.config/`)
- Custom prompt configuration:
  - Cyan color scheme for all elements
  - Simplified format: `[$directory$git_branch$git_status]($style)$character`
  - Directory truncation: 2 levels
  - Git status indicators customized
  - Success symbol: `❯` (cyan)
  - Error symbol: `✗` (cyan)

## Installation

### Structure
```
dotfiles/
├── .config/
│   ├── hypr/
│   │   ├── hyprland.conf
│   │   ├── input.conf
│   │   ├── monitors.conf
│   │   ├── hypridle.conf
│   │   └── hyprlock.conf
│   └── waybar/
│       ├── config.jsonc
│       └── style.css
├── home/
│   ├── .bashrc
│   └── starship.toml
└── README.md
```

### How to Apply

1. **Backup existing configs:**
   ```bash
   cp -r ~/.config/hypr ~/.config/hypr.backup
   cp -r ~/.config/waybar ~/.config/waybar.backup
   cp ~/.bashrc ~/.bashrc.backup
   cp ~/.config/starship.toml ~/.config/starship.toml.backup
   ```

2. **Copy Hyprland configs:**
   ```bash
   cp dotfiles/.config/hypr/* ~/.config/hypr/
   ```

3. **Copy Waybar configs:**
   ```bash
   cp dotfiles/.config/waybar/* ~/.config/waybar/
   ```

4. **Copy shell configs:**
   ```bash
   cp dotfiles/home/.bashrc ~/
   cp dotfiles/home/starship.toml ~/.config/
   ```

5. **Reload configurations:**
   ```bash
   # Reload Hyprland
   hyprctl reload
   
   # Restart Waybar
   killall waybar && waybar &
   
   # Reload shell
   source ~/.bashrc
   ```

## Notes

- These configs are designed for Omarchy OS and depend on Omarchy-specific scripts and theming
- The Hyprland config sources from `~/.local/share/omarchy/default/` for base configuration
- Theme files are located in `~/.config/omarchy/current/theme/`
- Monitor configuration (`monitors.conf`) should be adjusted for your specific display setup
- NVIDIA variables in `hyprland.conf` are GPU-specific and may need removal on non-NVIDIA systems

## Dependencies

These configs assume the following are installed (standard on Omarchy OS):
- Hyprland
- Waybar
- Starship
- JetBrainsMono Nerd Font
- wttrbar (weather widget)
- Various Omarchy-specific tools (`omarchy-*` commands)

## Key Customizations Summary

1. **Dual keyboard layout** (US/Russian) with Alt+Shift switching
2. **Natural scrolling** enabled for touchpad
3. **Custom monitor scaling** for 1080p@144Hz display
4. **Weather location** set to Delhi
5. **NVIDIA GPU optimizations**
6. **Cyan-themed Starship prompt**
7. **Custom lock screen** with fingerprint auth

## Author

Created for personal use on Omarchy OS.

## License

Feel free to use and modify as needed.
