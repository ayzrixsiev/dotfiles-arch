# If not running interactively, don't do anything (leave this at the top of this file)
[[ $- != *i* ]] && return

# All the default Omarchy aliases and functions
# (don't mess with these directly, just overwrite them here!)
source ~/.local/share/omarchy/default/bash/rc

# =============================================================================
# SYSTEM & GENERAL TOOLS
# =============================================================================


# =============================================================================
# GO DEVELOPMENT
# =============================================================================

# Golang
export GOPATH=$HOME/Development/go

# Go's compiled binary directory path, so that we can use toold installed via "go install"
export PATH=$PATH:$GOPATH/bin


# =============================================================================
# FLUTTER & MOBILE DEVELOPMENT
# =============================================================================

# Flutter
export PATH="$HOME/Development/flutter/bin:$PATH"

# Java/OpenJDK
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk"
export PATH="$JAVA_HOME/bin:$PATH"

# Android, to compile flutter for android phones
export ANDROID_HOME="$HOME/Development/Android/Sdk"
export PATH="$PATH:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/tools/bin"

# Chrome Executable: Tells Flutter Web to target Chromium
export CHROME_EXECUTABLE="/usr/bin/chromium"
