from pathlib import Path
import os
import sys
from circleguard import Circleguard, set_options, ReplayPath, ReplayMap, Check, Replay

ROOT_PATH = Path(__file__).parent
if(not (ROOT_PATH / "secret.py").is_file()):
    key = input("Please enter your api key below - you can get it from https://osu.ppy.sh/p/api. "
                "This will only ever be stored locally, and is necessary to retrieve replay data.\n")
    with open(ROOT_PATH / "secret.py", mode="x") as secret:
        secret.write("API_KEY = '{}'".format(key))
from secret import API_KEY
from argparser import argparser


class IdentifiableReplay(ReplayPath):

    def __init__(self, id, path):
        self.id = id
        ReplayPath.__init__(self, path)


# set_options(cache=True)
set_options(failfast=False)
args = argparser.parse_args()
circleguard = Circleguard(API_KEY, ROOT_PATH / "db" / "cache.db")
replays = [IdentifiableReplay(1, ROOT_PATH / "replays" / "woey.osr"), IdentifiableReplay(2, ROOT_PATH / "replays" / "cheater.osr")]
# check = Check(replays)
iterator = circleguard.run(Check(replays))
# iterator = circleguard.map_check(221777, num=3)
# iterator = circleguard.local_check()
for result in iterator:
    print(result.similarity)
    print(result.replay1.id)
    print(result.replay2.id)
# circleguard.verify(1699366, 12092800, 7477458, False)


# Check objects should be able to be instantiated with an arbitrary mix of ReplayPath and ReplayMap and maybe other, client implemented, objects
# usage on the client end: circleguard.run(check)
# circleguard.verify() etc are just shortcuts for making Check objects with the relevant ReplayMap and (if applicable) ReplayPath objects
