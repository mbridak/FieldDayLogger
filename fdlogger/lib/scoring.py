"""Field Day scoring helpers."""


def calculate_score(cw_contacts, phone_contacts, digital_contacts, qrp, altpower):
    """Return total score and base score for the supplied contact counts."""
    base_score = (int(cw_contacts) * 2) + int(phone_contacts) + (
        int(digital_contacts) * 2
    )
    multiplier = 2
    if qrp and altpower:
        multiplier = 5
    return base_score * multiplier, base_score
