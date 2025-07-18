"""
Clinical Assessment Data Module - Barthel ADL Index & Lawton IADL Scale
=======================================================================
Contains exact official question wording, answer options, and scoring
for Barthel Index (ADL) and Lawton IADL as per published reference standards.

Each question entry includes:
- code: unique question code
- domain: functional domain (for both table and graph linking)
- sequence: question order within assessment
- text: official question wording
- description: clarifies intent/context
- assessment_type: "ADL" or "IADL"
- answers: list of answer dicts (text, clinical_score, order)
"""

from typing import Dict, List, Any

# IADL - Lawton (always first)
LAWTON_IADL_QUESTIONS = [
    {
        "code": "LAWTON_TELEPHONE",
        "domain": "telephone",
        "sequence": 1,
        "text": "Ability to Use Telephone",
        "description": "Assessment of telephone usage ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Does not use telephone at all", "clinical_score": 0, "order": 1},
            {"text": "Operates telephone on own initiative; looks up and dials numbers", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_SHOPPING",
        "domain": "shopping",
        "sequence": 2,
        "text": "Shopping",
        "description": "Assessment of shopping ability for necessities",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help with all shopping", "clinical_score": 0, "order": 1},
            {"text": "Takes care of all shopping needs independently", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_FOOD_PREP",
        "domain": "food_preparation",
        "sequence": 3,
        "text": "Food Preparation",
        "description": "Assessment of meal planning and preparation ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help with meal preparation", "clinical_score": 0, "order": 1},
            {"text": "Plans, prepares, and serves meals independently", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_HOUSEKEEPING",
        "domain": "housekeeping",
        "sequence": 4,
        "text": "Housekeeping",
        "description": "Assessment of home maintenance ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help with all home maintenance", "clinical_score": 0, "order": 1},
            {"text": "Maintains house alone with occasional help", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_LAUNDRY",
        "domain": "laundry",
        "sequence": 5,
        "text": "Laundry",
        "description": "Assessment of personal laundry ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help with all laundry", "clinical_score": 0, "order": 1},
            {"text": "Does personal laundry completely", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_TRANSPORTATION",
        "domain": "transportation",
        "sequence": 6,
        "text": "Mode of Transportation",
        "description": "Assessment of transportation arrangement ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help or is unable to travel", "clinical_score": 0, "order": 1},
            {"text": "Travels independently", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_MEDICATION",
        "domain": "medication",
        "sequence": 7,
        "text": "Responsibility for Own Medications",
        "description": "Assessment of medication management ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help with medications", "clinical_score": 0, "order": 1},
            {"text": "Takes medications independently", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "LAWTON_FINANCES",
        "domain": "finances",
        "sequence": 8,
        "text": "Ability to Handle Finances",
        "description": "Assessment of financial management ability",
        "assessment_type": "IADL",
        "answers": [
            {"text": "Needs help with finances", "clinical_score": 0, "order": 1},
            {"text": "Manages financial matters independently", "clinical_score": 1, "order": 2}
        ]
    }
]

# ADL - Barthel
BARTHEL_ADL_QUESTIONS = [
    {
        "code": "BARTHEL_BOWELS",
        "domain": "bowels",
        "sequence": 1,
        "text": "Bowel control",
        "description": "Assessment of bowel continence over the past week",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Incontinent (or needs to be given enemata)", "clinical_score": 0, "order": 1},
            {"text": "Occasional accident (once/week)", "clinical_score": 1, "order": 2},
            {"text": "Continent", "clinical_score": 2, "order": 3}
        ]
    },
    {
        "code": "BARTHEL_BLADDER",
        "domain": "bladder",
        "sequence": 2,
        "text": "Bladder control",
        "description": "Assessment of bladder continence over the past week",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Incontinent, or catheterized and unable to manage", "clinical_score": 0, "order": 1},
            {"text": "Occasional accident (max. once per 24 hours)", "clinical_score": 1, "order": 2},
            {"text": "Continent (for over 7 days)", "clinical_score": 2, "order": 3}
        ]
    },
    {
        "code": "BARTHEL_GROOMING",
        "domain": "grooming",
        "sequence": 3,
        "text": "Grooming",
        "description": "Personal hygiene including teeth, hair, shaving, washing face",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Needs help with personal care", "clinical_score": 0, "order": 1},
            {"text": "Independent (face/hair/teeth/shaving, implements provided)", "clinical_score": 1, "order": 2}
        ]
    },
    {
        "code": "BARTHEL_TOILET_USE",
        "domain": "toilet_use",
        "sequence": 4,
        "text": "Toilet use",
        "description": "Ability to reach toilet, undress, clean self, dress, and leave",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Dependent", "clinical_score": 0, "order": 1},
            {"text": "Needs some help, but can do something alone", "clinical_score": 1, "order": 2},
            {"text": "Independent (on/off, dressing, wiping)", "clinical_score": 2, "order": 3}
        ]
    },
    {
        "code": "BARTHEL_FEEDING",
        "domain": "feeding",
        "sequence": 5,
        "text": "Feeding",
        "description": "Ability to eat any normal food (food cooked and served by others)",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Unable", "clinical_score": 0, "order": 1},
            {"text": "Needs help cutting, spreading butter, etc.", "clinical_score": 1, "order": 2},
            {"text": "Independent (food provided within reach)", "clinical_score": 2, "order": 3}
        ]
    },
    {
        "code": "BARTHEL_TRANSFERS",
        "domain": "transfers",
        "sequence": 6,
        "text": "Transfer (bed to chair and back)",
        "description": "Ability to move from bed to chair and back",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Unable – no sitting balance", "clinical_score": 0, "order": 1},
            {"text": "Major help (one or two people, physical), can sit", "clinical_score": 1, "order": 2},
            {"text": "Minor help (verbal or physical)", "clinical_score": 2, "order": 3},
            {"text": "Independent", "clinical_score": 3, "order": 4}
        ]
    },
    {
        "code": "BARTHEL_MOBILITY",
        "domain": "mobility",
        "sequence": 7,
        "text": "Mobility",
        "description": "Mobility about house/ward, indoors (may use aid)",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Immobile", "clinical_score": 0, "order": 1},
            {"text": "Wheelchair independent (including corners, etc.)", "clinical_score": 1, "order": 2},
            {"text": "Walks with help of one person (verbal or physical)", "clinical_score": 2, "order": 3},
            {"text": "Independent (may use aid, e.g., stick)", "clinical_score": 3, "order": 4}
        ]
    },
    {
        "code": "BARTHEL_DRESSING",
        "domain": "dressing",
        "sequence": 8,
        "text": "Dressing",
        "description": "Ability to select and put on all clothes (may be adapted)",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Dependent", "clinical_score": 0, "order": 1},
            {"text": "Needs help, but can do about half unaided", "clinical_score": 1, "order": 2},
            {"text": "Independent (including buttons, zips, laces, etc.)", "clinical_score": 2, "order": 3}
        ]
    },
    {
        "code": "BARTHEL_STAIRS",
        "domain": "stairs",
        "sequence": 9,
        "text": "Stairs",
        "description": "Ability to go up and down stairs (must carry any walking aid used)",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Unable", "clinical_score": 0, "order": 1},
            {"text": "Needs help (verbal, physical, carrying aid)", "clinical_score": 1, "order": 2},
            {"text": "Independent up and down", "clinical_score": 2, "order": 3}
        ]
    },
    {
        "code": "BARTHEL_BATHING",
        "domain": "bathing",
        "sequence": 10,
        "text": "Bathing",
        "description": "Ability to get in and out unsupervised and wash self",
        "assessment_type": "ADL",
        "answers": [
            {"text": "Dependent", "clinical_score": 0, "order": 1},
            {"text": "Independent (or in shower)", "clinical_score": 1, "order": 2}
        ]
    }
]

def get_iadl_questions() -> List[Dict[str, Any]]:
    """Returns Lawton IADL questions, in sequence order."""
    return sorted(LAWTON_IADL_QUESTIONS, key=lambda q: q["sequence"])

def get_adl_questions() -> List[Dict[str, Any]]:
    """Returns Barthel ADL questions, in sequence order."""
    return sorted(BARTHEL_ADL_QUESTIONS, key=lambda q: q["sequence"])

def get_all_questions() -> List[Dict[str, Any]]:
    """Returns all questions, IADL first (sequence), then ADL (sequence)."""
    return get_iadl_questions() + get_adl_questions()
