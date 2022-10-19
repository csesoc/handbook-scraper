"""
APIs for the /courses/ route.
"""
from contextlib import suppress
import re
from typing import Dict, List, Mapping, Set, Tuple

from data.config import ARCHIVED_YEARS, LIVE_YEAR
from fastapi import APIRouter, HTTPException
from fuzzywuzzy import fuzz # type: ignore
from server.database import archivesDB, coursesCOL
from server.routers.model import CourseDetails, ProgramCourses, TermsList
from server.routers.utility import get_core_courses, map_suppressed_errors


router = APIRouter(
    prefix="/courses",
    tags=["courses"],
)

@router.get(
    "/getCourse/{courseCode}",
    response_model=CourseDetails,
    responses={
        400: {
            "description": "The given course code could not be found in the database",
        },
        200: {
            "description": "Returns all course details to given code",
            "content": {
                "application/json": {
                    "example": {
                        "title": "Programming Fundamentals",
                        "code": "COMP1511",
                        "UOC": 6,
                        "level": 1,
                        "description": """An introduction to problem-solving via programming, which aims to have students develop
                                    proficiency in using a high level programming language. Topics: algorithms, program structures
                                    (statements, sequence, selection, iteration, functions), data types (numeric, character), data structures
                                    (arrays, tuples, pointers, lists), storage structures (memory, addresses), introduction to analysis of
                                    algorithms, testing, code quality, teamwork, and reflective practice. The course includes extensive practical
                                    work in labs and programming projects.</p>\n<p>Additional Information</p>\n<p>This course should be taken by
                                    all CSE majors, and any other students who have an interest in computing or who wish to be extended.
                                    It does not require any prior computing knowledge or experience.</p>\n
                                    <p>COMP1511 leads on to COMP1521, COMP1531, COMP2511 and COMP2521, which form the core of the study of
                                    computing at UNSW and which are pre-requisites for the full range of further computing courses.</p>\n<p>Due to
                                    overlapping material, students who complete COMP1511 may not also enrol in COMP1911 or COMP1921. </p>""",
                        "study_level": "Undergraduate",
                        "school": "School of Computer Science and Engineering",
                        "faculty": "Faculty of Engineering",
                        "campus": "Sydney",
                        "equivalents": {"DPST1091": 1, "COMP1917": 1},
                        "exclusions": {"DPST1091": 1},
                        "terms": ["T1", "T2", "T3"],
                        "raw_requirements": "",
                        "gen_ed": True,
                    }
                }
            },
        },
    },
)
def get_course(courseCode: str) -> Dict:
    """
    Get info about a course given its courseCode
    - start with the current database
    - if not found, check the archives
    """
    result = coursesCOL.find_one({"code": courseCode})
    if not result:
        for year in sorted(ARCHIVED_YEARS, reverse=True):
            result = archivesDB[str(year)].find_one({"code": courseCode})
            if result is not None:
                result.setdefault("raw_requirements", "")
                result["is_legacy"] = True
                break
    else:
        result["is_legacy"] = False

    if not result:
        raise HTTPException(
            status_code=400, detail=f"Course code {courseCode} was not found"
        )
    result.setdefault("school", None)
    del result["_id"]
    with suppress(KeyError):
        del result["exclusions"]["leftover_plaintext"]
    return result


@router.post(
    "/searchCourse/{search_string}",
    responses={
        200: {
            "description": "Returns a list of the most relevant courses to a search term",
            "content": {
                "application/json": {
                    "example": {
                            "ACCT1511": "Accounting and Financial Management 1B",
                            "ACCT2542": "Corporate Financial Reporting and Analysis",
                            "ACCT3202": "Industry Placement 2",
                            "ACCT3303": "Industry Placement 3",
                            "ACCT3610": "Business Analysis and Valuation",
                            "ACCT4797": "Thesis (Accounting) B",
                            "ACCT4809": "Current Developments in Auditing Research",
                            "ACCT4852": "Current Developments in Accounting Research - Managerial",
                            "ACCT4897": "Seminar in Research Methodology",
                            "ACTL1101": "Introduction to Actuarial Studies",
                            "ACTL2101": "Industry Placement 1",
                            "ACTL2102": "Foundations of Actuarial Models",
                            "ACTL3142": "Actuarial Data and Analysis",
                    }
                }
            }
        }
    },
)
def regex_search(search_string: str) -> Mapping[str, str]:
    """
    Uses the search string as a regex to match all courses with an exact pattern.
    """

    pat = re.compile(search_string, re.I)
    courses = list(coursesCOL.find({"code": {"$regex": pat}}))

    if not courses:
        for year in sorted(ARCHIVED_YEARS, reverse=True):
            courses = list(archivesDB[str(year)].find({"code": {"$regex": pat}}))
            if courses:
                break

    return { course["code"]: course["title"] for course in courses }

@router.get(
    "/getLegacyCourses/{year}/{term}",
    response_model=ProgramCourses,
    responses={
        400: {"description": "Year or Term input is incorrect"},
        200: {
            "description": "Returns the program structure",
            "content": {
                "application/json": {
                    "example": {
                        "courses": {
                            "ACCT1511": "Accounting and Financial Management 1B",
                            "ACCT2542": "Corporate Financial Reporting and Analysis",
                            "ACCT3202": "Industry Placement 2",
                            "ACCT3303": "Industry Placement 3",
                            "ACCT3610": "Business Analysis and Valuation",
                            "ACCT4797": "Thesis (Accounting) B",
                            "ACCT4809": "Current Developments in Auditing Research",
                            "ACCT4852": "Current Developments in Accounting Research - Managerial",
                            "ACCT4897": "Seminar in Research Methodology",
                            "ACTL1101": "Introduction to Actuarial Studies",
                            "ACTL2101": "Industry Placement 1",
                            "ACTL2102": "Foundations of Actuarial Models",
                            "ACTL3142": "Actuarial Data and Analysis",
                        }
                    }
                }
            },
        },
    },
)
def get_legacy_courses(year, term) -> Dict[str, Dict[str, str]]:
    """
    Gets all the courses that were offered in that term for that year
    """
    result = {c['code']: c['title'] for c in archivesDB[year].find() if term in c['terms']}

    if not result:
        raise HTTPException(status_code=400, detail="Invalid term or year. Valid terms: T0, T1, T2, T3. Valid years: 2019, 2020, 2021, 2022.")

    return {'courses' : result}


@router.get("/getLegacyCourse/{year}/{courseCode}")
def get_legacy_course(year, courseCode) -> Dict:
    """
        Like /getCourse/ but for legacy courses in the given year.
        Returns information relating to the given course
    """
    result = archivesDB[str(year)].find_one({"code": courseCode})
    if not result:
        raise HTTPException(status_code=400, detail="invalid course code or year")
    del result["_id"]
    result["is_legacy"] = True
    return result

@router.get(
    "/termsOffered/{course}/{years}",
    response_model=TermsList,
    responses={
        400: {
            "description": "The given course code could not be found in the database",
        },
        200: {
            "description": "Returns the terms a course is offered in",
            "content": {
                "application/json": {
                    "example": {
                        "terms": {
                            "2022": [ "T1", "T2", "T3" ],
                        },
                        "fails": [
                            [
                                "COMP1511",
                                "2023",
                                {
                                    "status_code": 400,
                                    "detail": "invalid course code or year",
                                    "headers": None
                                }
                            ]
                        ]
                    },
                },
            },
        },
    }
)
def terms_offered(course: str, years:str) -> Dict:
    """
    Recieves a course and a list of years. Returns a list of terms the
    course is offered in for the given years.

    Expected Input:
        course: (str) CODEXXXX
        years: (str): `+`-connected string of years
            eg: "2020+2021+2022"
    Output: {
            year: [terms offered],
            fails: [(year, exception)]
        }
    """
    fails: List[str] = []
    terms = {
        year: map_suppressed_errors(get_term_offered, fails, course, year)
        for year in years.split("+")
    }

    return {
        "terms": terms,
        "fails": fails,
    }


###############################################################################
#                                                                             #
#                             End of Routes                                   #
#                                                                             #
###############################################################################


def unlocked_set(courses_state) -> Set[str]:
    """ Fetch the set of unlocked courses from the courses_state of a getAllUnlocked call """
    return set(course for course in courses_state if courses_state[course]['unlocked'])

def fuzzy_match(course: Tuple[str, str], search_term: str) -> float:
    """ Gives the course a weighting based on the relevance to the search """
    code, title = course

    # either match against a course code, or match many words against the title
    # (not necessarily in the same order as the title)
    search_term = search_term.lower()
    if re.match('[a-z]{4}[0-9]', search_term):
        return fuzz.ratio(code.lower(), search_term) * 10

    return max(fuzz.ratio(code.lower(), search_term),
               sum(fuzz.partial_ratio(title.lower(), word)
                       for word in search_term.split(' ')))

def get_course_info(course: str, year: str | int=LIVE_YEAR) -> Dict:
    """
    Returns the course info for the given course and year.
    If no year is given, the current year is used.
    If the year is not the LIVE_YEAR, then uses legacy information
    """
    return get_course(course) if int(year) == int(LIVE_YEAR) else get_legacy_course(year, course)

def get_term_offered(course: str, year: int | str=LIVE_YEAR) -> List[str]:
    """
    Returns the terms in which the given course is offered, for the given year.
    """
    return get_course_info(course, year).get("terms", [])

