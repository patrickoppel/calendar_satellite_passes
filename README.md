# Venv

**Set-up Virtual Environment**

```
python3 -m venv venv
source venv/bin/activate
pip install requests pytz skyfield google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client python-dateutil
```

# Config

Use the `config.ini` file to specify your satellite(s) and groundstation(s).

Here is an example containing the CUAVA-2 and Waratah Seed-1 satellite and two groundstations:
```
[Satellites]
Satellites = [
    ("CUAVA-2", 60527),
    ("Waratah Seed-1", 60469)]
; [
;     (name, norad_id),
; ]

[Groundstations]
Groundstations = [
    ("USYD", -33.889585, 151.193511, 30.0),
    ("AWS", -32.177011, 148.615696, 287.0)]
; [
;     (name, latitude, longitude, altitude),
; ]

[Passes]
Combine = True
Tolerance = 180
TimeZone = 'Australia/Sydney'
```

Set the Passes options to:

- Combine passes over multiple groundstations into one calendar event showing if they overlap
- Set the overlap tolerance in seconds (default=180)
- Set your timezone (default='Australia/Sydney')

# Calendar ID

To find your Google Calendar ID, follow these steps:

### Step-by-Step Instructions

1. **Open Google Calendar**:
   Open your web browser and go to [Google Calendar](https://calendar.google.com/).

2. **Go to Calendar Settings**:
   - On the left side of the screen, you will see a list of your calendars under "My calendars".
   - Hover over the calendar for which you want to find the ID.
   - Click on the three vertical dots that appear next to the calendar name.
   - Select "Settings and sharing" from the dropdown menu.

3. **Find the Calendar ID**:
   - In the "Settings" page, scroll down to the "Integrate calendar" section.
   - You will see the "Calendar ID" field. It will look something like `your_calendar_id@gmail.com` or a long string of characters followed by `@group.calendar.google.com`.

4. **Copy the Calendar ID**:
   - Copy the Calendar ID from this field.

### Create the `id.ini` File
Create a file named `id.ini` in your project directory and add the Calendar ID to it:

```ini
[Calendar]
ID = your_calendar_id
```

Replace `your_calendar_id` with the actual Calendar ID you copied from Google Calendar.

# Google API credentials

## Step-by-Step Instructions

1. **Go to the Google API Console**:
   Open your web browser and go to the [Google API Console](https://console.developers.google.com/).

2. **Create a New Project**:
   If you don't already have a project, create a new one:
   - Click on the project dropdown at the top of the page.
   - Click on "New Project".
   - Enter a project name and click "Create".

3. **Enable the Google Calendar API**:
   - In the API Console, go to the "Library" tab.
   - Search for "Google Calendar API".
   - Click on "Google Calendar API" and then click "Enable".

4. **Create OAuth 2.0 Credentials**:
   - Go to the "Credentials" tab in the API Console.
   - Click on "Create Credentials" and select "OAuth client ID".
   - If prompted to configure the OAuth consent screen, follow the instructions to set it up.
   - Select "Application type" as "Desktop app".
   - Enter a name for your OAuth client ID and click "Create".

5. **Download the `credentials.json` File**:
   - After creating the OAuth client ID, you will see a dialog with your client ID and client secret.
   - Click on "Download" to download the `credentials.json` file.
   - Save the file to your project directory.

### Example Directory Structure
Your project directory might look like this:

```
/home/user/calendar_satellite_passes/
├── calendar_satellite_passes.py
├── credentials.json
├── token.json
├── config.ini
├── id.ini
└── tle/
    ├── 60527.txt
    └── 60469.txt
```