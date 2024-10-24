#!/usr/bin/env python3

from collections import defaultdict
from dataclasses import dataclass
from typing import List
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from pysat.card import *

debug_print = False

def print_debug(*printables) -> None:
     if not debug_print:
          return
     print(" ".join([str(i) for i in printables]))


@dataclass
class ScrumData():
    num_slots: int
    people: defaultdict[dict] ## person -> groups they belong to
    groups : defaultdict[dict] # group_name -> list of members 
    group_meeting_slot_vars : defaultdict[dict] ## (group, slot) -> int indicator variables for group meeting in slot
    person_in_group_meeting_slot : defaultdict[dict] # (person, group, slot) -> int, indicator variables for person participating in group meeting in slot 
    highest_var : int

def print_data_properties(data: ScrumData) -> None:
    print("Scrum data to compute on")
    print("Num meeting slots: ", data.num_slots)
    print("People: ", list(data.people.keys()))
    print("Groups and their members")
    for group_name, members in groups.items():
         print("\t", group_name, ": ", members)
    print()


## Expects the grous as a dictionary mapping a group name to the members of it. Will break if group names are not unique, but does not check 
def create_scrum_data(_num_slots : int, _groups : defaultdict) -> ScrumData:
    ## crete mapping of people to the groups they belong to
    dict_people = defaultdict(set)
    for group_name in _groups: 
        for person in _groups[group_name]:
            dict_people[person].add(group_name)

    ### then we create a mapping to the groups they belong to 
    _highest_var = 0
    ## add names for the indicators of group meetings these variables are meant to indicate that a gorup should keep its meeting in slot
    _group_meeting_slot_vars = defaultdict(None)

    for group_name in _groups: 
        for slot_num in range(1, _num_slots +1):
            _highest_var = _highest_var + 1
            _group_meeting_slot_vars[(group_name, slot_num)] = _highest_var

    ## add indicators for a person participating in the meeting of group in a specific slot. For a fixed person we only define these variables for the groups in which the person is am meber of
    _person_in_group_meeting_slot = defaultdict(None)
    for group_name in _groups: 
        for person in _groups[group_name]:
             for slot_num in range(1, _num_slots +1):
                 _highest_var = _highest_var + 1
                 _person_in_group_meeting_slot[(person, group_name, slot_num)] = _highest_var

    return ScrumData(num_slots=_num_slots, people = dict_people, groups=_groups, 
                    group_meeting_slot_vars=_group_meeting_slot_vars, 
                    person_in_group_meeting_slot=_person_in_group_meeting_slot,
                    highest_var=_highest_var)

def create_wcnf(data : ScrumData) -> WCNF:
    cnf = WCNF()
    top_var = data.highest_var
    
    print_debug("every group has a meeting in exactly one slot")
    for group_name in data.groups:
        slot_vars = [data.group_meeting_slot_vars[(group_name, x)] for x in range(1, data.num_slots +1) ]
        print_debug("group_name ", group_name, " range ", range(1,data.num_slots+1), " slot_vars ", slot_vars)
        assert all(var is not None for var in slot_vars)
        # at least one meeting
        cnf.append(slot_vars)
        # at most one meeting
        print_debug("Top_var ", top_var)
        enc = CardEnc.atmost(lits=slot_vars, bound=1, top_id = top_var, encoding=EncType.seqcounter)
        cnf.extend(enc.clauses)
        top_var = max(top_var, cnf.nv)
            
    print_debug("every person has at most one meeting in a slot" )
    for person, groups in data.people.items():
        for slot in range(1, data.num_slots +1):
            slot_vars = [data.person_in_group_meeting_slot[(person, g, slot)] for g in groups ]
            assert all(var is not None for var in slot_vars)
            assert len(slot_vars) > 0
            print_debug("Person ", person, " slot ", slot, " vars ", slot_vars)       
            print_debug("Top_var ", top_var)
            enc = CardEnc.atmost(lits=slot_vars, bound=1, top_id = top_var, encoding=EncType.seqcounter)
            cnf.extend(enc.clauses)
            top_var = max(top_var, cnf.nv)
    
    ### A person cannot attend a groups meeting in a slot if that meeting is not being held
    print_debug("a person can not attend a meeting that does not exist" )
    for person, groups in data.people.items():
        for group in groups: 
            for slot in range(1, data.num_slots +1):
                print_debug("Person ", person, " slot ", slot, " group ", group , " vars ",  data.group_meeting_slot_vars[(group, slot)], " or ",  -data.person_in_group_meeting_slot[(person, group, slot)]  )
                cnf.append([data.group_meeting_slot_vars[(group, slot)], -data.person_in_group_meeting_slot[(person, group, slot)]   ])

    print_debug("soft constraints: every person should make the meetings of groups they are members of")
    for person, groups in data.people.items():
        for g in groups: 
            meet_vars = [data.person_in_group_meeting_slot[(person, g, s)] for s in range(1, data.num_slots +1)] 
            print_debug("Person ", person, " group ", g, " vars ", meet_vars)
            cnf.append(meet_vars, weight=1)
    return cnf

def get_group_meeting_slot(group_name : str, model_set : set, data: ScrumData ) -> int:
    meeting_times = [slot for slot in range(1, data.num_slots +1) if data.group_meeting_slot_vars[(group_name, slot)] in model_set]
    if (len(meeting_times) != 1):
            print("Group: ", group_name, " meeting slot: ", meeting_times)
    assert len(meeting_times) == 1
    return meeting_times[0]

## Debug method
def get_non_group_meeting_slots(group_name : str, model_set : set, data: ScrumData ) -> List[int]:
    meeting_times = [slot for slot in range(1, data.num_slots +1) if -data.group_meeting_slot_vars[(group_name, slot)] in model_set]
    if (len(meeting_times) != 1):
            print("Group: ", group_name, " meeting slot: ", meeting_times)
    return meeting_times

def get_meetings_in_slot(person : str, slot: int, model_set : set, data: ScrumData ):
    groups = data.people[person]
    meeting_participation = [group for group in groups if data.person_in_group_meeting_slot[(person, group, slot)] in model_set]
    if (len(meeting_participation) > 1):
                print("Person: ", person, " meeting slot: ", slot, " participation ", meeting_participation)
    assert len(meeting_participation) <= 1
    if len(meeting_participation) == 0:
         return None 
    return meeting_participation[0]

def get_meetings_missed(person : str,  model_set : set, data: ScrumData ) -> List[str]:
     groups = data.people[person]
     missed = [g for g in groups if all( data.person_in_group_meeting_slot[(person, g, slot)] not in model_set for slot in range(1, data.num_slots +1) )]
     return missed


def interpret_model(model : List[int], data : ScrumData, missed_meetings : int) -> None:
    model_set = set(model)
    print("Found schedule with ", missed_meetings, " missed meetings"  )
    print("Group Schedules")
    for group_name in data.groups:        
        print("Group: ", group_name, " meeting slot: ", get_group_meeting_slot(group_name, model_set, data))
    
    print()
    print("People schedules")
    for person in data.people:
        schedule = "Person " + person + ":"
        for slot in range(1, data.num_slots +1):
            schedule = schedule + "\n\tslot " + str(slot) + "-> "
            groups_participated_in = get_meetings_in_slot(person, slot, model_set, data)
            if groups_participated_in is None:
                 schedule = schedule + "no meetings"
            else:
                 schedule = schedule + groups_participated_in
        print (schedule)
        print("Person ", person, " misses meeting with groups ", get_meetings_missed(person, model_set, data))
    return

def schedule_scrum_meetings(data : ScrumData) -> None:
    cnf = create_wcnf(data)
    with RC2(cnf) as rc2:
        model = rc2.compute() 
        interpret_model(model, data, rc2.cost)
    return 


if (__name__ == "__main__"):
    num_slots = 2
    groups = defaultdict(None)
    groups = {
    'g1' : {'A', 'B', 'C'},
    'g2' : {'B', 'C', 'D'},
    'g3' : {'A', 'C', 'D'},
    'g4' : {'D', 'E', 'F'}
    }
    scrum_data = create_scrum_data(num_slots, groups)
    print_data_properties(scrum_data)
    print_debug(scrum_data)
    schedule_scrum_meetings(scrum_data)