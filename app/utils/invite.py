import random
import string

def generate_invite_code(length=8):
    return ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=length)
    )