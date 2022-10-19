"""
API for fetching data about programs and specialisations """
from contextlib import suppress
import functools
import re
from typing import Callable, Dict, List, Mapping, Optional, Tuple, cast

from fastapi import APIRouter, HTTPException

from data.processors.models import (
    CourseContainer,
    Program,
    ProgramContainer,
    Specialisation,
)
from data.utility import data_helpers
from server.database import programsCOL, specialisationsCOL
from server.manual_fixes import apply_manual_fixes
from server.routers.courses import regex_search
from server.routers.model import (
    CourseCodes,
    Courses,
    Programs,
    Structure,
    StructureContainer,
)
from server.routers.utility import get_core_courses

router = APIRouter(
    prefix="/programs",
    tags=["programs"],
)


@router.get("/")
def programs_index() -> str:
    """ sanity test that this file is loaded """
    return "Index of programs"


@router.get(
    "/getPrograms",
    response_model=Programs,
    responses={
        200: {
            "description": "Returns all programs",
            "content": {
                "application/json": {
                    "example": {
                        "programs": {
                            "3502": "Commerce",
                            "3707": "Engineering (Honours)",
                            "3778": "Computer Science",
                            "3970": "Science",
                        }
                    }
                }
            },
        }
    },
)
def get_programs() -> dict[str, dict[str, str]]:
    """ Fetch all the programs the backend knows about in the format of { code: title } """
    return {"programs": {q["code"]: q["title"] for q in programsCOL.find()}}


def convert_subgroup_object_to_courses_dict(object: str, description: str|list[str]) -> Mapping[str, str | list[str]]:
    """ Gets a subgroup object (format laid out in the processor) and fetches the exact courses its referring to """
    if " or " in object and isinstance(description, list):
        return {c: description[index] for index, c in enumerate(object.split(" or "))}
    if not re.match(r"[A-Z]{4}[0-9]{4}", object):
        return regex_search(rf"^{object}")

    return { object: description }

def add_subgroup_container(structure: dict[str, StructureContainer], type: str, container: ProgramContainer | CourseContainer, exceptions: list[str]) -> list[str]:
    """ Returns the added courses """
    # TODO: further standardise non_spec_data to remove these lines:
    title = container.get("title", "")
    if container.get("type") == "gened":
        title = "General Education"
    conditional_type = container.get("type")
    if conditional_type is not None and "rule" in conditional_type:
        type = "Rules"
    structure[type]["content"][title] = {
        "UOC": container.get("credits_to_complete") or 0,
        "courses": functools.reduce(
            lambda rest, current: rest | {
                course: description for course, description
                in convert_subgroup_object_to_courses_dict(current[0], current[1]).items()
                if course not in exceptions
            }, container.get("courses", {}).items(), {}
        ),
        "type": container.get("type", ""),
        "notes": container.get("notes", "") if type == "Rules" else ""
    }
    return list(structure[type]["content"][title]["courses"].keys())

def add_geneds_courses(programCode: str, structure: dict[str, StructureContainer], container: ProgramContainer) -> list[str]:
    """ Returns the added courses """
    if container.get("type") != "gened":
        return []

    item = structure["General"]["content"]["General Education"]
    item["courses"] = {}
    if container.get("courses") is None:
        gen_ed_courses = list(set(get_gen_eds(programCode)["courses"].keys()) - set(sum(
            (
                sum((
                    list(value["courses"].keys())
                    for sub_group, value in spec["content"].items()
                    if 'core' in sub_group.lower()
                ), [])
            for spec_name, spec in structure.items()
            if "Major" in spec_name or "Honours" in spec_name)
        , [])))
        geneds = get_gen_eds(programCode)
        item["courses"] = {course: geneds["courses"][course] for course in gen_ed_courses}


    return list(item["courses"].keys())


def add_specialisation(structure: dict[str, StructureContainer], code: str) -> None:
    """ Add a specialisation to the structure of a getStructure call """
    # in a specialisation, the first container takes priority - no duplicates may exist
    if code.endswith("1"):
        type = "Major"
    elif code.endswith("2"):
        type = "Minor"
    else:
        type = "Honours"

    spnResult = cast(Specialisation | None, specialisationsCOL.find_one({"code": code}))
    type = f"{type} - {code}"
    if not spnResult:
        raise HTTPException(
            status_code=400, detail=f"{code} of type {type} not found")
    structure[type] = {"name": spnResult["name"], "content": {}}
    # NOTE: takes Core Courses are first
    exceptions: list[str] = []
    for cores in filter(lambda a: "Core" in a["title"], spnResult["curriculum"]):
        new = add_subgroup_container(structure, type, cores, exceptions)
        exceptions.extend(new)

    for container in spnResult["curriculum"]:
        if "Core" not in container["title"]:
            add_subgroup_container(structure, type, container, exceptions)

@router.get(
    "/getStructure/{programCode}/{spec}",
    response_model=Structure,
    responses={
        400: { "description": "Uh oh you broke me" },
        200: {
            "description": "Returns the program structure",
            "content": {
                "application/json": {
                    "example": {
                        "Major - COMPS1 - Computer Science": {
                            "name": "Database Systems",
                            "content": {
                                "Core Courses": {
                                    "UOC": 66,
                                    "courses": {
                                        "COMP3821": "Extended Algorithms and Programming Techniques",
                                        "COMP3121": "Algorithms and Programming Techniques",
                                    },
                                },
                                "Computing Electives": {
                                    "UOC": 30,
                                    "courses": {
                                        "ENGG4600": "Engineering Vertically Integrated Project",
                                        "ENGG2600": "Engineering Vertically Integrated Project",
                                    },
                                },
                            },
                            "notes": "Students must take 30 UOC of the following courses.",
                        },
                        "Major - FINSA1 - Finance": {
                            "name": "Finance",
                            "content": {
                                "Core Courses": {
                                    "UOC": 66,
                                    "courses": {
                                        "FINS3121": "Financial Accounting",
                                    },
                                },
                            },
                            "notes": "Students must take 60 UOC of the following courses.",
                        },
                        "Minor - FINSA2 - Finance": {
                            "name": "Finance",
                            "content": {
                                "Prescribed Electives": {
                                    "UOC": 12,
                                    "courses": {
                                        "FINS3616": "International Business Finance",
                                        "FINS3634": "Credit Analysis and Lending",
                                    },
                                },
                                "Core Courses": {
                                    "UOC": 18,
                                    "courses": {
                                        "FINS2613": "Intermediate Business Finance",
                                        "COMM1180": "Value Creation",
                                        "FINS1612": "Capital Markets and Institutions",
                                    },
                                },
                            },
                            "notes": "Students must take 12 UOC of the following courses.",
                        },
                        "General": {
                            "name": "General Program Requirements",
                            "content": {
                                "General Education": {"UOC": 12},
                                "FlexEducation": {"UOC": 6},
                                "BusinessCoreCourses": {
                                    "UOC": 6,
                                    "courses": {"BUSI9999": "How To Business"},
                                },
                            }
                        },
                    }
                }
            }
        }
    }
)
@router.get("/getStructure/{programCode}", response_model=Structure)
def get_structure(
    programCode: str, spec: Optional[str] = None
):
    """ get the structure of a course given specs and program code """
    # TODO: This ugly, use compose instead
    structure: dict[str, StructureContainer] = {}
    structure = add_specialisations(structure, spec)
    structure, uoc = add_program_code_details(structure, programCode)
    structure = add_geneds_to_structure(structure, programCode)
    apply_manual_fixes(structure, programCode)

    return {
        "structure": structure,
        "uoc": uoc,
    }

@router.get("/getStructureCourseList/{programCode}/{spec}", response_model=CourseCodes)
@router.get("/getStructureCourseList/{programCode}", response_model=CourseCodes)
def get_structure_course_list(
        programCode: str, spec: Optional[str]=None
    ):
    """
        Similar to `/getStructure` but, returns a raw list of courses with no further
        nesting or categorisation.
        TODO: Add a test for this.
    """
    structure: dict[str, StructureContainer] = {}
    structure = add_specialisations(structure, spec)
    structure, _ = add_program_code_details(structure, programCode)
    apply_manual_fixes(structure, programCode)

    return {
        "courses": course_list_from_structure(structure),
    }

@router.get(
    "/getGenEds/{programCode}",
    response_model=Courses,
    responses={
        400: {
            "description": "The given program code could not be found in the database",
        },
        200: {
            "description": "Returns all geneds available to a given to the given code",
            "content": {
                "application/json": {
                    "example": {
                        "courses": {
                            "ACTL3142": "Statistical Machine Learning for Risk and Actuarial Applications",
                            "ACTL4305": "Actuarial Data Analytic Applications",
                            "ADAD2610": "Art and Design for Environmental Challenges",
                            "ANAT2521": "Biological Anthropology: Principles and Practices",
                            "ARTS1010": "The Life of Words"
                        }
                    }
                }
            },
        },
    },
)
def get_gen_eds(programCode: str):
    """ fetches gen eds from file """
    all_geneds = data_helpers.read_data("data/scrapers/genedPureRaw.json")[programCode]
    return {"courses" : all_geneds}

@router.get("/getCores/{programCode}/{spec}")
def get_cores(programCode: str, spec: str):
    return get_core_courses(programCode, spec.split('+'))

###############################################################
#                       End of Routes                         #
###############################################################

def course_list_from_structure(structure: dict) -> list[str]:
    """
        Given a formed structure, return the list of courses
        in that structure
    """
    courses = []
    def __recursive_course_search(structure: dict) -> None:
        """
            Recursively search for courses in a structure. Add
            courses found to `courses` object in upper group.
        """
        if not isinstance(structure, (list, dict)):
            return
        for k, v in structure.items():
            with suppress(KeyError):
                if not isinstance(v, dict) or "rule" in v["type"]:
                    continue
            if "courses" in k:
                courses.extend(v.keys())
            __recursive_course_search(v)
        return
    __recursive_course_search(structure)
    return courses

def add_specialisations(structure: dict[str, StructureContainer], spec: Optional[str]) -> dict[str, StructureContainer]:
    """
        Take a string of `+` joined specialisations and add
        them to the structure
    """
    if spec:
        specs = spec.split("+") if "+" in spec else [spec]
        for m in specs:
            add_specialisation(structure, m)
    return structure

def add_program_code_details(structure: dict[str, StructureContainer], programCode: str) -> Tuple[dict[str, StructureContainer], int]:
    """
    Add the details for given program code to the structure.
    Returns:
        - structure
        - uoc (int) associated with the program code.
    """
    programsResult = cast(Optional[Program], programsCOL.find_one({"code": programCode}))
    if not programsResult:
        raise HTTPException(
            status_code=400, detail="Program code was not found")

    structure['General'] = {"name": "General Program Requirements", "content": {}}
    structure['Rules'] = {"name": "General Program Rules", "content": {}}
    return (structure, programsResult["UOC"])

def add_geneds_to_structure(structure: dict[str, StructureContainer], programCode: str) -> dict[str, StructureContainer]:
    """
        Insert geneds of the given programCode into the structure
        provided
    """
    programsResult = cast(Program | None, programsCOL.find_one({"code": programCode}))
    if programsResult is None:
        raise HTTPException(
            status_code=400, detail="Program code was not found")

    with suppress(KeyError):
        for container in programsResult['components']['non_spec_data']:
            add_subgroup_container(structure, "General", container, [])
            if container.get("type") == "gened":
                add_geneds_courses(programCode, structure, container)
    return structure


def compose(*functions: Callable) -> Callable:
    """
        Compose a list of functions into a single function.
        The functions are applied in the order they are given.
    """
    return functools.reduce(lambda f, g: lambda *args, **kwargs: f(g(*args, **kwargs)), functions)

def proto_edges_to_edges(proto_edges: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Take the proto-edges created by calls to `path_from` and convert them into
    a full list of edges of form.
    [
        {
            "source": (str) - course_code, # This is the 'original' value
            "target": (str) - course_code, # This is the value of 'courses'
        }
    ]
    Effectively, turning an adjacency list into a flat list of edges
    """
    edges: List = []
    for proto_edge in proto_edges:
        # Incoming: { original: str,  courses: List[str]}
        # Outcome:  { "src": str, "target": str }
        if not proto_edge or not proto_edge["courses"]:
            continue
        for course in proto_edge["courses"]:
            edges.append({
                    "source": course,
                    "target": proto_edge["original"],
                }
            )
    return edges

def prune_edges(edges: List[Dict[str, str]], courses: List[str]) -> List[Dict[str, str]]:
    """
    Remove edges between vertices that are not in the list of courses provided.
    """
    return [edge for edge in edges if edge["source"] in courses and edge["target"] in courses]

