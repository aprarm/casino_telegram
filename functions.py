import re
import string
import random
from datetime import datetime, timezone, timedelta


async def get_invoice_from_message(input_string):
    # Извлечение суммы после $
    amount_matches = re.findall(r'\$\s*(\d+(\.\d+)?)', input_string)
    if amount_matches:
        amounts = [float(match[0]) for match in amount_matches]
    else:
        amounts = None
    # Извлечение суммы между скобками
    bracket_matches = re.findall(r'\(\s*(\d+(\.\d+)?)\s*\)', input_string)
    if bracket_matches:
        bracket_amounts = [float(match[0]) for match in bracket_matches]
        amounts.extend(bracket_amounts)

    # Извлечение текста после 💬
    comment_match = re.search(r'💬 (.+)', input_string)
    comment = comment_match.group(1) if comment_match else None
    value = list(amounts)[-1]
    return {'amount': value, 'comment': comment}

def get_date_and_hours():
    moscow_tz = timezone(timedelta(hours=3))  # UTC+3 для Москвы
    this_date = datetime.now(moscow_tz).replace(microsecond=0)
    formatted_date = this_date.strftime("%d.%m.%Y %H:%M:%S")
    return formatted_date

def generate_unique_string(length):
    characters = string.ascii_letters + string.digits
    unique_string = ''.join(random.choice(characters) for _ in range(length))
    return unique_string

def apply_percentage(number, percentage):
    if number is not None and percentage is not None:
        result = number + (percentage / 100 * number)
        return result
    else:
        return None