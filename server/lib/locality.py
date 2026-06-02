import re

_NYC_NEIGHBORHOODS = {
    "manhattan", "brooklyn", "queens", "bronx", "staten island",
    "williamsburg", "bushwick", "dumbo", "soho", "tribeca",
    "harlem", "greenpoint", "astoria", "flushing", "bed-stuy",
    "bed stuy", "bedford-stuyvesant", "chelsea", "east village",
    "west village", "lower east side", "les", "upper east side",
    "upper west side", "ues", "uws", "midtown", "financial district",
    "fidi", "chinatown", "little italy", "nolita", "noho",
    "flatiron", "gramercy", "murray hill", "hells kitchen",
    "hell's kitchen", "washington heights", "inwood", "morningside heights",
    "park slope", "crown heights", "prospect heights",
    "fort greene", "cobble hill", "boerum hill", "carroll gardens",
    "red hook", "sunset park", "bay ridge", "bensonhurst",
    "flatbush", "east flatbush", "canarsie", "brighton beach",
    "coney island", "sheepshead bay", "long island city", "lic",
    "jackson heights", "elmhurst", "woodside", "sunnyside",
    "forest hills", "rego park", "jamaica", "bayside",
    "riverdale", "fordham", "pelham bay", "mott haven",
    "hunts point", "south bronx", "st. george", "stapleton",
}

_NYC_CITIES = {"new york", "nyc", "new york city"}

_METRO_AREAS = {
    "jersey city", "hoboken", "newark", "weehawken",
    "long island", "westchester", "yonkers", "white plains",
    "stamford", "new rochelle", "mount vernon",
}

_NYC_PATTERN = re.compile(
    r"\b(?:ny|n\.y\.|new york|nyc)\b", re.IGNORECASE
)


def compute_nyc_score(location: str | None) -> float:
    if not location:
        return 0.0

    loc = location.lower().strip()

    for neighborhood in _NYC_NEIGHBORHOODS:
        if neighborhood in loc:
            return 1.0

    for city in _NYC_CITIES:
        if city in loc:
            return 1.0

    if _NYC_PATTERN.search(loc):
        return 1.0

    for metro in _METRO_AREAS:
        if metro in loc:
            return 0.7

    return 0.0
