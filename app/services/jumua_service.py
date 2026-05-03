from datetime import datetime

def is_friday():
    return datetime.utcnow().weekday() == 4  # 4 = Friday