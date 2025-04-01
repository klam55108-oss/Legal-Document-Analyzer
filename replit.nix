{pkgs}: {
  deps = [
    pkgs.python3
    pkgs.wkhtmltopdf
    pkgs.tk
    pkgs.tcl
    pkgs.qhull
    pkgs.pkg-config
    pkgs.gtk3
    pkgs.gobject-introspection
    pkgs.ghostscript
    pkgs.freetype
    pkgs.ffmpeg-full
    pkgs.cairo
    pkgs.glibcLocales
    pkgs.arrow-cpp
    pkgs.postgresql
    pkgs.openssl
  ];
}
