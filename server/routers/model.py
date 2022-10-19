""" model for interacting with the FE """
# pylint: disable=missing-class-docstring
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel

class Programs(BaseModel):
    programs: dict


class Specialisations(BaseModel):
    spec: dict[str, dict] # cant do more specific because NotRequired doesnt work


class ProgramCourses(BaseModel):
    courses: dict[str, str]


class CourseDetails(BaseModel):
    title: str
    code: str
    UOC: int
    level: int
    description: str
    study_level: str
    school: Optional[str]
    campus: str
    equivalents: dict[str, str]
    raw_requirements: str
    exclusions: dict[str, Literal[1]]
    terms: list[str]
    gen_ed: bool
    is_legacy: bool
    is_multiterm: Optional[bool]


class ContainerContent(TypedDict):
    UOC: int
    courses: dict[str, str | list[str]]
    type: str
    notes: str

class StructureContainer(TypedDict):
    name: str
    content: dict[str, ContainerContent]

class Structure(BaseModel):
    structure: dict[str, StructureContainer]
    uoc: int


class UserData(BaseModel):
    program: str
    specialisations: dict
    courses: dict


class CourseState(BaseModel):
    is_accurate: bool
    unlocked: bool
    handbook_note: str
    warnings: list


class ValidCourseState(BaseModel):
    is_accurate: bool
    unlocked: bool
    handbook_note: str
    warnings: list
    supressed: bool


class CoursesState(BaseModel):
    courses_state: dict[str, CourseState] = {}


class ValidCoursesState(BaseModel):
    courses_state: dict[str, ValidCourseState] = {}


class CoursesUnlockedWhenTaken (BaseModel):
    direct_unlock: list[str]
    indirect_unlock: list[str]


class CourseTypeState(BaseModel):
    is_accurate: bool
    unlocked: bool
    handbook_note: str
    warnings: list[str]
    course_type: list[str]


class CoursesTypeState(BaseModel):
    courses_state: dict[str, CourseTypeState] = {}


class MostRecentPastTerm(TypedDict):
    Y: int
    T: int


class ValidPlannerData(BaseModel):
    program: str
    specialisations: list[str]
    plan: list[list[dict[str, tuple[int, int | None]]]]
    mostRecentPastTerm: MostRecentPastTerm

class PlannerData(BaseModel):
    program: str
    specialisations: list[str]
    plan: list[list[dict[str,  None | list[int | None]]]]
    mostRecentPastTerm: MostRecentPastTerm
    class Config:
        schema_extra = {
            "example": {
                "program": "3707",
                "specialisations": ["COMPA1"],
                "year": 1,
                "plan": [
                    [
                        {},
                        {
                            "COMP1511": [6, None],
                            "MATH1141": [6, None],
                            "MATH1081": [6, None],
                        },
                        {
                            "COMP1521": [6, None],
                            "COMP9444": [6, None],
                        },
                        {
                            "COMP2521": [6, None],
                            "MATH1241": [6, None],
                            "COMP3331": [6, None],
                        },
                    ],
                    [
                        {},
                        {
                            "COMP1531": [6, None],
                            "COMP6080": [6, None],
                            "COMP3821": [6, None],
                        },
                    ],
                ],
                "mostRecentPastTerm": {
                    "Y": 1,
                    "T": 0,
                },
            }
        }

class CourseCodes(BaseModel):
    courses: list[str]

class Courses(BaseModel):
    courses: dict[str, str] = {}

class CoursesPath(BaseModel):
    original: str
    courses: list[str]


class Description(BaseModel):
    description: str


class SpecialisationTypes(BaseModel):
    types: list[str]

class Graph(BaseModel):
    edges: list[dict[str, str]]
    courses: list[str]

class TermsList(BaseModel):
    terms: Optional[dict[str, Optional[list[str]]]]
    # Actually tuple(str, fastapi.exceptions.HTTPException)
    fails: Optional[list[tuple]]
