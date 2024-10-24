# Schedule meetings with MaxSAT

## Installation
(Optionally) set up a virtual environment for python

Install PySAT https://pysathq.github.io/installation/

The dependencies of this project are listed in `requirements.txt`, update this file if the PySAT installation instruction changes!

    pip install -r requirements.txt
    
Currently, the data set is hardcoded into the file. 
To use mor egenerally, invoke `create_scrum_data(num_slots, groups)` with the number of slots your want, and a dictionary that maps 
team names to their participants (string -> set(string)) and then `schedule_scrum_meetings` with the retunred value.
