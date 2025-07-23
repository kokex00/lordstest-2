# Discord Server Manager Bot

## Overview

A comprehensive Discord bot for server management with match scheduling capabilities. The application consists of a Flask web dashboard for monitoring and a Discord bot with advanced features including multi-language support, automatic reminders, and extensive logging.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Flask Web Application**: Provides REST API and web dashboard
- **Discord Bot**: Handles Discord interactions using discord.py
- **SQLAlchemy ORM**: Database abstraction layer with declarative models
- **Threading**: Separates web server from Discord bot execution

### Frontend Architecture
- **Server-Side Rendered Templates**: Jinja2 templates with Bootstrap UI
- **JavaScript Dashboard**: Real-time data updates and interactive features
- **Responsive Design**: Mobile-friendly interface with dark theme

### Database Schema
- **SQLite/PostgreSQL**: Configurable database backend
- **Models**: Server, Match, MatchReminder, BotLog
- **Relationships**: Proper foreign keys and cascading deletes

## Key Components

### Discord Bot Features
- **Slash Commands**: Modern Discord interaction system
- **Multi-language Support**: English, Portuguese, Spanish translations
- **Match Management**: Create, view, and end matches with automatic reminders
- **Translation Interface**: Interactive buttons for message translation
- **Server Administration**: Channel restrictions, logging, announcements
- **Timezone Handling**: Automatic conversion for different regions

### Web Dashboard
- **Real-time Statistics**: Server count, active matches, bot status
- **Match Overview**: Comprehensive match listing and management
- **Log Viewer**: Filterable command usage and activity logs
- **Server Management**: Configuration for Discord servers

### Bot Commands
#### Match Management
- **Match Creation**: Simple command structure for scheduling matches
- **Reminder System**: 10-minute and 3-minute automatic alerts
- **Match Listing**: View all active matches with IDs
- **Match Termination**: End matches by ID
- **Direct Messaging**: Private notifications to mentioned roles with translation buttons

#### Server Administration
- **Moderation Commands**: kick, ban, timeout, warn members
- **Channel Management**: lock, unlock, slowmode control, message clearing
- **Role Management**: add/remove roles from members
- **Nickname Management**: change member nicknames
- **User Information**: detailed user/server information display

#### Communication & Translation
- **Private Messaging**: Send DMs to specific users with translation options
- **Announcements**: Server-wide announcements with embeds
- **Translation System**: Interactive buttons for English, Portuguese, Spanish
- **Activity Logging**: Comprehensive command and action tracking

## Data Flow

### Match Creation Flow
1. User executes slash command with team names and date
2. Bot validates input and creates database entry
3. System sends private messages to mentioned roles with translation buttons
4. Automatic reminders scheduled for 10 and 3 minutes before match
5. Activity logged to database and optional log channel

### Translation System
1. Original message displayed with translation buttons
2. User clicks language button (🇺🇸🇵🇹🇪🇸)
3. Bot deletes original message and posts translated version
4. Timezone conversion applied based on selected language

### Logging Pipeline
1. All commands trigger logging utility
2. Database entry created with user, command, and details
3. Optional broadcast to designated log channel
4. Web dashboard displays aggregated statistics

## External Dependencies

### Python Packages
- **discord.py**: Discord API interaction
- **Flask**: Web framework and API
- **SQLAlchemy**: Database ORM
- **APScheduler**: Task scheduling for reminders
- **pytz**: Timezone handling
- **Werkzeug**: WSGI utilities and proxy handling

### Frontend Libraries
- **Bootstrap**: UI framework with dark theme
- **Chart.js**: Data visualization for dashboard
- **Font Awesome**: Icon library

### Environment Variables
- **DISCORD_TOKEN**: Discord bot authentication
- **DATABASE_URL**: Database connection string
- **SESSION_SECRET**: Flask session encryption key

### Support Information
- **Creator**: kokex
- **Contact**: kokexe
- **Support Discord ID**: 1215053388404756580
- **Bot Version**: 1.0.0

### Recent Changes (July 23, 2025)
- Added comprehensive moderation commands (kick, ban, timeout, warn, clear)
- Implemented channel management (lock, unlock, slowmode)
- Added role and nickname management capabilities
- Enhanced translation system with more languages and terms
- Created dedicated support page with contact information
- Updated web dashboard with statistics page
- Improved activity logging and monitoring system
- Added keep alive system (port 8080) for uptime monitoring
- Fixed Discord private message handling to prevent errors
- Created complete about page with bot information
- Added comprehensive help command (/help) with categorized command listing
- Updated bot status to include creator name and dashboard link
- Removed Bot Activity notification messages to prevent spam
- Updated all copyright information to 2025
- Enhanced bot bio with web dashboard link integration

## Deployment Strategy

### Application Structure
- **app.py**: Main Flask application with database initialization
- **main.py**: Development server entry point
- **bot.py**: Discord bot implementation with command handlers
- **models.py**: Database schema definitions

### Threading Model
- Flask web server runs on main thread
- Discord bot executes in separate thread for concurrent operation
- Shared database context through SQLAlchemy

### Database Migration
- Automatic table creation on startup
- SQLAlchemy handles schema management
- Configurable database backend (SQLite for development, PostgreSQL for production)

### Static Assets
- CSS and JavaScript served through Flask static handling
- Bootstrap CDN for reliable UI framework delivery
- Custom styling for Discord-themed interface

### Logging Configuration
- Python logging configured for DEBUG level
- Database logging for all bot activities
- Optional Discord channel logging for real-time monitoring

The application is designed for scalability with proper separation of concerns between the web interface and Discord bot functionality, making it suitable for managing multiple Discord servers with comprehensive activity tracking and user-friendly match scheduling.