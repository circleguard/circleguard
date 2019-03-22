import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument("-m", "--map", dest="map_id",
                    help="checks the leaderboard on the given beatmap id against each other", type=int)

argparser.add_argument("-u", "--user", dest="user_id",
                    help="checks only the given user against the other leaderboard replays. Must be set with -m", type=int)

argparser.add_argument("--mods", help="Download and compare only replays set with the exact mods given. "
                       "Any number of arguments can be passed, and the top -n (or the number of replays available for that combination, "
                       "whichever is fewer) replays will be downloaded and compared for each argument.", nargs="*")

argparser.add_argument("-l", "--local", help=("compare scores under the replays/ directory to a beatmap leaderboard (if set with -m), "
                                             "a score set by a user on a beatmap (if set with -m and -u) or the other scores in the folder "
                                            "(default behavior)"), action="store_true")

argparser.add_argument("-t", "--threshold", help="sets the similarity threshold to print results that score under it. Defaults to 20", type=int, default=18)

argparser.add_argument("-a", "--auto", help="sets the threshold to a number of standard deviations below the average similarity", type=float, dest="stddevs")

argparser.add_argument("-n", "--num", help="how many replays to get from a beatmap. No effect if not set with -m. Must be between 2 and 100 inclusive,"
                                              "defaults to 50. NOTE: THE TIME COMPLEXITY OF THE COMPARISONS WILL SCALE WITH O(n^2).", type=int, default=50)

argparser.add_argument("-c", "--cache", help="if set, locally caches replays so they don't have to be redownloaded when checking the same map multiple times.",
                                        action="store_true")

argparser.add_argument("-s", "--silent", help="if set, you will not be prompted for a visualization of comparisons under the threshold",
                                         action="store_true")

argparser.add_argument("-v", "--verify", help="takes 3 positional arguments - map id, user1 id and user2 id. Verifies that the scores are steals of each other", nargs=3)

argparser.add_argument("--version", help="prints the program version", action="store_true")
