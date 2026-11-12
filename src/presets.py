"""
User Preset Regex Expressions
Regex Stripper (RegexStripper)

========================================================================================
💡 HOW TO ADD YOUR OWN REGEX PRESETS:
----------------------------------------------------------------------------------------
To add a new regular expression to your preset menu, simply add a new dictionary
to the PRESET_EXPRESSIONS list below!

Each entry has:
  - "name": (Required) Descriptive title shown in the list.
  - "expression": (Required) The regex pattern string (use r"..." raw strings).
  - "description": (Optional) Brief summary or example of what it matches.
========================================================================================
"""

from typing import List, Dict

PRESET_EXPRESSIONS: List[Dict[str, str]] = [
    {
        "name": "Strip Phrase tags",
        "expression": r"\{.+?>|<.+?\}",
        "description": "Matches phrase tags like {...> or <...}",
    },
    {
        "name": "Email Addresses",
        "expression": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "description": "Standard email address extraction",
    },
    {
        "name": "Web URLs (HTTP/HTTPS)",
        "expression": r"https?://[^\s/$.?#].[^\s]*",
        "description": "Web hyperlinks starting with http:// or https://",
    },
    {
        "name": "HTML / XML Tags",
        "expression": r"<[^>]+>",
        "description": "Matches all HTML and XML markup tags",
    },
    {
        "name": "Excessive Blank Lines",
        "expression": r"\n\s*\n+",
        "description": "Matches duplicate or redundant blank lines",
    },
    {
        "name": "Trailing Whitespace",
        "expression": r"[ \t]+$",
        "description": "Matches spaces and tabs at the ends of lines",
    },
]

