# Circleguard

Circleguard is a player made and maintained cheat detection tool. It currently focuses heavily on detecting replay stealing and remodding, but can be used as an all purpose replay viewer.

Circleguard is the frontend gui, which runs circlecore behind the scenes. If you're looking to integrate circlecore into your own project, extensive documentation on the internals can be found at its repo [here](https://github.com/circleguard/circlecore). It is available as a pip module.

Circleguard is developed and maintained by:

* tybug
* samuelhklumpers
* Invisible_Symbol

With contributions from:

* Watch The Circles

## Download

The latest binaries can be found here: <https://github.com/circleguard/circleguard/releases/latest>. Download the appropriate binary for your os - circleguard.exe for windows, and circleguard.app for osx. If you are on aother os such as linux, you will have to build the app yourself. See Building From Source.

If you don't trust the downloaded binary, feel more than welcome to build from source yourself. You can validate that the code never sends your api key anywhere by looking at the code in the circleguard and circlecore repos.

There is a short introduction of the program when you first open it. Everything should be relatively self explenatory, and if you have any questions, feel free to ask on [our discord](https://discord.gg/VNnkTjm).

## Building From Source

The gui is bundled into a single program using [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/). Read the pyinstaller [documentation for your specific platform](https://pyinstaller.readthedocs.io/en/stable/requirements.html) - it may not be supported, or you may need to install a package for it to work. Run pyinstaller on gui.py with the --one-file option to generate an executable. You may find that further tweaking is required depending on your platform - I'm afraid that our journey together ends there, and you must forge ahead on your own. We will do our best to asist you if you ask us in our discord.

## Links

* Discord: <https://discord.gg/VNnkTjm>
* Circlecore: <https://github.com/circleguard/circlecore>

## Credits

Thanks to [kszlim](https://github.com/kszlim), whose [replay parser](https://github.com/kszlim/osu-replay-parser) formed the basis of [circleparse](https://github.com/circleguard/osu-replay-parser).

Thanks to [Accalix](https://twitter.com/Accalix_) for creating our logo. You can check out more of his work [here](https://accalixgfx.com/index.php).
