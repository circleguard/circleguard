from pathlib import Path
import os
import sys
from circleguard import Circleguard, set_options, ReplayPath, ReplayMap, Check

ROOT_PATH = Path(__file__).parent
if(not (ROOT_PATH / "secret.py").is_file()):
    key = input("Please enter your api key below - you can get it from https://osu.ppy.sh/p/api. "
                "This will only ever be stored locally, and is necessary to retrieve replay data.\n")
    with open(ROOT_PATH / "secret.py", mode="x") as secret:
        secret.write("API_KEY = '{}'".format(key))
from secret import API_KEY
from argparser import argparser

# set_options(cache=True)
set_options(failfast=False)
args = argparser.parse_args()
circleguard = Circleguard(API_KEY, ROOT_PATH / "replays", ROOT_PATH / "db" / "cache.db")
# replays = [ReplayPath("/Users/tybug/Desktop/Coding/osu/circleguard/circleguard/replays/woey.osr"), ReplayPath("/Users/tybug/Desktop/Coding/osu/circleguard/circleguard/replays/cheater.osr")]
# check = Check(replays)
# circleguard.run(check)
iterator = circleguard.map_check(221777, u=12092800, num=3)
# iterator = circleguard.local_check()
for result in iterator:
    print(result.similiarity)
# circleguard.verify(1699366, 12092800, 7477458, False)


# Check objects should be able to be instantiated with an arbitrary mix of ReplayPath and ReplayMap and maybe other, client implemented, objects
# usage on the client end: circleguard.run(check)
# circleguard.verify() etc are just shortcuts for making Check objects with the relevant ReplayMap and (if applicable) ReplayPath objects
