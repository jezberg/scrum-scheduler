#!/usr/bin/env python3

from collections import defaultdict
from dataclasses import dataclass
from typing import List
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from pysat.card import *



@dataclass
class ScrumData():
    num_slots: int
    people: defaultdict[dict] ## person -> groups they belong to
    groups : defaultdict[dict] # group_name -> list of members 
    group_meeting_slot_vars : defaultdict[dict] ## (group, slot) -> int indicator variables for group meeting in slot
    person_in_group_meeting_slot : defaultdict[dict] # (person, group, slot) -> int, indicator variables for person participating in group meeting in slot 
    highest_var : int

def print_non_sat_info(data: ScrumData) -> None:
    print("Num slots ", data.num_slots)
    print("People")
    print(data.people.keys())
    print("Groups (and members)")
    print(groups)


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


def interpret_model(model : List[int], data : ScrumData, missed_meetings : int) -> None:
    model_set = set(model)
    print("Found schedule with ", missed_meetings, " missed meetings"  )
    print("Group schedules")
    for group_name in data.groups:
        meeting_times = [slot for slot in range(1, data.num_slots +1) if data.group_meeting_slot_vars[(group_name, slot)] in model_set]
        if (len(meeting_times) != 1):
            print("Group: ", group_name, " meeting slot: ", meeting_times)
        assert len(meeting_times) == 1
        print("Group: ", group_name, " meeting slot: ", meeting_times[0])
    
    print("Peoples schedules")
    for person, groups in data.people.items():
        schedule = defaultdict(None)
        for slot in range(1, data.num_slots +1):
            meeting_participation = [group for group in groups if data.person_in_group_meeting_slot[(person, group, slot)] in model_set]
            if (len(meeting_participation) > 1):
                print("Group: ", group_name, " meeting slot: ", meeting_times)
            assert len(meeting_participation) <= 1
            if (len(meeting_participation) == 1):
                schedule[slot] = meeting_participation[0]
        print("person: ", person, " schedule ", schedule)
    return

def schedule_scrum_meetings(data : ScrumData) -> None:
    cnf = WCNF()
    top_var = data.highest_var
    ### Every group should  have their meeting in exactly one slot 
   # print("Exactly one meeting per group")
    for group_name in data.groups:
        slot_vars = [data.group_meeting_slot_vars[(group_name, x)] for x in range(1, data.num_slots +1) ]
     #   print("group_name ", group_name, " range ", range(1,data.num_slots+1), " slot_vars ", slot_vars)
        assert all(var is not None for var in slot_vars)
        ## group_name needs to have at least one meeting
        cnf.append(slot_vars)
        ## group_name can have at most one meeting
        enc = CardEnc.atmost(lits=slot_vars, bound=1, top_id = top_var, encoding=EncType.seqcounter)
        cnf.extend(enc.clauses)
        top_var = cnf.nv
            
    ### Every person can attend at most one meeting in a slot 
    for person, groups in data.people.items():
        for slot in range(1, data.num_slots +1):
            slot_vars = [data.person_in_group_meeting_slot[(person, g, slot)] for g in groups ]
            assert all(var is not None for var in slot_vars)
            assert len(slot_vars) > 0
            enc = CardEnc.atmost(lits=slot_vars, bound=1, top_id = top_var, encoding=EncType.seqcounter)
            cnf.extend(enc.clauses)
            top_var = cnf.nv
    
    ### A person cannot attend a groups meeting in a slot if that meeting is not being held
    for person, groups in data.people.items():
        for group in groups: 
            for slot in range(1, data.num_slots +1):
                ### group meeting false -> person attending false
                cnf.append([data.group_meeting_slot_vars[(group, slot)], -data.person_in_group_meeting_slot[(person, group, slot)]   ])

    ### Soft constraints stating that every person should try to attend the meeting of a group theyre a member of
    for person, groups in data.people.items():
        for g in groups: 
        ##indicator variable for person attending a meeting
            meet_vars = [data.person_in_group_meeting_slot[(person, g, s)] for s in range(1, data.num_slots +1)] 
            cnf.append(meet_vars, weight=1)

    with RC2(cnf) as rc2:
        m = rc2.compute() 
       # print('model {0} has cost {1}'.format(m, rc2.cost))
        interpret_model(m, data, rc2.cost)
       # print('model {0} has cost {1}'.format(m, rc2.cost))
    return 


if (__name__ == "__main__"):
    num_slots = 2
    # a group is represented by a string "name", and a list (its members)
    groups = defaultdict(None)
    groups = {
    'g1' : {'A', 'B', 'C'},
    'g2' : {'B', 'C', 'D'},
    'g3' : {'A', 'C', 'D'},
    'g4' : {'D', 'E', 'F'}
    }
    scrum_data = create_scrum_data(num_slots, groups)
    print_non_sat_info(scrum_data)
    #print(scrum_data)
    schedule_scrum_meetings(scrum_data)