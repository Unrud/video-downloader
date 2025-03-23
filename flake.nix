{
  description = "Unrud/video-downloader app";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      allSystems = [
        "x86_64-linux"
        #"aarch64-linux"
        #"x86_64-darwin"
        #"aarch64-darwin"
      ];

      forAllSystems = f: nixpkgs.lib.genAttrs allSystems (system: f  {
        pkgs = import nixpkgs { inherit system; };
      });

      system = "x86_64-linux";

      python =
        with import nixpkgs { inherit system; };
        python3.withPackages (ps : with ps; [ pygobject3 yt-dlp ]);

    in
    {
      packages = forAllSystems ({ pkgs }: {

        default = pkgs.stdenv.mkDerivation rec {        
          name = "video-downloader";
          src = self;

          nativeBuildInputs = with pkgs; [
            desktop-file-utils
            appstream-glib
            meson
            ninja
            pkg-config
            python3
            wrapGAppsHook4
          ];

          buildInputs = with pkgs; [
            gtk4
            libadwaita
            haskellPackages.gi-gdk
            haskellPackages.gi-gtk
            yt-dlp
            ffmpeg
          ];

          preFixup = ''
            wrapProgram $out/bin/$pname/video-downloader \
              --prefix PYTHONPATH : ${python}/${python.sitePackages} \
          '';

        };
      });
    };
}
