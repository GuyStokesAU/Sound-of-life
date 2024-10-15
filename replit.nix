{ pkgs ? import <nixpkgs> {} }:

{
  deps = [
    pkgs.python311Full        # Ensures Python 3.11 is installed
    pkgs.portaudio            # PortAudio library required by pyo
    pkgs.alsaLib              # ALSA sound library for Linux systems
    pkgs.ffmpeg               # FFmpeg for audio processing and exporting
    pkgs.gcc                  # GNU Compiler Collection for compiling C extensions
    pkgs.gnumake              # GNU Make tool required for compiling some packages
    pkgs.pkg-config           # Package configuration helper
    pkgs.git                  # Git for version control (optional)
    # Add any other dependencies you might need
  ];
}
