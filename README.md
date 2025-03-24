# Meeting Manager Bot
This bot was inspired by the meeting functionality of tools like Microsoft Teams and simplifies the process of managing meetings on Discord. It allows users to create, manage, and organize meetings with voice channels, threads, and recurring meeting support. The bot was built using Python, Discord.py, and SQLite.

## Features
- Schedule and create meetings with private text and voice channels
- Cancel meetings along with notifications
- Reschedule meetings if availability changes.
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

### `/cancel_meeting [meeting id]`

Cancels the meeting according to its specific id, removing the generated text and voice channels, and messages the forum post that the meeting has been cancelled.

- **[meeting_id]**: The id of the meeting.

### `/reschedule_meeting [meeting_id] [new_time] [new_date]`

Reschedules an existing meeting, updates the meeting's date and time, sends a notification in the meeting's text channel, and posts a new update in the forum thread with an updated embed.

- **[meeting_id]**: The id of the meeting.
- **[new_time]**: The new meeting time. Enter "none" to make no changes.
- **[new_date]**: The new meeting date. Enter "none" to make no changes.

### `/change_status [status]`

Changes your current availability status for future meetings.

- **[status]**: The current status of the user (Formats: 'Available' or 'Busy').

### `/cleanup [meeting_id]`

Cleans up the meeting corresponding to the given ID by archiving the text channel and forum post, and deleting the voice channel and role

- **[meeting_id]**: The id of the meeting.
