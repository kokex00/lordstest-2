"""Timezone conversion utilities"""

import pytz
from datetime import datetime
from typing import Dict

def convert_to_timezones(utc_datetime: datetime) -> Dict[str, datetime]:
    """Convert UTC datetime to different timezones"""
    
    # Define timezones
    timezones = {
        'en': pytz.UTC,  # GMT
        'pt': pytz.timezone('America/Sao_Paulo'),  # Brazilian time
        'es': pytz.timezone('Europe/Madrid')  # Spanish time
    }
    
    # Ensure input is UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.UTC.localize(utc_datetime)
    elif utc_datetime.tzinfo != pytz.UTC:
        utc_datetime = utc_datetime.astimezone(pytz.UTC)
    
    # Convert to each timezone
    converted_times = {}
    for lang, tz in timezones.items():
        converted_times[lang] = utc_datetime.astimezone(tz)
    
    return converted_times

def format_time_for_language(dt: datetime, language: str) -> str:
    """Format datetime for specific language"""
    
    formats = {
        'en': '%A, %B %d, %Y at %I:%M %p %Z',
        'pt': '%A, %d de %B de %Y às %H:%M %Z',
        'es': '%A, %d de %B de %Y a las %H:%M %Z'
    }
    
    # Month names in different languages
    month_names = {
        'pt': {
            'January': 'janeiro', 'February': 'fevereiro', 'March': 'março',
            'April': 'abril', 'May': 'maio', 'June': 'junho',
            'July': 'julho', 'August': 'agosto', 'September': 'setembro',
            'October': 'outubro', 'November': 'novembro', 'December': 'dezembro'
        },
        'es': {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
    }
    
    # Day names in different languages
    day_names = {
        'pt': {
            'Monday': 'segunda-feira', 'Tuesday': 'terça-feira', 'Wednesday': 'quarta-feira',
            'Thursday': 'quinta-feira', 'Friday': 'sexta-feira', 'Saturday': 'sábado',
            'Sunday': 'domingo'
        },
        'es': {
            'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
            'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado',
            'Sunday': 'domingo'
        }
    }
    
    format_str = formats.get(language, formats['en'])
    formatted = dt.strftime(format_str)
    
    # Replace English month and day names with local ones
    if language in month_names:
        for english, local in month_names[language].items():
            formatted = formatted.replace(english, local)
    
    if language in day_names:
        for english, local in day_names[language].items():
            formatted = formatted.replace(english, local)
    
    return formatted

def get_current_time_in_timezone(language: str) -> datetime:
    """Get current time in timezone for language"""
    timezones = {
        'en': pytz.UTC,
        'pt': pytz.timezone('America/Sao_Paulo'),
        'es': pytz.timezone('Europe/Madrid')
    }
    
    tz = timezones.get(language, pytz.UTC)
    return datetime.now(tz)
