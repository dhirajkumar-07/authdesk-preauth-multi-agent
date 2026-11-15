import re
def procedure(t):
    t = t.lower()
    rules = [("cosmetic", r"rhinoplasty|cosmetic|appearance|nose shape"), ("experimental", r"experimental|investigational"),
             ("bariatric", r"bariatric"), ("chemo", r"chemotherapy"), ("tkr", r"total knee replacement"),
             ("arthroscopy", r"arthroscopy"), ("knee_surgery", r"knee surgery"), ("mri", r"\bmri\b"), ("ct", r"\bct\b")]
    for k, p in rules:
        if re.search(p, t): return k
    return "unknown"
MISSING = r"\bno (imaging|history|details)\b|not provided|no details"
