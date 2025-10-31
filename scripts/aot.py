from paradox_file_parser import ParadoxFileParser
import os
import re
import json
import yaml
import shutil

state_file_dir = {
    # "map_data": r"map_data/state_regions/",
    "state": r"common/history/states/",
    "pops": r"common/history/pops/",
    "buildings": r"common/history/buildings/",
    # "trade": r"common/history/trade/"
}

def clear_mod_dir(dir_dict):
    # Clear the output directory
    for dir in dir_dict.values():
        if not os.path.exists(dir):
            os.makedirs(dir)
        else:
            for file in os.listdir(dir):
                os.remove(os.path.join(dir, file))

class ModState:
    def __init__(self, base_game_dir, mod_dir, diff=False):
        self.base_parsers = {}
        self.mod_parsers = {}
        self.load_directory_files(base_game_dir, mod_dir, diff)

    def load_directory_files(self, base_game_dir, mod_dir, diff=False):
        for entity_type, dir_path in base_game_dir.items():
            self.base_parsers[entity_type] = ParadoxFileParser()
            self.mod_parsers[entity_type] = ParadoxFileParser()
            self.load_files_from_directory(entity_type, dir_path, base_game=True)

            if diff:
                self.mod_parsers[entity_type].set_data_from_changes_json(
                    self.base_parsers[entity_type],
                    mod_dir + os.sep + entity_type + ".json",
                )
            else:
                if entity_type in mod_dir:
                    self.load_files_from_directory(
                        entity_type, mod_dir[entity_type], base_game=False
                    )

    def load_files_from_directory(self, entity_type, dir_path, base_game=True):
        for file_name in os.listdir(dir_path):
            if file_name.startswith("_"):
                continue
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path):
                print("reading file:", file_path)
                if base_game:
                    self.base_parsers[entity_type].parse_file(file_path)
                    self.mod_parsers[entity_type].parse_file(file_path)
                else:
                    mod_data = self.parse_mod_file(file_path)
                    self.mod_parsers[entity_type].merge_data(mod_data)

    def parse_mod_file(self, file_path):
        parser = ParadoxFileParser()
        parser.parse_file(file_path)
        return parser.data

    def get_data(self, entity_type):
        return (
            self.mod_parsers[entity_type].data
            if entity_type in self.mod_parsers
            else None
        )

    def get_string_form(self, entity_type):
        return (
            str(self.mod_parsers[entity_type])
            if entity_type in self.mod_parsers
            else None
        )

    def update_and_write_file(self, entity_type, file_path):
        if entity_type in self.mod_parsers:
            self.mod_parsers[entity_type].write_file(
                file_path, self.base_parsers[entity_type]
            )

    def save_changes_to_json(self, file_path, entity_type=None):
        if entity_type is None:
            for entity_type in self.mod_parsers:
                self.mod_parsers[entity_type].save_changes_to_json(
                    self.base_parsers[entity_type],
                    file_path + os.sep + entity_type + ".json",
                )
        else:
            if entity_type in self.mod_parsers:
                self.mod_parsers[entity_type].save_changes_to_json(
                    self.base_parsers[entity_type], file_path
                )
            else:
                raise Exception(f"entity_type {entity_type} not found")

class Building:
    def __init__(self, dict):
        '''Initialize the building object with a dictionary'''
        if "building" in dict.keys():
            self.building = dict["building"]
        else:
            self.building = None
        self.building_ownership = []
        self.country_ownership = []
        self.company_ownership = []
        self.reserves = 0
        self.activate_production_methods = []
        self.isMonument = ("level" in dict.keys())
        if self.isMonument: return
        if "add_ownership" in dict.keys():
            if "building" in dict["add_ownership"].keys():
                if not isinstance(dict["add_ownership"]["building"], list):
                    dict["add_ownership"]["building"] = [dict["add_ownership"]["building"]]
                self.building_ownership = dict["add_ownership"]["building"]
            if "country" in dict["add_ownership"].keys():
                if not isinstance(dict["add_ownership"]["country"], list):
                    dict["add_ownership"]["country"] = [dict["add_ownership"]["country"]]
                self.country_ownership = dict["add_ownership"]["country"]
            if "company" in dict["add_ownership"].keys():
                if not isinstance(dict["add_ownership"]["company"], list):
                    dict["add_ownership"]["company"] = [dict["add_ownership"]["company"]]
                self.company_ownership = dict["add_ownership"]["company"]
        if "reserves" in dict.keys():
            self.reserves = int(dict["reserves"])
        if "activate_production_methods" in dict.keys():
            self.activate_production_methods = dict["activate_production_methods"]
        self.refresh()

    def is_empty(self):
        '''Check if the building object is empty'''
        if self.building is None:
            return True
        if self.isMonument:
            return False
        if (not self.building_ownership and not self.country_ownership and not self.company_ownership):
            return True
        return False
    
    def refresh(self):
        '''Sort ownerships and merge duplicate ownerships'''
        if self.is_empty():
            self.building = None
            self.building_ownership = []
            self.country_ownership = []
            self.company_ownership = []
            return
        sorted_ownership = []
        for other_ownership in self.building_ownership:
            found = False
            for this_ownership in sorted_ownership:
                if (this_ownership["type"] == other_ownership["type"] and
                    this_ownership["country"] == other_ownership["country"] and
                    this_ownership["region"] == other_ownership["region"]):
                    found = True
                    this_ownership["levels"] = int(this_ownership["levels"]) + int(other_ownership["levels"])
                    break
            if not found:
                sorted_ownership.append(other_ownership)
        self.building_ownership = sorted_ownership
        if not isinstance(self.activate_production_methods, list):
            self.activate_production_methods = [self.activate_production_methods]

    def level_cnt(self):
        if self.isMonument: return 1
        levels = 0
        for ownership in (self.building_ownership + self.country_ownership + self.company_ownership):
            levels += int(ownership["levels"])
        return levels
    
    def __iadd__(self, other):
        '''Add two building objects together'''
        if self.building != other.building:
            raise ValueError("Cannot add buildings with different types")
        for ownership in other.building_ownership:
            found = False
            for this_ownership in self.building_ownership:
                if (this_ownership["type"] == ownership["type"] and
                    this_ownership["country"] == ownership["country"] and
                    this_ownership["region"] == ownership["region"]):
                    found = True
                    this_ownership["levels"] = int(this_ownership["levels"]) + int(ownership["levels"])
                    break
            if not found:
                self.building_ownership.append(ownership)
        for ownership in other.country_ownership:
            found = False
            for this_ownership in self.country_ownership:
                if this_ownership["country"] == ownership["country"]:
                    found = True
                    this_ownership["levels"] = int(this_ownership["levels"]) + int(ownership["levels"])
                    break
            if not found:
                self.country_ownership.append(ownership)
        for ownership in other.company_ownership:
            found = False
            for this_ownership in self.company_ownership:
                if (this_ownership["type"] == ownership["type"] and
                    this_ownership["country"] == ownership["country"]):
                    found = True
                    this_ownership["levels"] = int(this_ownership["levels"]) + int(ownership["levels"])
                    break
            if not found:
                self.company_ownership.append(ownership)
        return self
    
    def __str__(self):
        building_str = f"            create_building = {{\n"
        if self.is_empty():
            building_str += "            }\n"
            return building_str
        building_str += f"                building = {self.building}\n"
        if self.isMonument:
            building_str += f"                level = 1\n"
            building_str += "            }\n"
            return building_str
        building_str += f"                add_ownership = {{\n"
        for ownership in self.building_ownership:
            building_str += f"                    building = {{\n"
            building_str += f"                        type = {ownership['type']}\n"
            building_str += f"                        country = {ownership['country']}\n"
            building_str += f"                        levels = {ownership['levels']}\n"
            building_str += f"                        region = {ownership['region']}\n"
            building_str += f"                    }}\n"
        for ownership in self.country_ownership:
            building_str += f"                    country = {{\n"
            building_str += f"                        country = {ownership['country']}\n"
            building_str += f"                        levels = {ownership['levels']}\n"
            building_str += f"                    }}\n"
        for ownership in self.company_ownership:
            building_str += f"                    company = {{\n"
            building_str += f"                        type = {ownership['type']}\n"
            building_str += f"                        country = {ownership['country']}\n"
            building_str += f"                        levels = {ownership['levels']}\n"
            building_str += f"                    }}\n"
        building_str += f"                }}\n"
        building_str += f"                reserves = {self.reserves}\n"
        building_str += f"                activate_production_methods = {{\n"
        for method in self.activate_production_methods:
            building_str += f"                    {method}\n"
        building_str += f"                }}\n"
        building_str += f"            }}\n"
        return building_str

class Buildings:
    def __init__(self, buildings_dict):
        self.data = {}
        for state_id in buildings_dict["BUILDINGS"].keys():
            if state_id == "if": # dlc buildings
                continue
            print("Reading buildings: "+state_id)
            self.data[state_id] = {}
            for tag in buildings_dict["BUILDINGS"][state_id].keys():
                self.data[state_id][tag] = []
                if (not isinstance(buildings_dict["BUILDINGS"][state_id][tag], dict)) or ("create_building" not in buildings_dict["BUILDINGS"][state_id][tag].keys()):
                    continue
                if not isinstance(buildings_dict["BUILDINGS"][state_id][tag]["create_building"], list):
                    buildings_dict["BUILDINGS"][state_id][tag]["create_building"] = [buildings_dict["BUILDINGS"][state_id][tag]["create_building"]]
                for building in buildings_dict["BUILDINGS"][state_id][tag]["create_building"]:
                    self.data[state_id][tag].append(Building(building))
        self.format()

    def format(self):
        for state_id in self.data.keys(): # Restore the original structure of certain building keys
            if state_id == "if":
                continue
            for tag in self.data[state_id].keys():
                for i in range(len(self.data[state_id][tag]), 0, -1):
                    if self.data[state_id][tag][i-1].is_empty():
                        self.data[state_id][tag].pop(i-1)

    def merge(self, merge_dict):
        # Merge building ownerships
        for state_id in self.data.keys():
            if state_id == "if": # dlc buildings
                continue
            for tag in self.data[state_id].keys():
                if not isinstance(self.data[state_id][tag], list):
                    continue
                for building in self.data[state_id][tag]:
                    if building.is_empty() or building.isMonument:
                        continue
                    for ownership in building.building_ownership:
                        region = ownership["region"].replace('\"', '') # Remove '\"' from ownership["region"]
                        for diner, food_list in merge_dict.items():
                            if region in food_list:
                                ownership["region"] = '\"'+diner+'\"'
                                building.refresh()
                                break
        # Merge building
        for diner, food_list in merge_dict.items():
            for food in food_list:
                if ("s:"+food) in self.data.keys():
                    print(f'Merging {food} building data into {diner}')
                    # self.merge_by_id("s:"+diner, "s:"+food)
                    for tag in self.data["s:"+food].keys():
                        if tag not in self.data["s:"+diner].keys():
                            self.data["s:"+diner][tag] = self.data["s:"+food][tag]
                            continue
                        for other_building in self.data["s:"+food][tag]:
                            if other_building.is_empty():
                                continue
                            found = False
                            for this_building in self.data["s:"+diner][tag]:
                                if this_building.building == other_building.building:
                                    found = True
                                    this_building += other_building
                                    break
                            if not found:
                                self.data["s:"+diner][tag].append(other_building)
                    # Remove the food from data
                    self.data.pop("s:"+food)
        self.format()
    
    def consolidate(self, state_id, tag):
        # Consolidate buildings in all split states in `state_id` into a single state under `tag`
        consolidated_buildings = []
        for other_tag in self.data[state_id].keys():
            for other_building in self.data[state_id][other_tag]:
                if other_building.is_empty():
                    continue
                found = False
                for this_building in consolidated_buildings:
                    if this_building.building == other_building.building:
                        found = True
                        this_building += other_building
                        break
                if not found:
                    consolidated_buildings.append(other_building)
        self.data[state_id] = {tag: consolidated_buildings}

    def get_str(self, state_id):
        if state_id == "if":
            return ""
        building_str = f'    {state_id} = {{\n'
        for tag in self.data[state_id].keys():
            building_str += f'        {tag} = {{\n'
            for building in self.data[state_id][tag]:
                building_str += str(building)
            building_str += f'        }}\n'
        building_str += f'    }}\n'

        return building_str

    def dump(self, dir):
        with open(dir, 'w', encoding='utf-8-sig') as file:
            file.write('BUILDINGS = {\n')
            for state_id in self.data.keys():
                print("Exporting building data: "+state_id)
                file.write(self.get_str(state_id))
            file.write('}\n')

class Pops:
    def __init__(self, pops_dict):
        self.data = pops_dict["POPS"]
        self.format()

    def format(self):
        for state_id in self.data.keys(): # Restore the original structure of certain pop keys
            print(f'Formatting pop data: {state_id}')
            for tag in self.data[state_id].keys():
                if not isinstance(self.data[state_id][tag], dict):
                    self.data[state_id][tag] = {"create_pop": []}
                    continue
                if isinstance(self.data[state_id][tag]["create_pop"], tuple):
                    self.data[state_id][tag]["create_pop"] = list(self.data[state_id][tag]["create_pop"])
                elif not isinstance(self.data[state_id][tag]["create_pop"], list):
                    self.data[state_id][tag]["create_pop"] = [self.data[state_id][tag]["create_pop"]]

    def is_same_pop(self, pop1, pop2):
        if pop1["culture"] != pop2["culture"]:
            return False
        if pop1.get("pop_type") != pop2.get("pop_type"):
            return False
        if pop1.get("religion") != pop2.get("religion"):
            return False
        return True

    def merge_by_id(self, this, other): # this, other are "state_id" strings
        for tag in self.data[other].keys():
            if tag in self.data[this].keys():
                for other_pop in self.data[other][tag]["create_pop"]:
                    found = False
                    hasAttributeType = "pop_type" in other_pop
                    hasAttributeReligion = "religion" in other_pop
                    for this_pop in self.data[this][tag]["create_pop"]:
                        if other_pop["culture"] != this_pop["culture"]:
                            continue
                        if hasAttributeType and "pop_type" in this_pop:
                            if other_pop["pop_type"] == this_pop["pop_type"]:
                                if hasAttributeReligion and "religion" in this_pop:
                                    if other_pop["religion"] == this_pop["religion"]:
                                        this_pop["size"] = int(this_pop["size"]) + int(other_pop["size"])
                                        found = True
                                        break
                                elif not hasAttributeReligion and "religion" not in this_pop:
                                    this_pop["size"] = int(this_pop["size"]) + int(other_pop["size"])
                                    found = True
                                    break
                            continue
                        elif not hasAttributeType and "pop_type" not in this_pop:
                            if hasAttributeReligion and "religion" in this_pop:
                                if other_pop["religion"] == this_pop["religion"]:
                                    this_pop["size"] = int(this_pop["size"]) + int(other_pop["size"])
                                    found = True
                                    break
                            elif not hasAttributeReligion and "religion" not in this_pop:
                                this_pop["size"] = int(this_pop["size"]) + int(other_pop["size"])
                                found = True
                                break
                    if not found:
                        self.data[this][tag]["create_pop"].append(other_pop)
            else:
                self.data[this][tag] = self.data[other][tag]

    def consolidate(self, state_id, tag):
        # Consolidate pops in all split states in `state_id` into a single state under `tag`
        consolidated_pops = []
        for other_tag in self.data[state_id].keys():
            for other_pop in self.data[state_id][other_tag]["create_pop"]:
                found = False
                for this_pop in consolidated_pops:
                    if self.is_same_pop(this_pop, other_pop):
                        this_pop["size"] = int(this_pop["size"]) + int(other_pop["size"])
                        found = True
                        break
                if not found:
                    consolidated_pops.append(other_pop)
        self.data[state_id] = {tag: {"create_pop": consolidated_pops}}

    def get_str(self, state_id):
        state_str = f'    {state_id} = {{\n'
        for tag in self.data[state_id].keys():
            state_str += f'        {tag} = {{\n'
            for pop in self.data[state_id][tag]["create_pop"]:
                state_str += f'            create_pop = {{\n'
                for key, value in pop.items():
                    state_str += f'                {key} = {value}\n'
                state_str += f'            }}\n'
            state_str += f'        }}\n'
        state_str += f'    }}\n'

        return state_str

    def merge(self, merge_dict):
        for diner, food_list in merge_dict.items():
            for food in food_list:
                if ("s:"+food) in self.data.keys():
                    print(f'Merging {food} pop data into {diner}')
                    self.merge_by_id(("s:"+diner), ("s:"+food))
                    self.data.pop("s:"+food)

    def dump(self, dir):
        with open(dir, 'w', encoding='utf-8-sig') as file:
            file.write('POPS = {\n')
            for state_id in self.data.keys():
                print("Exporting pop data: "+state_id)
                file.write(self.get_str(state_id))
            file.write('}\n')

class States:
    def __init__(self, states_dict):
        self.data = states_dict["STATES"]
        self.format()

    def format(self):
        for state_id in self.data.keys():
            print(f'Formatting state data: {state_id}')
            if not isinstance(self.data[state_id], dict):
                self.data[state_id] = {"create_state": []}
                continue
            if isinstance(self.data[state_id]["create_state"], tuple):
                self.data[state_id]["create_state"] = list(self.data[state_id]["create_state"])
            elif not isinstance(self.data[state_id]["create_state"], list):
                self.data[state_id]["create_state"] = [self.data[state_id]["create_state"]]
            for state in self.data[state_id]["create_state"]:
                if isinstance(state["owned_provinces"], tuple):
                    state["owned_provinces"] = list(state["owned_provinces"])
                elif not isinstance(state["owned_provinces"], list):
                    state["owned_provinces"] = [state["owned_provinces"]]
                if "state_type" in state.keys():
                    if isinstance(state["state_type"], tuple):
                        state["state_type"] = list(state["state_type"])
                    elif not isinstance(state["state_type"], list):
                        state["state_type"] = [state["state_type"]]
            if "add_homeland" in self.data[state_id].keys():
                if isinstance(self.data[state_id]["add_homeland"], tuple):
                    self.data[state_id]["add_homeland"] = list(self.data[state_id]["add_homeland"])
                elif not isinstance(self.data[state_id]["add_homeland"], list):
                    self.data[state_id]["add_homeland"] = [self.data[state_id]["add_homeland"]]
            if "add_claim" in self.data[state_id].keys():
                if isinstance(self.data[state_id]["add_claim"], tuple):
                    self.data[state_id]["add_claim"] = list(self.data[state_id]["add_claim"])
                elif not isinstance(self.data[state_id]["add_claim"], list):
                    self.data[state_id]["add_claim"] = [self.data[state_id]["add_claim"]]

    def merge_by_id(self, this, other): # this, other are "state_id" strings
        # Merge create_state
        for province in self.data[other]["create_state"]:
            found = False
            for province_ref in self.data[this]["create_state"]:
                if province["country"] == province_ref["country"]:
                    found = True
                    province_ref["owned_provinces"] += province["owned_provinces"]
                    break
            if not found:
                self.data[this]["create_state"].append(province)
        # Merge add_homeland
        if "add_homeland" in self.data[other].keys():
            for culture in self.data[other]["add_homeland"]:
                if culture not in self.data[this]["add_homeland"]:
                    self.data[this]["add_homeland"].append(culture)
        # Merge add_claim
        if "add_claim" not in self.data[this].keys():
            if "add_claim" in self.data[other].keys():
                self.data[this]["add_claim"] = self.data[other]["add_claim"]
        elif "add_claim" in self.data[other].keys():
            for country in self.data[other]["add_claim"]:
                if country not in self.data[this]["add_claim"]:
                    self.data[this]["add_claim"].append(country)

    def consolidate(self, state_id, tag):
        # Consolidate all split states in `state_id` into a single state
        consolidated_provinces = []
        for province in self.data[state_id]["create_state"]:
            consolidated_provinces += province["owned_provinces"]
        self.data[state_id]["create_state"] = [{"country": tag, "owned_provinces": consolidated_provinces, "state_type": ["unincorporated"]}]

    def get_str(self, state_id):
        state_str = f'    {state_id} = {{\n'
        for province in self.data[state_id]["create_state"]:
            state_str += f'        create_state = {{\n'
            state_str += f'            country = {province["country"]}\n'
            state_str += f'            owned_provinces = {{ '
            for owned_province in province["owned_provinces"]:
                state_str += f'{owned_province} '
            state_str += '}\n'
            if "state_type" in province.keys():
                for state_type in province["state_type"]:
                    state_str += f'            state_type = {state_type}\n'
            state_str += '        }\n\n'
        if "add_homeland" in self.data[state_id].keys():
            for culture in self.data[state_id]["add_homeland"]:
                state_str += f'        add_homeland = {culture}\n'
        if "add_claim" in self.data[state_id].keys():
            for country in self.data[state_id]["add_claim"]:
                state_str += f'        add_claim = {country}\n'
        state_str += '    }\n'

        return state_str

    def merge(self, merge_dict):
        for diner, food_list in merge_dict.items():
            for food in food_list:
                if ("s:"+food) in self.data.keys():
                    print(f'Merging {food} state data into {diner}')
                    self.merge_by_id(("s:"+diner), ("s:"+food))
                    self.data.pop("s:"+food)

    def dump(self, dir):
        with open(dir, 'w', encoding='utf-8-sig') as file:
            file.write('STATES = {\n')
            for state_id in self.data.keys():
                print("Exporting state data: "+state_id)
                file.write(self.get_str(state_id))
            file.write('}\n')

class Mod:
    def __init__(self, game_root_dir, write_dir, cache_dir="./data"):
        self.base_game_dir = {}
        self.mod_dir = {}
        self.game_root_dir = game_root_dir
        self.write_dir = write_dir
        self.cache_dir = cache_dir

        # Set the base game and mod directories
        for key, value in state_file_dir.items():
            self.base_game_dir[key] = self.game_root_dir+value
            self.mod_dir[key] = write_dir+value
        clear_mod_dir(self.mod_dir)

        # Read base game data
        mod_state = ModState(self.base_game_dir, self.mod_dir)
        game_data = {}
        for key in self.base_game_dir.keys():
            game_data[key] = mod_state.get_data(key)

        # Parse data
        # self.map_data = MapData(game_data["map_data"])
        self.buildings = Buildings(game_data["buildings"])
        self.pops = Pops(game_data["pops"])
        self.states = States(game_data["state"])
        # self.trade = Trade(game_data["trade"])

    def consolidate(self, tag, except_list=[]):
        # Write cleared base game data to mod directory
        for key, value in self.base_game_dir.items():
            for file in os.listdir(value):
                if file == "00_states_merging.txt":
                    continue
                with open(self.mod_dir[key]+file, 'w', encoding='utf-8-sig') as file:
                    file.write("")

        for state_id in list(self.pops.data.keys()):
            if state_id in except_list:
                continue
            print(f'Consolidating state data: {state_id}')
            self.states.consolidate(state_id, tag)
            self.pops.consolidate(state_id, tag)
            self.buildings.consolidate(state_id, tag)
        # Export data
        self.states.dump(self.mod_dir["state"]+"00_states.txt")
        self.pops.dump(self.mod_dir["pops"]+"00_aot_pops.txt")
        self.buildings.dump(self.mod_dir["buildings"]+"00_aot_buildings.txt")
