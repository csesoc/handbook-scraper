"""
The driver for our processors. Provide the relevant command line arguments
in order to run the relevant drivers
If you need to  bash this, use:
    python3 -m runprocessors --type data-fix --stage all
"""

import argparse
import subprocess
from sys import exit
from typing import Callable

from data.processors.courses_processing import process_course_data
from data.processors.programs_processing import process_prg_data
from data.processors.specialisations_processing import customise_spn_data

from data.scrapers.courses_formatting import format_course_data
from data.scrapers.courses_scraper import scrape_course_data
from data.scrapers.programs_formatting import format_prg_data
from data.scrapers.programs_scraper import scrape_prg_data
from data.scrapers.gened_scraper import scrape_gened_data
from data.scrapers.specialisations_formatting import format_spn_data
from data.scrapers.specialisations_scraper import scrape_spn_data
from data.scrapers.faculty_code_formatting import format_code_data
from data.scrapers.enrolment_scraper import scrape_enrolment_data

parser = argparse.ArgumentParser()

parser.add_argument(
    "--type",
    type=str,
    help="program, specialisation, course, condition, data-fix, enrolment",
)

parser.add_argument(
    "--stage",
    type=str,
    help="""
            (any) --> all
            program/specialisation/course --> scrape, format, process
            condition --> process, manual, tokenise, parsingErrors, pickle
            cache --> exclusion, handbook_note, mapping, program
            enrolment --> scrape
        """,
)

parser.add_argument(
    "--username",
    type=str,
    help="username (zID) for the enrolment scraper",
    nargs='?',
    default=None,
)

parser.add_argument(
    "--password",
    type=str,
    help="password (zPass) for the enrolment scraper",
    nargs='?',
    default=None,
)

try:
    args = parser.parse_args()
except argparse.ArgumentError:
    parser.print_help()
    exit(0)

def run_manual_fixes():
    """ runs all the manual fix scripts """
    try:
        subprocess.run(["sh", "data/processors/manual_fixes/run_manual_fixes.sh"], check=True)
    except subprocess.CalledProcessError:
        print("Unable to run the 'run_manual_fixes.sh'; exiting with error")
        exit(0)

def run_scrape_enrolment_data():
    """ runs the enrolment scraper """
    if args.username is None or args.password is None:
        print("Please provide a username and password for the enrolment scraper")
    else:
        scrape_enrolment_data(args.username, args.password)


run: dict[str, dict[str, Callable]] = {
    "program": {
        "scrape": scrape_prg_data,
        "format": format_prg_data,
        "process": process_prg_data,
    },
    "specialisation": {
        "scrape": scrape_spn_data,
        "format": format_spn_data,
        "process": customise_spn_data,
    },
    "course": {
        "scrape": scrape_course_data,
        "format": format_course_data,
        "process": process_course_data,
    },
}

if __name__ == "__main__":
    if args.type is None and args.stage is None:
        res = input("did you mean to run all data fixes? [y/N] ")
        if res == "y":
            args.type = "data-fix"
            args.stage = "all"
        else:
            parser.print_help()
            exit()
    if args.type == "data-fix" and args.stage == "all":
        # run all the things except for the scrapers and formatters to deal with code changes
        for t, type in run.items():
            for stage, function in type.items():
                if stage != "scrape":
                    function()

    elif args.stage == "all":
        # Run all the stages from top to bottom
        if args.type in ["program", "specialisation", "course", "gened"]:
            # NOTE: Be careful when using this as this will rerun the scrapers
            res = input(
                f"Careful. You are about to run all stages of {args.type} INCLUDING the scrapers... Enter 'y' if you wish to proceed or 'n' to cancel: "
            )
            if res == "y":
                for s in run[args.type]:
                    run[args.type][s]()
        else:
            # Conditions
            for s in run[args.type]:
                run[args.type][s]()
    else:
        # Run the specific process
        try:
            run[args.type][args.stage]()
        except KeyError:
            print(f"{args.type} and {args.stage} is an invalid combination")
            parser.print_help()

