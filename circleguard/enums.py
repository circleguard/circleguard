from enum import Enum

from exceptions import UnknownAPIException, RatelimitException, InvalidKeyException, ReplayUnavailableException
# strings taken from osu api error responses
# [api response, exception class type, details to pass to an exception]
class Error(Enum):
    NO_REPLAY         = ["Replay not available.", ReplayUnavailableException, "Could not find any replay data. Skipping"]
    RATELIMITED       = ["Requesting too fast! Slow your operation, cap'n!", RatelimitException, "We were ratelimited. Waiting it out"]
    RETRIEVAL_FAILED  = ["Replay retrieval failed.", ReplayUnavailableException, "Replay retrieval failed. Skipping"]
    INVALID_KEY       = ["Please provide a valid API key.", InvalidKeyException, "Please provide a valid key in secret.py"]
    UNKNOWN           = ["Unknown error.", UnknownAPIException, "Unknown error when requesting replay. Please lodge an issue with the devs immediately"]

class Mod(Enum):
    NoMod          = NM = 0
    NoFail         = NF = 1
    Easy           = EZ = 2
    NoVideo        = NV = 4
    Hidden         = HD = 8
    HardRock       = HR = 16
    SuddenDeath    = SD = 32
    DoubleTime     = DT = 64
    Relax          = RL = 128
    HalfTime       = HT = 256
    Nightcore      = NC = 512
    Flashlight     = FL = 1024
    Autoplay       = CN = 2048
    SpunOut        = SO = 4096
    Autopilot      = AP = 8192
    Perfect        = PF = 16384
    Key4           = K4 = 32768
    Key5           = K5 = 65536
    Key6           = K6 = 131072
    Key7           = K7 = 262144
    Key8           = K8 = 524288
    keyMod         = KM = 1015808
    FadeIn         = FI = 1048576
    Random         = RD = 2097152
    LastMod        = LM = 4194304
    TargetPractice = TP = 8388608
    Key9           = K9 = 16777216
    Coop           = CO = 33554432
    Key1           = K1 = 67108864
    Key3           = K3 = 134217728
    Key2           = K2 = 268435456
