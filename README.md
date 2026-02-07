# Omarchy OS Dotfiles

Personal configuration files for Omarchy OS (Arch Linux-based Hyprland distribution).

## Overview

These dotfiles contain customizations made from the default Omarchy OS configuration. Omarchy uses a system where defaults are sourced from `~/.local/share/omarchy/default/` and user customizations override them.

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

## Author

Created for personal use on Omarchy OS.

## License

Feel free to use and modify as needed.
