"""Translation utilities for multi-language support"""

TRANSLATIONS = {
    'en': {
        'match_notification': 'Match Notification',
        'match_teams': 'Teams',
        'match_time': 'Time',
        'match_date': 'Date',
        'translated_message': 'This message has been translated',
        'reminder_10min': 'Match starts in 10 minutes!',
        'reminder_3min': 'Match starts in 3 minutes!',
        'match_ended': 'Match has ended',
        'bot_activity': 'Bot Activity',
        'announcement': 'Announcement',
        'server_info': 'Server Information',
        'private_message': 'Private Message from Server Admin',
        'server': 'Server',
        'from': 'From',
        'moderation_action': 'Moderation Action',
        'member': 'Member',
        'moderator': 'Moderator',
        'reason': 'Reason',
        'duration': 'Duration',
        'role': 'Role',
        'channel': 'Channel',
        'created_by': 'Created by kokex | Contact: kokexe'
    },
    'pt': {
        'match_notification': 'Notificação de Partida',
        'match_teams': 'Equipes',
        'match_time': 'Hora',
        'match_date': 'Data',
        'translated_message': 'Esta mensagem foi traduzida',
        'reminder_10min': 'A partida começa em 10 minutos!',
        'reminder_3min': 'A partida começa em 3 minutos!',
        'match_ended': 'A partida terminou',
        'bot_activity': 'Atividade do Bot',
        'announcement': 'Anúncio',
        'server_info': 'Informações do Servidor',
        'private_message': 'Mensagem Privada do Admin do Servidor',
        'server': 'Servidor',
        'from': 'De',
        'moderation_action': 'Ação de Moderação',
        'member': 'Membro',
        'moderator': 'Moderador',
        'reason': 'Motivo',
        'duration': 'Duração',
        'role': 'Cargo',
        'channel': 'Canal',
        'created_by': 'Criado por kokex | Contato: kokexe'
    },
    'es': {
        'match_notification': 'Notificación de Partido',
        'match_teams': 'Equipos',
        'match_time': 'Hora',
        'match_date': 'Fecha',
        'translated_message': 'Este mensaje ha sido traducido',
        'reminder_10min': '¡El partido comienza en 10 minutos!',
        'reminder_3min': '¡El partido comienza en 3 minutos!',
        'match_ended': 'El partido ha terminado',
        'bot_activity': 'Actividad del Bot',
        'announcement': 'Anuncio',
        'server_info': 'Información del Servidor',
        'private_message': 'Mensaje Privado del Admin del Servidor',
        'server': 'Servidor',
        'from': 'De',
        'moderation_action': 'Acción de Moderación',
        'member': 'Miembro',
        'moderator': 'Moderador',
        'reason': 'Razón',
        'duration': 'Duración',
        'role': 'Rol',
        'channel': 'Canal',
        'created_by': 'Creado por kokex | Contacto: kokexe'
    }
}

def get_translation(key: str, language: str = 'en') -> str:
    """Get translation for a key in specified language"""
    if language not in TRANSLATIONS:
        language = 'en'
    
    return TRANSLATIONS[language].get(key, TRANSLATIONS['en'].get(key, key))

def get_available_languages() -> list:
    """Get list of available language codes"""
    return list(TRANSLATIONS.keys())
