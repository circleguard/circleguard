
<img src="readme_resources/logo.png" alt="Gif Demo" width="200" height="200"/>

[![Latest Version](https://img.shields.io/github/release/circleguard/circleguard?label=Latest%20version)](https://circleguard.dev/download)
[![GitHub Releases Downloads](https://img.shields.io/github/downloads/circleguard/circleguard/total?label=Downloads)](https://circleguard.dev/download)
[![CodeFactor](https://www.codefactor.io/repository/github/circleguard/circleguard/badge)](https://www.codefactor.io/repository/github/circleguard/circleguard)
[![Discord Server](https://img.shields.io/discord/532476765860265984?label=Discord&logo=discord&logoColor=%23FFFFFF)](https://discord.gg/e84qxkQ)

# Circleguard

Circleguard is a tool to help you catch cheaters. Features include:

* An all-purpose replay viewer to look at any replay indepth
* Replay Stealing / Remodding detection
* Unstable Rate (ur) calculation, for relax cheats
* Finding suspicious movements in replays (called Snaps), for aim correction cheats
* Frametime analysis, for timewarp cheats
* viewing the raw replay data (time, position, and keys pressed for each frame) in a formatted table, for very fine-grained analysis

Our replay viewer supports seeking to any timestamp in the replay, slowing down or speeding up time, frame-by-frame movement, and more.

<img src="readme_resources/demo.gif" alt="Gif Demo" width="728" height="538"/>

Circleguard is developed and maintained by:

* [tybug](https://github.com/tybug)
* [samuelhklumpers](https://github.com/samuelhklumpers)
* [InvisibleSymbol](https://github.com/InvisibleSymbol)

With contributions from:

* Watch The Circles

## Download

The latest version of circleguard can be found here: <https://github.com/circleguard/circleguard/releases/latest>. Download the appropriate binary for your OS - circleguard_win_x64.zip or circleguard_win_x86.zip for Windows, and circleguard_osx.app.zip for Mac OS. Circleguard was previously bundled as an exe for Windows but opened unbearably slowly, so we distribute it as a zip and you can run Circleguard.lnk (found inside the zip) in place of an exe. If you are on another OS such as Linux, you will have to build the app yourself. See [Building From Source](#building-from-source).

If you don't trust the downloaded binary, you are more than welcome to build from source yourself. You can validate that the code never sends your api key anywhere by looking at the code in the circleguard and circlecore repositories.

There is a short introduction to the program when you first open it. Everything should be relatively self-explanatory, and if you have any questions, feel free to ask on [our discord](https://discord.gg/VNnkTjm).

## Building From Source

The gui is bundled into a single program using [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/). You will need to download the source code of this repository and read the pyinstaller [documentation for your specific platform](https://pyinstaller.readthedocs.io/en/stable/requirements.html) - the OS may not be supported, or you may need to install some package for it to work. Run pyinstaller on main.py with the --one-file option to generate an executable. You may find that further tweaking is required depending on your platform - I'm afraid that our journey together ends there, and you must forge ahead on your own. We will do our best to assist you if you ask us in our discord.

If you are building for windows or mac, we provide premade specfiles for easy building. You can run `pyinstaller path-to-specfile` to generate an app for your platform as an alternative to using pyinstaller options.

## Contributing

Join [our discord](https://discord.gg/VNnkTjm) and ask how you can help, or look around for open issues which interest you and tackle those. We welcome PR requests!

## Links

* Discord: <https://discord.gg/VNnkTjm>
* Circlecore: <https://github.com/circleguard/circlecore>

## Credits

Thanks to [kszlim](https://github.com/kszlim), whose [replay parser](https://github.com/kszlim/osu-replay-parser) formed the basis of [circleparse](https://github.com/circleguard/osu-replay-parser).

Thanks to [Accalix](https://twitter.com/Accalix_) for creating our logo. You can check out more of his work [here](https://accalixgfx.com/index.php).
