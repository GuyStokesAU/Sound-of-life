{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python310Full        # Python 3.10
    pkgs.portaudio            # PortAudio library required by pyo
    pkgs.alsaLib              # ALSA sound library for Linux systems
    pkgs.ffmpeg               # FFmpeg for audio processing and exporting
    pkgs.gcc                  # GNU Compiler Collection for compiling C extensions
    pkgs.gnumake              # GNU Make tool required for compiling some packages
    pkgs.pkg-config           # Package configuration helper
    pkgs.git                  # Git for version control (optional)
    pkgs.libsndfile           # Library for reading and writing sound files
    pkgs.qt5.qtbase           # Qt5 base libraries required by PyQt5
    pkgs.qt5.qttools          # Qt5 tools required by PyQt5
    # Add any other dependencies you might need
  ];

  shellHook = ''
    echo "Entering the Nix shell environment for the Sound-of-life project"
    # You can add any setup commands here
  '';
}
