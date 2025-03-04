﻿# Meeting Manager Bot
This bot was inspired by the meeting functionality of tools like Microsoft Teams and simplifies the process of managing meetings on Discord. It allows users to create, manage, and organize meetings with voice channels, threads, and recurring meeting support. The bot was built using Python, Discord.py, and SQLite.

## Features
- Schedule and create meetings with private text and voice channels
- Cancel meetings along with notifications
- Automatically receive reminders 15 minutes prior to a meeting
- Automatic drag into designated meeting channels

## Bot Setup Guide
### Prerequisites
- Python 3.8 or higher

### Installation
1. Clone the repository:**
```
git clone https://github.com/edisonrhuang/Discord-Meeting-Manager.git
cd Discord-Meeting-Manager
```
2. Install the required dependencies:
```
pip install -r requirements.txt
```
3. Create a `.env` file in the root directory of your project and add your bot's token and server id:
```
PROD_TOKEN=
GUILD_ID=
```
4. Run the bot:
```
python main.py
```

## Server Setup Guide

1. Create a `MEETINGS` category.
2. Create a `meetings-list` forum text channel.
3. Create an `auto-dragging-vc` voice channel.

## Command Guide

### `/create_meeting [title] [description] [time] [date]`

Creates a new meeting with the specified title, description, date, and time.

- **[title]**: The title of the meeting.
- **[description]**: The meeting's description.
- **[time]**: The time of the meeting (Supported formats: `HH:MM PM`, `HH:MM pm`, `HH:MM PM`, `HH:MM pm`, or `HH:MM` in 24-hour format).
- **[date]**: The date of the meeting (Supported formats: `MM/DD/YYYY` or `MM/DD/YY`).

### `/cancel_meeting [title]`

Cancels the titled meeting, removing the generated text and voice channels, and messages the forum post that the meeting has been cancelled.

- **[title]**: The title of the meeting.