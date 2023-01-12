# https://stackoverflow.com/q/1976007
FORBIDDEN_FILENAME_CHARS = {
    "<",  # less than
    ">",  # greater than
    ":",  # colon - sometimes works, but is actually NTFS Alternate Data Streams
    '"',  # double quote
    "/",  # forward slash
    "\\",  # backslash
    "|",  # vertical bar or pipe
    "?",  # question mark
    "*",  # asterisk
}


def route_contains_invalid_characters(module_name: str) -> set[str]:
    return set(module_name) - FORBIDDEN_FILENAME_CHARS


def underscore_to_camel_case(word: str) -> str:
    # foo_bar_baz -> FooBarBaz
    return "".join(c.capitalize() or "_" for c in word.split("_"))
