
<img src="readme_resources/logo.png" alt="logo" width="200" height="200"/>

[![Latest Version](https://img.shields.io/github/release/circleguard/circleguard?label=Latest%20version)](https://github.com/circleguard/circleguard/releases/latest)
[![GitHub Releases Downloads](https://img.shields.io/github/downloads/circleguard/circleguard/total?label=Downloads)](https://github.com/circleguard/circleguard/releases/latest)
[![CodeFactor](https://www.codefactor.io/repository/github/circleguard/circleguard/badge)](https://www.codefactor.io/repository/github/circleguard/circleguard)
[![Discord Server](https://img.shields.io/discord/532476765860265984?label=Discord&logo=discord&logoColor=%23FFFFFF)](https://discord.gg/e84qxkQ)

# Circleguard

Circleguard is a tool to help you catch cheaters. Features include:

* An replay viewer to look at any replay in depth
* Replay stealing / remodding detection
* Unstable Rate (ur) calculation, for relax cheats
* Finding suspicious movements in replays (called Snaps), for aim correction cheats
* Frametime analysis, for timewarp cheats
* Viewing the raw replay data (time, position, and keys pressed for each frame) in a formatted table, for very fine-grained analysis

The replay viewer supports seeking to any timestamp in the replay, slowing down or speeding up time, frame-by-frame movement, and more.

<img src="readme_resources/visualizer_demo.gif" alt="Demo gif of the visualizer" width="728" height="538"/><br/>
[*(click here to view a high quality version)*](https://streamable.com/9bkq8z)

<img src="readme_resources/demo.gif" alt="Demo gif of main gui" width="728" height="538"/><br/>
[*(click here to view a high quality version)*](https://streamable.com/0z0bw4)

Circleguard is developed and maintained by:

* [tybug](https://github.com/tybug)
* [samuelhklumpers](https://github.com/samuelhklumpers)

With contributions from:

* [InvisibleSymbol](https://github.com/InvisibleSymbol)

## Download

The latest version of circleguard can be found here: <https://github.com/circleguard/circleguard/releases/latest>. Download the appropriate binary for your OS (circleguard_win_x64.zip or circleguard_win_x86.zip for Windows, and circleguard_osx.app.zip for Mac OS). Circleguard was previously bundled as an exe for Windows but opened unbearably slowly, so it is distributed as a zip and you can run Circleguard.vbs (found inside the zip) in place of an exe.

If you are on another OS such as Linux, you will have to build circleguard yourself. See [Building From Source](#building-from-source).

There is an introduction / tutorial to using circleguard when you first open it. If you have any questions, feel free to ask on [the discord](https://discord.gg/VNnkTjm).

## Building From Source

The gui is bundled into a single program using [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/). You will need to download the source code of this repository and read the pyinstaller [documentation for your specific platform](https://pyinstaller.readthedocs.io/en/stable/requirements.html). You may find that further tweaking is required depending on your platform. If you run into trouble, I'll do my best to assist you if you ask in [the discord](https://discord.gg/VNnkTjm).

If you are building for windows or mac, we provide premade specfiles for easy building. Run `pyinstaller path-to-specfile` to generate an app for your platform as an alternative to using pyinstaller options.

## Contributing

Join [our discord](https://discord.gg/VNnkTjm) and ask how you can help, or look around for open issues which interest you and tackle those. Pull requests are welcome!

## Links

Discord: <https://discord.gg/VNnkTjm>

### Circlecore

Circlecore does most of the heavy lifting for circleguard, such as calculating ur, similarity, frametimes, etc. If you would like to use circlecore in your own project, please see the developer guidance over at its repository:

<https://github.com/circleguard/circlecore>

### Circlevis

The replay viewer is powerful enough that it was split off into its own repository. If you would like to use the replay viewer in your own project, please see the developer guidance over at its repository:

<https://github.com/circleguard/circlevis>

Note that the replay viewer is a [Qt](https://doc.qt.io/) widget, and will only work if you are using the Qt (or [pyqt](https://pypi.org/project/PyQt5/), as we are) GUI framwork.

## Credits

Thanks to [Accalix](https://twitter.com/Accalix_) for creating circleguard's logo. You can check out more of his work [here](https://accalix.art).
