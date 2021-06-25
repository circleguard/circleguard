
<img src="readme_resources/logo.png" alt="logo" width="200" height="200"/>

[![Latest Version](https://img.shields.io/github/release/circleguard/circleguard?label=Latest%20version)](https://github.com/circleguard/circleguard/releases/latest)
[![GitHub Releases Downloads](https://img.shields.io/github/downloads/circleguard/circleguard/total?label=Downloads)](https://github.com/circleguard/circleguard/releases/latest)
[![CodeFactor](https://www.codefactor.io/repository/github/circleguard/circleguard/badge)](https://www.codefactor.io/repository/github/circleguard/circleguard)
[![Discord Server](https://img.shields.io/discord/532476765860265984?label=Discord&logo=discord&logoColor=%23FFFFFF)](https://discord.gg/e84qxkQ)

# Circleguard

Circleguard is a tool to help you analyze osu! replays. Either your own, or replays from someone you suspect is cheating. Features:

* A replay viewer, with
  * A ur bar
  * Judgment indicators (green dots for 100s, blue dots for 50s, red dots for misses)
  * Ability to speed up and slow down playback speed
  * Ability to jump to any point in the replay
  * Frame by frame movement
* Cheat detection 
  * Similarity (for replay stealing)
  * Unstable rate (for relax)
  * Suspicious movements called snaps (for aim correction)
  * Frametime (for timewarp)
* Raw replay data (time, position, and keys pressed for each frame) in a nicely formatted table

If you're only interested in using circleguard to analyze your own replays, to (eg) figure out why you missed a note or to be able to quickly jump to any point in time in a replay, don't be scared off by the talk of cheat detection above. When you open circleguard, [simply click the "Visualization" panel](https://i.imgur.com/Gg9ohbP.png) to easily visualize one of your replays. Circleguard is fully fledged as a replay analysis tool as well as a cheat detection tool.

<img src="readme_resources/visualizer_demo.gif" alt="Demo gif of the visualizer" width="728" height="538"/><br/>
[*(click here to view a high quality version)*](https://streamable.com/9bkq8z)

<img src="readme_resources/demo.gif" alt="Demo gif of main gui" width="728" height="538"/><br/>
[*(click here to view a high quality version)*](https://streamable.com/0z0bw4)

Circleguard is developed and maintained by:

* [tybug](https://github.com/tybug)

With contributions from:

* [samuelhklumpers](https://github.com/samuelhklumpers)
* [InvisibleSymbol](https://github.com/InvisibleSymbol)

## Download

The latest version of circleguard can be found here: <https://github.com/circleguard/circleguard/releases/latest>. Download the appropriate binary for your OS (circleguard_win_x64.zip or circleguard_win_x86.zip for Windows, and circleguard_osx.app.zip for Mac OS). Circleguard was previously bundled as an exe for Windows but opened unbearably slowly, so it is distributed as a zip and you can run Circleguard.vbs (found inside the zip) in place of an exe.

If you are on another OS such as Linux, you will have to build circleguard yourself. See [Building From Source](#building-from-source).

There is an introduction / tutorial to using circleguard when you first open it. If you have any questions, feel free to ask on [the discord](https://discord.gg/VNnkTjm).

## Building From Source

The gui is bundled into a single program using [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/). You'll need to install pyinstaller, download the source code of this repository, and read the pyinstaller [documentation for your specific platform](https://pyinstaller.readthedocs.io/en/stable/requirements.html). You may find that further tweaking is required depending on your platform. If you run into trouble, I'll do my best to assist you if you ask in [the discord](https://discord.gg/VNnkTjm).

If you are building for windows or mac, there are premade specfiles in the root directory for easy building. Run `pyinstaller path-to-specfile` to generate an app for your platform as an alternative to using pyinstaller options. For instance, `pyinstaller gui_win_x64.spec` for 64-bit windows.

## Running Locally

To run circleguard locally, you'll need to have [git](https://git-scm.com/downloads) and [python3.9](https://www.python.org/downloads/) installed. After installing them, run the following:

```bash
git clone https://github.com/circleguard/circleguard.git
cd circleguard
pip install -r requirements.txt
python circleguard/main.py
# you might have to use python3 instead, eg python3 circleguard/main.py
```

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

## Credits

Thanks to [Accalix](https://twitter.com/Accalix_) for creating circleguard's logo. You can check out more of his work [here](https://accalix.art).
