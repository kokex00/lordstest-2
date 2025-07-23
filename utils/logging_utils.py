"""Logging utilities for bot activities"""

import logging
from datetime import datetime
from app import app, db
from models import BotLog, Server

async def log_command_usage(guild_id: int, user_id: int, username: str, command: str, channel_id: int, details: str = ""):
    """Log command usage to database and send to log channel if configured"""
    
    with app.app_context():
        try:
            # Get server configuration
            server = Server.query.filter_by(guild_id=str(guild_id)).first()
            if not server:
                return
            
            # Create log entry
            log_entry = BotLog(
                server_id=server.id,
                user_id=str(user_id),
                username=username,
                command=command,
                channel_id=str(channel_id),
                details=details
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            # Send to log channel if configured
            if server.log_channel_id:
                try:
                    from bot import bot
                    import discord
                    
                    log_channel = bot.get_channel(int(server.log_channel_id))
                    if log_channel:
                        embed = discord.Embed(
                            title="📝 Command Log",
                            color=0x95a5a6,
                            timestamp=datetime.utcnow()
                        )
                        
                        embed.add_field(name="User", value=f"{username} (`{user_id}`)", inline=True)
                        embed.add_field(name="Command", value=f"`/{command}`", inline=True)
                        embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)
                        
                        if details:
                            embed.add_field(name="Details", value=details, inline=False)
                        
                        embed.set_footer(text="Bot created by kokex | Contact: kokexe")
                        
                        await log_channel.send(embed=embed)
                        
                except Exception as e:
                    logging.error(f"Error sending to log channel: {e}")
            
        except Exception as e:
            logging.error(f"Error logging command usage: {e}")

def get_recent_logs(guild_id: str, limit: int = 50):
    """Get recent logs for a guild"""
    with app.app_context():
        server = Server.query.filter_by(guild_id=guild_id).first()
        if not server:
            return []
        
        logs = BotLog.query.filter_by(server_id=server.id).order_by(BotLog.timestamp.desc()).limit(limit).all()
        return logs
