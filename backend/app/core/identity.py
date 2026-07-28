def normalize_email(email: str) -> str:
    '''Return the canonical email identity used for lookup and uniqueness.'''
    return email.strip().lower()
