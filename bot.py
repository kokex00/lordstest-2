import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import discord
from discord.ext import commands, tasks
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import app, db
from models import Server, Match, MatchReminder, BotLog
from utils.translations import get_translation, get_available_languages
from utils.timezone_utils import convert_to_timezones, format_time_for_language
from utils.logging_utils import log_command_usage

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    logging.error("DISCORD_TOKEN environment variable not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
scheduler = AsyncIOScheduler()

class TranslationView(discord.ui.View):
    def __init__(self, original_embed, original_language='en'):
        super().__init__(timeout=300)
        self.original_embed = original_embed
        self.original_language = original_language
        
        # Add translation buttons
        languages = [
            ('🇺🇸', 'en', 'English'),
            ('🇵🇹', 'pt', 'Português'),
            ('🇪🇸', 'es', 'Español')
        ]
        
        for emoji, lang_code, lang_name in languages:
            if lang_code != original_language:
                button = discord.ui.Button(
                    emoji=emoji,
                    label=lang_name,
                    custom_id=f'translate_{lang_code}'
                )
                button.callback = self.create_translation_callback(lang_code)
                self.add_item(button)
    
    def create_translation_callback(self, target_language):
        async def translation_callback(interaction):
            try:
                # Create translated embed
                translated_embed = discord.Embed(
                    title=get_translation('match_notification', target_language),
                    color=0x00ff00
                )
                
                # Copy and translate fields
                for field in self.original_embed.fields:
                    field_name = field.name
                    field_value = field.value
                    
                    # Translate common field names
                    if 'vs' in field_name.lower():
                        field_name = get_translation('match_teams', target_language)
                    elif 'time' in field_name.lower() or 'hora' in field_name.lower():
                        field_name = get_translation('match_time', target_language)
                    elif 'date' in field_name.lower() or 'fecha' in field_name.lower():
                        field_name = get_translation('match_date', target_language)
                    
                    translated_embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=field.inline
                    )
                
                translated_embed.set_footer(
                    text=get_translation('translated_message', target_language)
                )
                
                await interaction.response.edit_message(
                    embed=translated_embed,
                    view=TranslationView(self.original_embed, target_language)
                )
            except Exception as e:
                logging.error(f"Translation error: {e}")
                await interaction.response.send_message(
                    "Translation failed. Please try again.", 
                    ephemeral=True
                )
        
        return translation_callback

@bot.event
async def on_ready():
    logging.info(f'{bot.user} has connected to Discord!')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="Server Management | Made by kokex | Dashboard: tinyurl.com/kokex-bot"))
    
    # Start the scheduler
    scheduler.start()
    
    # Start reminder checking task
    check_reminders.start()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

@bot.event
async def on_guild_join(guild):
    with app.app_context():
        # Create server entry
        server = Server(
            guild_id=str(guild.id),
            guild_name=guild.name
        )
        db.session.add(server)
        db.session.commit()
        logging.info(f"Added new server: {guild.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        # Skip logging bot's own messages to avoid spam
        return
    
    # Process regular user messages
    await bot.process_commands(message)

def check_channel_permissions(guild_id: str, channel_id: str) -> bool:
    """Check if bot is allowed to work in this channel"""
    with app.app_context():
        server = Server.query.filter_by(guild_id=guild_id).first()
        if not server or not server.allowed_channels:
            return True  # If no restrictions, allow all channels
        
        allowed_channels = json.loads(server.allowed_channels)
        return channel_id in allowed_channels

@bot.tree.command(name="setup", description="Setup the bot for this server")
@discord.app_commands.describe(
    log_channel="Channel for bot logs",
    activity_channel="Channel for bot activity notifications"
)
async def setup_command(
    interaction: discord.Interaction,
    log_channel: Optional[discord.TextChannel] = None,
    activity_channel: Optional[discord.TextChannel] = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You need administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    with app.app_context():
        server = Server.query.filter_by(guild_id=str(interaction.guild.id)).first()
        if not server:
            server = Server(
                guild_id=str(interaction.guild.id),
                guild_name=interaction.guild.name
            )
            db.session.add(server)
        
        if log_channel:
            server.log_channel_id = str(log_channel.id)
        if activity_channel:
            server.activity_channel_id = str(activity_channel.id)
        
        db.session.commit()
        
        # Log this command
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "setup", interaction.channel.id, f"log: {log_channel}, activity: {activity_channel}"
        )
    
    embed = discord.Embed(
        title="✅ Server Setup Complete",
        color=0x00ff00
    )
    
    if log_channel:
        embed.add_field(name="Log Channel", value=log_channel.mention, inline=True)
    if activity_channel:
        embed.add_field(name="Activity Channel", value=activity_channel.mention, inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_channels", description="Set allowed channels for bot commands")
@discord.app_commands.describe(channels="Channels where bot commands are allowed")
async def set_channels_command(interaction: discord.Interaction, channels: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You need administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    # Parse channel mentions
    channel_ids = []
    for word in channels.split():
        if word.startswith('<#') and word.endswith('>'):
            channel_id = word[2:-1]
            channel_ids.append(channel_id)
    
    if not channel_ids:
        await interaction.response.send_message(
            "❌ Please mention valid channels.",
            ephemeral=True
        )
        return
    
    with app.app_context():
        server = Server.query.filter_by(guild_id=str(interaction.guild.id)).first()
        if not server:
            server = Server(
                guild_id=str(interaction.guild.id),
                guild_name=interaction.guild.name
            )
            db.session.add(server)
        
        server.allowed_channels = json.dumps(channel_ids)
        db.session.commit()
        
        # Log this command
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "set_channels", interaction.channel.id, f"channels: {len(channel_ids)}"
        )
    
    channel_mentions = [f"<#{cid}>" for cid in channel_ids]
    embed = discord.Embed(
        title="✅ Allowed Channels Updated",
        description=f"Bot commands are now restricted to: {', '.join(channel_mentions)}",
        color=0x00ff00
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="create_match", description="Create a new match")
@discord.app_commands.describe(
    team1="First team (can mention roles)",
    team2="Second team (can mention roles)", 
    day="Day of the match (1-31)",
    hour="Hour of the match (0-23)",
    minute="Minute of the match (0-59)"
)
async def create_match_command(
    interaction: discord.Interaction,
    team1: str,
    team2: str,
    day: int,
    hour: int = 20,
    minute: int = 0
):
    if not check_channel_permissions(str(interaction.guild.id), str(interaction.channel.id)):
        await interaction.response.send_message(
            "❌ Bot commands are not allowed in this channel.",
            ephemeral=True
        )
        return
    
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need manage messages permission to create matches.",
            ephemeral=True
        )
        return
    
    try:
        # Create match date (current month and year)
        now = datetime.utcnow()
        match_date = datetime(now.year, now.month, day, hour, minute)
        
        # If the date is in the past, move to next month
        if match_date < now:
            if now.month == 12:
                match_date = match_date.replace(year=now.year + 1, month=1)
            else:
                match_date = match_date.replace(month=now.month + 1)
        
        # Extract role mentions
        role_mentions = []
        import re
        role_pattern = r'<@&(\d+)>'
        
        for match in re.finditer(role_pattern, team1 + ' ' + team2):
            role_mentions.append(match.group(1))
        
        with app.app_context():
            # Create match
            match = Match(
                server_id=None,  # Will be set after getting server
                team1=team1,
                team2=team2,
                match_date=match_date,
                role_mentions=json.dumps(role_mentions),
                channel_id=str(interaction.channel.id),
                created_by=str(interaction.user.id)
            )
            
            # Get or create server
            server = Server.query.filter_by(guild_id=str(interaction.guild.id)).first()
            if not server:
                server = Server(
                    guild_id=str(interaction.guild.id),
                    guild_name=interaction.guild.name
                )
                db.session.add(server)
                db.session.commit()
            
            match.server_id = server.id
            db.session.add(match)
            db.session.commit()
            
            # Create reminders
            reminder_10min = MatchReminder(
                match_id=match.id,
                reminder_time=match_date - timedelta(minutes=10),
                reminder_type='10min'
            )
            reminder_3min = MatchReminder(
                match_id=match.id,
                reminder_time=match_date - timedelta(minutes=3),
                reminder_type='3min'
            )
            
            db.session.add(reminder_10min)
            db.session.add(reminder_3min)
            db.session.commit()
            
            match_id = match.id
            
            # Log this command
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "create_match", interaction.channel.id, f"{team1} vs {team2}"
            )
        
        # Convert to different timezones
        time_zones = convert_to_timezones(match_date)
        
        # Create embed
        embed = discord.Embed(
            title="⚽ New Match Created",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="🆚 Teams", value=f"{team1} vs {team2}", inline=False)
        embed.add_field(name="🕐 Times", value=f"""
🇺🇸 **English (GMT):** {format_time_for_language(time_zones['en'], 'en')}
🇵🇹 **Português:** {format_time_for_language(time_zones['pt'], 'pt')}
🇪🇸 **Español:** {format_time_for_language(time_zones['es'], 'es')}
        """, inline=False)
        
        embed.add_field(name="📝 Match ID", value=f"`{match_id}`", inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        await interaction.response.send_message(embed=embed)
        
        # Send DMs to mentioned roles
        if role_mentions:
            await send_match_notifications(interaction.guild, role_mentions, embed, team1, team2, time_zones)
            
    except ValueError as e:
        await interaction.response.send_message(f"❌ Invalid date: {e}", ephemeral=True)
    except Exception as e:
        logging.error(f"Error creating match: {e}")
        await interaction.response.send_message("❌ Error creating match. Please try again.", ephemeral=True)

async def send_match_notifications(guild, role_mentions, original_embed, team1, team2, time_zones):
    """Send DM notifications to all members of mentioned roles"""
    members_notified = set()
    
    for role_id in role_mentions:
        role = guild.get_role(int(role_id))
        if role:
            for member in role.members:
                if member.id not in members_notified and not member.bot:
                    try:
                        # Create personalized DM embed
                        dm_embed = discord.Embed(
                            title="⚽ Match Notification",
                            color=0x00ff00,
                            timestamp=datetime.utcnow()
                        )
                        
                        # Convert role mentions to role names for DM
                        team1_clean = team1
                        team2_clean = team2
                        
                        for role in guild.roles:
                            role_mention = f"<@&{role.id}>"
                            if role_mention in team1_clean:
                                team1_clean = team1_clean.replace(role_mention, role.name)
                            if role_mention in team2_clean:
                                team2_clean = team2_clean.replace(role_mention, role.name)
                        
                        dm_embed.add_field(name="🆚 Teams", value=f"{team1_clean} vs {team2_clean}", inline=False)
                        dm_embed.add_field(name="🕐 Times", value=f"""
🇺🇸 **English (GMT):** {format_time_for_language(time_zones['en'], 'en')}
🇵🇹 **Português:** {format_time_for_language(time_zones['pt'], 'pt')}
🇪🇸 **Español:** {format_time_for_language(time_zones['es'], 'es')}
                        """, inline=False)
                        
                        dm_embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
                        
                        # Send DM with translation buttons
                        view = TranslationView(dm_embed, 'en')
                        await member.send(embed=dm_embed, view=view)
                        
                        members_notified.add(member.id)
                        
                    except discord.Forbidden:
                        # User has DMs disabled
                        continue
                    except Exception as e:
                        logging.error(f"Error sending DM to {member}: {e}")
                        continue

@bot.tree.command(name="list_matches", description="List all active matches")
async def list_matches_command(interaction: discord.Interaction):
    if not check_channel_permissions(str(interaction.guild.id), str(interaction.channel.id)):
        await interaction.response.send_message(
            "❌ Bot commands are not allowed in this channel.",
            ephemeral=True
        )
        return
    
    with app.app_context():
        server = Server.query.filter_by(guild_id=str(interaction.guild.id)).first()
        if not server:
            await interaction.response.send_message("❌ No server configuration found.", ephemeral=True)
            return
        
        matches = Match.query.filter_by(server_id=server.id, is_active=True).order_by(Match.match_date).all()
        
        # Log this command
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "list_matches", interaction.channel.id, f"found: {len(matches)}"
        )
    
    if not matches:
        embed = discord.Embed(
            title="📋 Active Matches",
            description="No active matches found.",
            color=0xffaa00
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(
        title="📋 Active Matches",
        color=0x3498db,
        timestamp=datetime.utcnow()
    )
    
    for i, match in enumerate(matches, 1):
        time_zones = convert_to_timezones(match.match_date)
        
        match_info = f"""
**Teams:** {match.team1} vs {match.team2}
**Date:** {format_time_for_language(time_zones['en'], 'en')}
**ID:** `{match.id}`
        """
        
        embed.add_field(
            name=f"#{i} Match",
            value=match_info,
            inline=True
        )
    
    embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="end_match", description="End a match by ID")
@discord.app_commands.describe(match_id="ID of the match to end")
async def end_match_command(interaction: discord.Interaction, match_id: int):
    if not check_channel_permissions(str(interaction.guild.id), str(interaction.channel.id)):
        await interaction.response.send_message(
            "❌ Bot commands are not allowed in this channel.",
            ephemeral=True
        )
        return
    
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need manage messages permission to end matches.",
            ephemeral=True
        )
        return
    
    with app.app_context():
        server = Server.query.filter_by(guild_id=str(interaction.guild.id)).first()
        if not server:
            await interaction.response.send_message("❌ No server configuration found.", ephemeral=True)
            return
        
        match = Match.query.filter_by(id=match_id, server_id=server.id, is_active=True).first()
        if not match:
            await interaction.response.send_message("❌ Match not found or already ended.", ephemeral=True)
            return
        
        # Store match info before ending
        team1 = match.team1
        team2 = match.team2
        
        match.is_active = False
        db.session.commit()
        
        # Log this command
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "end_match", interaction.channel.id, f"match_id: {match_id}"
        )
    
        embed = discord.Embed(
            title="✅ Match Ended",
            description=f"Match #{match_id} ({team1} vs {team2}) has been ended.",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="send_dm", description="Send a private message to a user")
@discord.app_commands.describe(
    user="User to send message to",
    message="Message to send"
)
async def send_dm_command(interaction: discord.Interaction, user: discord.Member, message: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need manage messages permission to send DMs.",
            ephemeral=True
        )
        return
    
    try:
        embed = discord.Embed(
            title="📨 Message from Server Admin",
            description=message,
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Server", value=interaction.guild.name, inline=True)
        embed.add_field(name="From", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Send DM with translation buttons
        view = TranslationView(embed, 'en')
        await user.send(embed=embed, view=view)
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "send_dm", interaction.channel.id, f"to: {user.name}"
            )
        
        await interaction.response.send_message(
            f"✅ Message sent to {user.mention}",
            ephemeral=True
        )
        
    except discord.Forbidden:
        await interaction.response.send_message(
            f"❌ Cannot send DM to {user.mention}. They may have DMs disabled.",
            ephemeral=True
        )
    except Exception as e:
        logging.error(f"Error sending DM: {e}")
        await interaction.response.send_message(
            "❌ Error sending message. Please try again.",
            ephemeral=True
        )

@bot.tree.command(name="announce", description="Send an announcement embed")
@discord.app_commands.describe(
    title="Announcement title",
    message="Announcement message",
    channel="Channel to send to (optional)"
)
async def announce_command(
    interaction: discord.Interaction,
    title: str,
    message: str,
    channel: Optional[discord.TextChannel] = None
):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need manage messages permission to make announcements.",
            ephemeral=True
        )
        return
    
    target_channel = channel or interaction.channel
    
    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=0xe74c3c,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="Announced by", value=interaction.user.mention, inline=True)
    embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
    
    await target_channel.send(embed=embed)
    
    # Log this command
    with app.app_context():
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "announce", interaction.channel.id, f"title: {title}"
        )
    
    if channel and channel != interaction.channel:
        await interaction.response.send_message(
            f"✅ Announcement sent to {channel.mention}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)

@bot.tree.command(name="server_info", description="Display server information")
async def server_info_command(interaction: discord.Interaction):
    if not check_channel_permissions(str(interaction.guild.id), str(interaction.channel.id)):
        await interaction.response.send_message(
            "❌ Bot commands are not allowed in this channel.",
            ephemeral=True
        )
        return
    
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f"🏰 {guild.name}",
        color=0x3498db,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="📁 Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="📅 Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
    
    # Log this command
    with app.app_context():
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "server_info", interaction.channel.id, ""
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kick", description="Kick a member from the server")
@discord.app_commands.describe(
    member="Member to kick",
    reason="Reason for kick"
)
async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(
            "❌ You need kick members permission to use this command.",
            ephemeral=True
        )
        return
    
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot kick someone with equal or higher role.",
            ephemeral=True
        )
        return
    
    try:
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            color=0xe74c3c,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "kick", interaction.channel.id, f"kicked: {member.name}, reason: {reason}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to kick this member.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error kicking member: {e}")
        await interaction.response.send_message("❌ Error kicking member.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from the server")
@discord.app_commands.describe(
    member="Member to ban",
    reason="Reason for ban",
    delete_days="Days of messages to delete (0-7)"
)
async def ban_command(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: int = 0):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ You need ban members permission to use this command.",
            ephemeral=True
        )
        return
    
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot ban someone with equal or higher role.",
            ephemeral=True
        )
        return
    
    if delete_days < 0 or delete_days > 7:
        delete_days = 0
    
    try:
        await member.ban(reason=reason, delete_message_days=delete_days)
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            color=0x992d22,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "ban", interaction.channel.id, f"banned: {member.name}, reason: {reason}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to ban this member.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error banning member: {e}")
        await interaction.response.send_message("❌ Error banning member.", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a member")
@discord.app_commands.describe(
    member="Member to timeout",
    duration="Duration in minutes",
    reason="Reason for timeout"
)
async def timeout_command(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You need moderate members permission to use this command.",
            ephemeral=True
        )
        return
    
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot timeout someone with equal or higher role.",
            ephemeral=True
        )
        return
    
    if duration <= 0 or duration > 40320:  # Max 28 days
        await interaction.response.send_message(
            "❌ Duration must be between 1 and 40320 minutes (28 days).",
            ephemeral=True
        )
        return
    
    try:
        timeout_until = datetime.utcnow() + timedelta(minutes=duration)
        await member.timeout(timeout_until, reason=reason)
        
        embed = discord.Embed(
            title="🔇 Member Timed Out",
            color=0xf39c12,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "timeout", interaction.channel.id, f"member: {member.name}, duration: {duration}min"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to timeout this member.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error timing out member: {e}")
        await interaction.response.send_message("❌ Error timing out member.", ephemeral=True)

@bot.tree.command(name="clear", description="Clear messages from channel")
@discord.app_commands.describe(
    amount="Number of messages to delete (1-100)"
)
async def clear_command(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need manage messages permission to use this command.",
            ephemeral=True
        )
        return
    
    if amount <= 0 or amount > 100:
        await interaction.response.send_message(
            "❌ Amount must be between 1 and 100.",
            ephemeral=True
        )
        return
    
    try:
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=amount)
        
        embed = discord.Embed(
            title="🧹 Messages Cleared",
            description=f"Deleted {len(deleted)} messages",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "clear", interaction.channel.id, f"deleted: {len(deleted)} messages"
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to delete messages.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error clearing messages: {e}")
        await interaction.followup.send("❌ Error clearing messages.", ephemeral=True)

@bot.tree.command(name="role_add", description="Add role to a member")
@discord.app_commands.describe(
    member="Member to add role to",
    role="Role to add"
)
async def role_add_command(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ You need manage roles permission to use this command.",
            ephemeral=True
        )
        return
    
    if role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot assign a role equal or higher than your highest role.",
            ephemeral=True
        )
        return
    
    if role in member.roles:
        await interaction.response.send_message(
            f"❌ {member.mention} already has the {role.name} role.",
            ephemeral=True
        )
        return
    
    try:
        await member.add_roles(role)
        
        embed = discord.Embed(
            title="✅ Role Added",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "role_add", interaction.channel.id, f"member: {member.name}, role: {role.name}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error adding role: {e}")
        await interaction.response.send_message("❌ Error adding role.", ephemeral=True)

@bot.tree.command(name="role_remove", description="Remove role from a member")
@discord.app_commands.describe(
    member="Member to remove role from",
    role="Role to remove"
)
async def role_remove_command(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ You need manage roles permission to use this command.",
            ephemeral=True
        )
        return
    
    if role >= interaction.user.top_role:
        await interaction.response.send_message(
            "❌ You cannot manage a role equal or higher than your highest role.",
            ephemeral=True
        )
        return
    
    if role not in member.roles:
        await interaction.response.send_message(
            f"❌ {member.mention} doesn't have the {role.name} role.",
            ephemeral=True
        )
        return
    
    try:
        await member.remove_roles(role)
        
        embed = discord.Embed(
            title="❌ Role Removed",
            color=0xe74c3c,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "role_remove", interaction.channel.id, f"member: {member.name}, role: {role.name}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error removing role: {e}")
        await interaction.response.send_message("❌ Error removing role.", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set slowmode for a channel")
@discord.app_commands.describe(
    seconds="Slowmode duration in seconds (0-21600)",
    channel="Channel to set slowmode (optional)"
)
async def slowmode_command(interaction: discord.Interaction, seconds: int, channel: Optional[discord.TextChannel] = None):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ You need manage channels permission to use this command.",
            ephemeral=True
        )
        return
    
    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message(
            "❌ Slowmode must be between 0 and 21600 seconds (6 hours).",
            ephemeral=True
        )
        return
    
    target_channel = channel or interaction.channel
    
    try:
        await target_channel.edit(slowmode_delay=seconds)
        
        embed = discord.Embed(
            title="⏱️ Slowmode Updated",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        if seconds == 0:
            embed.description = f"Slowmode disabled in {target_channel.mention}"
        else:
            embed.description = f"Slowmode set to {seconds} seconds in {target_channel.mention}"
        
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "slowmode", interaction.channel.id, f"channel: {target_channel.name}, seconds: {seconds}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to edit this channel.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error setting slowmode: {e}")
        await interaction.response.send_message("❌ Error setting slowmode.", ephemeral=True)

@bot.tree.command(name="lock", description="Lock a channel")
@discord.app_commands.describe(
    channel="Channel to lock (optional)",
    reason="Reason for locking"
)
async def lock_command(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ You need manage channels permission to use this command.",
            ephemeral=True
        )
        return
    
    target_channel = channel or interaction.channel
    
    try:
        overwrite = target_channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await target_channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"{target_channel.mention} has been locked",
            color=0xe74c3c,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "lock", interaction.channel.id, f"channel: {target_channel.name}, reason: {reason}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to lock this channel.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error locking channel: {e}")
        await interaction.response.send_message("❌ Error locking channel.", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock a channel")
@discord.app_commands.describe(
    channel="Channel to unlock (optional)",
    reason="Reason for unlocking"
)
async def unlock_command(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "❌ You need manage channels permission to use this command.",
            ephemeral=True
        )
        return
    
    target_channel = channel or interaction.channel
    
    try:
        overwrite = target_channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await target_channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"{target_channel.mention} has been unlocked",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "unlock", interaction.channel.id, f"channel: {target_channel.name}, reason: {reason}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to unlock this channel.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error unlocking channel: {e}")
        await interaction.response.send_message("❌ Error unlocking channel.", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a member")
@discord.app_commands.describe(
    member="Member to warn",
    reason="Reason for warning"
)
async def warn_command(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You need manage messages permission to use this command.",
            ephemeral=True
        )
        return
    
    try:
        # Send warning DM to user
        dm_embed = discord.Embed(
            title="⚠️ Warning",
            color=0xf39c12,
            timestamp=datetime.utcnow()
        )
        
        dm_embed.add_field(name="Server", value=interaction.guild.name, inline=True)
        dm_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        dm_embed.add_field(name="Reason", value=reason, inline=False)
        dm_embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        try:
            view = TranslationView(dm_embed, 'en')
            await member.send(embed=dm_embed, view=view)
            dm_sent = True
        except discord.Forbidden:
            dm_sent = False
        
        # Send confirmation in channel
        embed = discord.Embed(
            title="⚠️ Member Warned",
            color=0xf39c12,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if not dm_sent:
            embed.add_field(name="Note", value="⚠️ Could not send DM to user", inline=False)
        
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "warn", interaction.channel.id, f"member: {member.name}, reason: {reason}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logging.error(f"Error warning member: {e}")
        await interaction.response.send_message("❌ Error warning member.", ephemeral=True)

@bot.tree.command(name="nick", description="Change a member's nickname")
@discord.app_commands.describe(
    member="Member to change nickname",
    nickname="New nickname (leave empty to remove)"
)
async def nick_command(interaction: discord.Interaction, member: discord.Member, nickname: str = None):
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message(
            "❌ You need manage nicknames permission to use this command.",
            ephemeral=True
        )
        return
    
    if member.top_role >= interaction.user.top_role and member != interaction.user:
        await interaction.response.send_message(
            "❌ You cannot change the nickname of someone with equal or higher role.",
            ephemeral=True
        )
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        
        embed = discord.Embed(
            title="📝 Nickname Changed",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="New Nickname", value=nickname or "None", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
        
        # Log this command
        with app.app_context():
            await log_command_usage(
                interaction.guild.id, interaction.user.id, interaction.user.name,
                "nick", interaction.channel.id, f"member: {member.name}, new_nick: {nickname}"
            )
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this member's nickname.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error changing nickname: {e}")
        await interaction.response.send_message("❌ Error changing nickname.", ephemeral=True)

@bot.tree.command(name="userinfo", description="Get information about a user")
@discord.app_commands.describe(member="Member to get info about")
async def userinfo_command(interaction: discord.Interaction, member: discord.Member = None):
    if not check_channel_permissions(str(interaction.guild.id), str(interaction.channel.id)):
        await interaction.response.send_message(
            "❌ Bot commands are not allowed in this channel.",
            ephemeral=True
        )
        return
    
    target = member or interaction.user
    
    embed = discord.Embed(
        title=f"👤 {target.display_name}",
        color=target.color if target.color != discord.Color.default() else 0x3498db,
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(name="🏷️ Username", value=f"{target.name}#{target.discriminator}", inline=True)
    embed.add_field(name="🆔 User ID", value=target.id, inline=True)
    embed.add_field(name="📅 Account Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="📥 Joined Server", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "Unknown", inline=True)
    embed.add_field(name="🎭 Roles", value=f"{len(target.roles)-1} roles", inline=True)
    embed.add_field(name="💎 Top Role", value=target.top_role.mention, inline=True)
    
    # Status
    status_emojis = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle", 
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline"
    }
    embed.add_field(name="📶 Status", value=status_emojis.get(target.status, "❓ Unknown"), inline=True)
    
    if target.premium_since:
        embed.add_field(name="💎 Boosting Since", value=target.premium_since.strftime("%Y-%m-%d"), inline=True)
    
    embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
    
    # Log this command
    with app.app_context():
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "userinfo", interaction.channel.id, f"target: {target.name}"
        )
    
    await interaction.response.send_message(embed=embed)

@tasks.loop(minutes=1)
async def check_reminders():
    """Check for match reminders that need to be sent"""
    with app.app_context():
        now = datetime.utcnow()
        
        # Get reminders that need to be sent
        reminders = MatchReminder.query.filter(
            MatchReminder.reminder_time <= now,
            MatchReminder.sent == False
        ).all()
        
        for reminder in reminders:
            try:
                match = reminder.match
                if not match.is_active:
                    reminder.sent = True
                    continue
                
                # Get guild and roles
                guild = bot.get_guild(int(match.server.guild_id))
                if not guild:
                    continue
                
                role_mentions = json.loads(match.role_mentions)
                members_to_notify = set()
                
                for role_id in role_mentions:
                    role = guild.get_role(int(role_id))
                    if role:
                        for member in role.members:
                            if not member.bot:
                                members_to_notify.add(member)
                
                # Create reminder embed
                time_left = "10 minutes" if reminder.reminder_type == "10min" else "3 minutes"
                time_zones = convert_to_timezones(match.match_date)
                
                embed = discord.Embed(
                    title=f"⏰ Match Reminder - {time_left}",
                    color=0xf39c12,
                    timestamp=datetime.utcnow()
                )
                
                # Convert role mentions to role names
                team1_clean = match.team1
                team2_clean = match.team2
                
                for role in guild.roles:
                    role_mention = f"<@&{role.id}>"
                    if role_mention in team1_clean:
                        team1_clean = team1_clean.replace(role_mention, role.name)
                    if role_mention in team2_clean:
                        team2_clean = team2_clean.replace(role_mention, role.name)
                
                embed.add_field(name="🆚 Teams", value=f"{team1_clean} vs {team2_clean}", inline=False)
                embed.add_field(name="🕐 Match Time", value=f"""
🇺🇸 **English (GMT):** {format_time_for_language(time_zones['en'], 'en')}
🇵🇹 **Português:** {format_time_for_language(time_zones['pt'], 'pt')}
🇪🇸 **Español:** {format_time_for_language(time_zones['es'], 'es')}
                """, inline=False)
                
                embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
                
                # Send reminders to all members
                for member in members_to_notify:
                    try:
                        view = TranslationView(embed, 'en')
                        await member.send(embed=embed, view=view)
                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        logging.error(f"Error sending reminder to {member}: {e}")
                        continue
                
                # Mark reminder as sent
                reminder.sent = True
                
            except Exception as e:
                logging.error(f"Error processing reminder {reminder.id}: {e}")
                reminder.sent = True  # Mark as sent to avoid repeated errors
        
        db.session.commit()

@bot.tree.command(name="help", description="Show all available bot commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Discord Server Manager Bot - Help",
        description="Here are all available commands organized by category:",
        color=0x3498db,
        timestamp=datetime.utcnow()
    )
    
    # Match Management Commands
    embed.add_field(
        name="⚔️ Match Management",
        value="""
`/create_match` - Create a new match with teams and date
`/list_matches` - View all active matches
`/end_match` - End a match by ID
        """,
        inline=False
    )
    
    # Moderation Commands
    embed.add_field(
        name="🛡️ Moderation",
        value="""
`/kick` - Kick a member from the server
`/ban` - Ban a member from the server
`/timeout` - Timeout a member
`/warn` - Send a warning to a member
`/clear` - Delete messages in bulk
        """,
        inline=False
    )
    
    # Channel Management
    embed.add_field(
        name="📺 Channel Management",
        value="""
`/lock` - Lock a channel (prevent sending messages)
`/unlock` - Unlock a channel
`/slowmode` - Set slowmode for a channel
        """,
        inline=False
    )
    
    # Member Management
    embed.add_field(
        name="👥 Member Management",
        value="""
`/nick` - Change a member's nickname
`/addrole` - Add a role to a member
`/removerole` - Remove a role from a member
`/userinfo` - Get information about a user
`/serverinfo` - Get server information
        """,
        inline=False
    )
    
    # Communication
    embed.add_field(
        name="💬 Communication",
        value="""
`/send_dm` - Send a private message to a user
`/announce` - Make a server announcement
        """,
        inline=False
    )
    
    # Bot Setup
    embed.add_field(
        name="⚙️ Bot Setup",
        value="""
`/setup` - Configure bot settings for your server
`/restrict` - Restrict bot to specific channels
        """,
        inline=False
    )
    
    embed.add_field(
        name="🌐 Web Dashboard",
        value="[Visit Bot Dashboard](https://5057fc81-5a06-4d87-b2e5-78b6e75fde4a-00-2m9k4kntkh9n.worf.replit.dev/)",
        inline=False
    )
    
    embed.set_footer(text="Bot created by kokex | Contact: kokexe | 2025")
    
    # Log this command
    with app.app_context():
        await log_command_usage(
            interaction.guild.id, interaction.user.id, interaction.user.name,
            "help", interaction.channel.id, "help_requested"
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

def run_bot():
    """Run the Discord bot"""
    try:
        # Start keep alive server
        from keep_alive import start_keep_alive
        start_keep_alive()
        
        # Run the bot
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"Bot error: {e}")
