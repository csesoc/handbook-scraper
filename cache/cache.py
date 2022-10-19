"""
Loads cached data such as exclusions, program mappings, etc, into local
JSON files for faster algorithms performance.
This should be run from the backend directory or via runprocessors
"""

from functools import reduce
import operator
import re
from typing import Any

from cache.cache_config import (CACHE_CONFIG, CACHED_EQUIVALENTS_FILE,
                                           CACHED_EXCLUSIONS_FILE,
                                           CACHED_WARNINGS_FILE,
                                           CONDITIONS_PROCESSED_FILE,
                                           COURSE_MAPPINGS_FILE,
                                           COURSES_PROCESSED_FILE,
                                           MAPPINGS_FILE,
                                           PROGRAM_MAPPINGS_FILE,
                                           PROGRAMS_FORMATTED_FILE)
from data.utility.data_helpers import read_data, write_data

def cache_equivalents():
    """
    Reads from processed courses and stores the exclusions in a map mapping
    COURSE: {
        EXCLUSION_1: 1,
        EXCLUSION_2: 1,
        EXCLUSION_3: 1
    }
    NOTE: Should run this after all the conditions have been processed as sometimes
    exclusions are included inside the conditions text
    """

    courses = read_data(COURSES_PROCESSED_FILE)

    cached_exclusions = {}

    for course, data in courses.items():
        cached_exclusions[course] =  data["equivalents"]

    write_data(cached_exclusions, CACHED_EQUIVALENTS_FILE)

def cache_exclusions():
    """
    Reads from processed courses and stores the exclusions in a map mapping
    COURSE: {
        EXCLUSION_1: 1,
        EXCLUSION_2: 1,
        EXCLUSION_3: 1
    }
    NOTE: Should run this after all the conditions have been processed as sometimes
    exclusions are included inside the conditions text
    """

    courses = read_data(COURSES_PROCESSED_FILE)

    cached_exclusions = {}

    for course, data in courses.items():
        cached_exclusions[course] = data["exclusions"] | data["equivalents"]

    write_data(cached_exclusions, CACHED_EXCLUSIONS_FILE)

def cache_mappings():
    """
    Writes to mappings.json and courseMappings.json (i.e maps courses to corresponding school/faculty)
    """
    mappings = {}
    courseMappings = {}
    courses = read_data(COURSES_PROCESSED_FILE)

    # Tokenise faculty using regex, e.g 'UNSW Business School' -> 'F Business'
    def tokeniseFaculty(Faculty):
        faculty_token = "F "
        if re.search("Faculty of.+", Faculty):
            match_object = re.search("(?<=Faculty\sof\s)[^\s\n\,]+", Faculty)
        elif re.search("UNSW", Faculty):
            match_object = re.search(r"(?<=UNSW\s)[^\s\n\,]+", Faculty)
        else:
            match_object = re.search("^([\w]+)", Faculty)
        match = match_object.group()
        faculty_token += match
        return faculty_token

    # Tokenise faculty using regex, e.g 'School of Psychology' -> 'S Psychology'
    def tokeniseSchool(School):
        school_token = "S "
        if re.search("School\sof\sthe.+", School):
            match_object = re.search("(?<=School\sof\sthe\s)[^\s\n\,]+", School)
        elif re.search("School\sof\s.+", School):
            match_object = re.search("(?<=School\sof\s)[^\s\n\,]+", School)
        elif re.search("^(UC)", School):
            match_object = re.search("(?<=UC\s)[^\s\n\,]+", School)
            match = school_token + "UC-" +  match_object.group()
            return match
        elif re.search("UNSW", School):
            match_object = re.search("(?<=UNSW\s)[^\s\n\,]+", School)
        else:
            match_object = re.search("^([\w]+)", School)
        match = match_object.group()
        school_token += match
        return school_token

    # add faculties to mappings.json
    for course in courses:
        faculty = courses[course]['faculty']
        if faculty not in mappings:
            faculty_token = tokeniseFaculty(faculty)
            mappings[faculty] = faculty_token
            courseMappings[faculty_token] = {}
    # add schools to mappings.json
    for course in courses.values():
        if 'school' in course:
            school = course['school']
            if school not in mappings:
                school_token = tokeniseSchool(school)
                mappings[school] = school_token
                courseMappings[school_token] = {}
    write_data(mappings, MAPPINGS_FILE)

    # finalise
    for course in courses.values():
        courseCode = course['code']
        courseFaculty = course['faculty']
        if 'school' in course:
            courseSchool = course['school']
            courseMappings[mappings[courseSchool]][courseCode] = 1
        courseMappings[mappings[courseFaculty]][courseCode] = 1

    write_data(courseMappings, COURSE_MAPPINGS_FILE)

def cache_program_mappings():
    """
    Maps CODE# to programs, e.g.
    {
        "ACTL#": {
            "3586": 1,
            "4520": 1,
        }
    }

    Achieves this by looking for a keyword in the program's title
    """

    keyword_codes: dict[str, list[str]] = read_data(CACHE_CONFIG)

    mappings = {
        code: {} for code
        in reduce(operator.add, keyword_codes.values())
    }

    programs: dict[str, Any] = read_data(PROGRAMS_FORMATTED_FILE)

    for program in programs.values():
        for keyword in keyword_codes.keys():
            if keyword.lower() in program["title"].lower():
                for code in keyword_codes[keyword]:
                    mappings[code][program["code"]] = 1

    write_data(mappings, PROGRAM_MAPPINGS_FILE)
