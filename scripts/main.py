from aot import *
import os
import json

this_dir = os.path.dirname(__file__)
game_dir = this_dir+"/../game/"
mod_dir = this_dir+"/../mod/"

except_list = ["s:STATE_ALGIERS", "s:STATE_CONSTANTINE", "s:STATE_ORAN", "s:STATE_SOUTH_MADAGASCAR", "s:STATE_NORTH_MADAGASCAR"]

def main():
    mod = Mod(game_dir, mod_dir)
    mod.consolidate("region_state:MRL", except_list)
    return

if __name__ == "__main__":
    main()
