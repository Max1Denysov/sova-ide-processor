import datetime


def generate_mktemp_pattern(now=None):

    if now is None:
        now = datetime.datetime.now()

    now_str = now.strftime("%Y%m%d-%H%M%S")

    return f"arm_{now_str}_XXXXXXXX"
