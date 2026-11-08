# Synthetic practice-facilitation field notes for the subagent demo -------------
# All practices, people, and events are invented. Edit or add notes freely;
# just add a matching entry to GOLD so the evaluation can score it.

CODEBOOK = {
    "LEADERSHIP_ENGAGEMENT": "Practice leaders' involvement in, support for, or commitment to the program.",
    "AVAILABLE_RESOURCES": "Staff time, staffing levels, equipment, or money available for the program.",
    "EHR_TECHNOLOGY": "The EHR, IT support, templates, integrations, or other technology.",
    "STAFF_KNOWLEDGE_BELIEFS": "Staff knowledge, attitudes, skepticism, enthusiasm, or training needs.",
    "PATIENT_NEEDS": "Patient barriers, resources, language, technology access, or preferences.",
}

NOTES = {
    "N01": (
        "Visit 3/4/26 at Riverside Family Medicine. Met with the office manager and two MAs. "
        "The medical director joined for the first 10 minutes and said diabetes outcomes are "
        "a top priority this year. Reviewed the CGM workflow draft. The MAs said they don't "
        "have time during rooming to start sensors, and one asked whether CGM data even "
        "changes treatment. Agreed to pilot sensor starts on Thursday afternoons. Next visit "
        "in two weeks."
    ),
    "N02": (
        "Visit 3/11/26 at Mesa Internal Medicine. The EHR template for CGM reports still isn't "
        "built; IT says it's in the queue behind other requests. Staff are scanning PDF reports "
        "into the chart, which takes about 15 minutes each. The practice lead seemed frustrated "
        "but committed to keep going."
    ),
    "N03": (
        "Visit 3/18/26 at Riverside Family Medicine. Pilot started, with five patients started "
        "on CGM. One patient called the next day reporting she felt dizzy and fell at home after "
        "her insulin dose was adjusted based on her readings; she was seen in urgent care and "
        "released. The clinician is reviewing. Staff are otherwise positive about the workflow."
    ),
    "N04": (
        "Visit 3/20/26 at Foothills Community Clinic. Many patients here have limited smartphone "
        "access, so the app-based CGM reader won't work for them. Discussed loaner readers. "
        "Spanish-language patient materials are needed. Front desk staff asked for training on "
        "how to explain the program to patients."
    ),
    "N05": (
        "Visit 4/1/26 at Mesa Internal Medicine. Two patients were enrolled before their consent "
        "forms were signed; the coordinator caught it the same week and contacted the study team. "
        "The practice paused new enrollments until the consent process is fixed. Scheduled a call "
        "with the study coordinator for Friday."
    ),
    "N06": (
        "Visit 4/8/26 at Foothills Community Clinic. The new medical director is enthusiastic and "
        "added CGM review to the monthly quality meeting agenda. The EHR integration went live "
        "last week, and MAs say pulling reports now takes under a minute. Will check sustainment "
        "at the 3-month visit."
    ),
}

# Gold standard: how a human coder labeled each note ------------------------------
GOLD = {
    "N01": {"codes": {"LEADERSHIP_ENGAGEMENT", "AVAILABLE_RESOURCES", "STAFF_KNOWLEDGE_BELIEFS"},
            "safety": False, "follow_up": True},
    "N02": {"codes": {"EHR_TECHNOLOGY", "AVAILABLE_RESOURCES", "LEADERSHIP_ENGAGEMENT"},
            "safety": False, "follow_up": False},
    "N03": {"codes": {"STAFF_KNOWLEDGE_BELIEFS"},
            "safety": True, "follow_up": False},
    "N04": {"codes": {"PATIENT_NEEDS", "STAFF_KNOWLEDGE_BELIEFS"},
            "safety": False, "follow_up": False},
    "N05": {"codes": set(),
            "safety": True, "follow_up": True},
    "N06": {"codes": {"LEADERSHIP_ENGAGEMENT", "EHR_TECHNOLOGY"},
            "safety": False, "follow_up": True},
}
