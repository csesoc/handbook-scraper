"""
Is the configuration file for `cache.py`
"""

# Config for mapping course -> code
# This json has two fields. `"codes"` and `"keywords"`
# "codes" is a list of valid codes
# "keyword_mapping" is a dict where the key is a keyword and the value
# is the codes that keyword maps to
CACHE_CONFIG = "cache/cache_config.json"

# INPUT SOURCES
COURSES_PROCESSED_FILE = "data/final_data/coursesProcessed.json"

PROGRAMS_FORMATTED_FILE = "data/scrapers/programsFormattedRaw.json"

CACHED_EXCLUSIONS_FILE = "data/final_data/exclusions.json"

CACHED_EQUIVALENTS_FILE = "data/final_data/equivalents.json"

CONDITIONS_PROCESSED_FILE = "data/final_data/conditionsProcessed.json"


# OUTPUT SOURCES
CACHED_WARNINGS_FILE = "data/final_data/handbook_note.json"

MAPPINGS_FILE = "data/final_data/mappings.json"

COURSE_MAPPINGS_FILE = "data/final_data/courseMappings.json"

PROGRAM_MAPPINGS_FILE = "data/final_data/programMappings.json"
