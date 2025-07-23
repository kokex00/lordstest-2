"""Dashboard routes for web interface"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
from models import Server, Match, BotLog
from app import db
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    """Main dashboard page"""
    # Get statistics
    total_servers = Server.query.count()
    active_matches = Match.query.filter_by(is_active=True).count()
    recent_logs = BotLog.query.order_by(BotLog.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html', 
                         total_servers=total_servers,
                         active_matches=active_matches,
                         recent_logs=recent_logs)

@dashboard_bp.route('/servers')
def servers():
    """Servers management page"""
    servers = Server.query.all()
    return render_template('servers.html', servers=servers)

@dashboard_bp.route('/matches')
def matches():
    """Matches overview page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    matches = Match.query.order_by(Match.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('matches.html', matches=matches)

@dashboard_bp.route('/logs')
def logs():
    """Logs viewer page"""
    page = request.args.get('page', 1, type=int)
    guild_id = request.args.get('guild_id', '')
    per_page = 50
    
    query = BotLog.query
    
    if guild_id:
        server = Server.query.filter_by(guild_id=guild_id).first()
        if server:
            query = query.filter_by(server_id=server.id)
    
    logs = query.order_by(BotLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    servers = Server.query.all()
    
    return render_template('logs.html', logs=logs, servers=servers, selected_guild=guild_id)

@dashboard_bp.route('/server/<guild_id>')
def server_detail(guild_id):
    """Server detail page"""
    server = Server.query.filter_by(guild_id=guild_id).first_or_404()
    
    # Get server statistics
    active_matches = Match.query.filter_by(server_id=server.id, is_active=True).count()
    total_matches = Match.query.filter_by(server_id=server.id).count()
    recent_logs = BotLog.query.filter_by(server_id=server.id).order_by(BotLog.timestamp.desc()).limit(5).all()
    
    # Get allowed channels
    allowed_channels = []
    if server.allowed_channels:
        try:
            allowed_channels = json.loads(server.allowed_channels)
        except:
            allowed_channels = []
    
    return render_template('server_detail.html', 
                         server=server,
                         active_matches=active_matches,
                         total_matches=total_matches,
                         recent_logs=recent_logs,
                         allowed_channels=allowed_channels)

@dashboard_bp.route('/stats')
def stats():
    """Statistics page"""
    # Calculate various statistics
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    stats_data = {
        'total_servers': Server.query.count(),
        'total_matches': Match.query.count(),
        'active_matches': Match.query.filter_by(is_active=True).count(),
        'matches_this_week': Match.query.filter(Match.created_at >= week_ago).count(),
        'matches_this_month': Match.query.filter(Match.created_at >= month_ago).count(),
        'total_logs': BotLog.query.count(),
        'logs_this_week': BotLog.query.filter(BotLog.timestamp >= week_ago).count(),
    }
    
    # Get top commands
    from sqlalchemy import func
    top_commands = db.session.query(
        BotLog.command,
        func.count(BotLog.command).label('count')
    ).group_by(BotLog.command).order_by(func.count(BotLog.command).desc()).limit(10).all()
    
    # Get activity data for charts
    activity_data = []
    for i in range(7):
        date = now - timedelta(days=i)
        day_logs = BotLog.query.filter(
            func.date(BotLog.timestamp) == date.date()
        ).count()
        activity_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'logs': day_logs
        })
    
    return render_template('stats.html', 
                         stats=stats_data,
                         top_commands=top_commands,
                         activity_data=activity_data)

@dashboard_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@dashboard_bp.route('/support')
def support():
    """Support page with contact information"""
    support_info = {
        'creator': 'kokex',
        'contact': 'kokexe',
        'discord_id': '1215053388404756580',
        'bot_version': '1.0.0',
        'features': [
            'Match scheduling with automatic reminders',
            'Multi-language support (English, Portuguese, Spanish)', 
            'Comprehensive moderation tools',
            'Channel management commands',
            'Role and nickname management',
            'Private messaging with translation',
            'Activity logging and monitoring',
            'Web dashboard with statistics'
        ]
    }
    return render_template('support.html', support=support_info)
