"""API routes for bot data"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models import Server, Match, BotLog
from app import db
from sqlalchemy import func

api_bp = Blueprint('api', __name__)

@api_bp.route('/stats')
def get_stats():
    """Get basic statistics"""
    stats = {
        'servers': Server.query.count(),
        'matches': Match.query.count(),
        'active_matches': Match.query.filter_by(is_active=True).count(),
        'logs': BotLog.query.count()
    }
    return jsonify(stats)

@api_bp.route('/activity')
def get_activity():
    """Get activity data for charts"""
    days = request.args.get('days', 7, type=int)
    now = datetime.utcnow()
    
    activity_data = []
    for i in range(days):
        date = now - timedelta(days=i)
        day_logs = BotLog.query.filter(
            func.date(BotLog.timestamp) == date.date()
        ).count()
        activity_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'logs': day_logs
        })
    
    return jsonify(activity_data)

@api_bp.route('/commands')
def get_top_commands():
    """Get top commands usage"""
    limit = request.args.get('limit', 10, type=int)
    
    top_commands = db.session.query(
        BotLog.command,
        func.count(BotLog.command).label('count')
    ).group_by(BotLog.command).order_by(func.count(BotLog.command).desc()).limit(limit).all()
    
    return jsonify([{
        'command': cmd[0],
        'count': cmd[1]
    } for cmd in top_commands])

@api_bp.route('/matches/upcoming')
def get_upcoming_matches():
    """Get upcoming matches"""
    limit = request.args.get('limit', 10, type=int)
    now = datetime.utcnow()
    
    matches = Match.query.filter(
        Match.match_date > now,
        Match.is_active == True
    ).order_by(Match.match_date).limit(limit).all()
    
    return jsonify([{
        'id': match.id,
        'team1': match.team1,
        'team2': match.team2,
        'match_date': match.match_date.isoformat(),
        'server': match.server.guild_name
    } for match in matches])

@api_bp.route('/server/<guild_id>/stats')
def get_server_stats(guild_id):
    """Get statistics for a specific server"""
    server = Server.query.filter_by(guild_id=guild_id).first()
    if not server:
        return jsonify({'error': 'Server not found'}), 404
    
    stats = {
        'server_name': server.guild_name,
        'total_matches': Match.query.filter_by(server_id=server.id).count(),
        'active_matches': Match.query.filter_by(server_id=server.id, is_active=True).count(),
        'total_logs': BotLog.query.filter_by(server_id=server.id).count(),
        'has_log_channel': bool(server.log_channel_id),
        'has_activity_channel': bool(server.activity_channel_id),
        'restricted_channels': bool(server.allowed_channels)
    }
    
    return jsonify(stats)

@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })
