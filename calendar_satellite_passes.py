#!/usr/bin/env python3

import datetime
import os.path
import requests
import pytz
import configparser
import ast

from skyfield.api import Topos, load, utc
from skyfield.sgp4lib import EarthSatellite
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, UTC
from dateutil.parser import isoparse

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Fetch TLE data from Celestrak
def fetch_tle(norad_id):
    # Read TLE data from a file
    tle_file_path = f'/home/pat/Observations/Calendar/tle/{norad_id}.txt'
    if not os.path.exists(tle_file_path):
        raise FileNotFoundError(f"TLE file for {norad_id} not found at {tle_file_path}")
    
    if os.path.getmtime(tle_file_path) < datetime.now().timestamp() - 7200:
        url = f'https://celestrak.com/NORAD/elements/gp.php?CATNR={norad_id}'
        response = requests.get(url)
        tle_lines = response.text.strip().split('\n')
        with open(tle_file_path, 'w') as file:
            file.write('\n'.join(tle_lines))

    with open(tle_file_path, 'r') as file:
        tle_lines = file.readlines()
    
    # Ensure the TLE data has exactly three lines
    if len(tle_lines) != 3:
        raise ValueError(f"Invalid TLE data in file {tle_file_path}")
    
    tle_lines = [line.strip() for line in tle_lines]

    return tle_lines

class GroundStation:
    def __init__(self, name, latitude, longitude, elevation):
        self.name = name
        self.topos = Topos(latitude, longitude, elevation_m=elevation)

class Pass:
    def __init__(self, start, end, ground_station, max_elevation, pass_id):
        self.start = start
        self.end = end
        # self.max_elevation = []
        # self.max_elevation.append(MaxElevation(ground_station, max_elevation))
        self.max_elevation = {}
        if ground_station not in self.max_elevation:
            self.max_elevation[ground_station] = []
        self.max_elevation[ground_station].append(max_elevation)
        self.pass_id = pass_id

    def add_max_elevation(self, ground_station, max_elevation):
        if ground_station not in self.max_elevation:
            self.max_elevation[ground_station] = []
        self.max_elevation[ground_station].append(max_elevation)

    def print_max_elevation(self):
        str_ = ""
        for gs, elevation in self.max_elevation.items():        
            str_ += (f"{gs}: {elevation[0]:.1f}° ")

        return str_
    
    def print_only_max_elevation(self):
        str_ = ""
        for gs, elevation in self.max_elevation.items():        
            str_ += (f"{elevation[0]:.1f}°,")

        str_ = str_[:-1]
        return str_

    def __repr__(self):
        return f"Pass ID: {self.pass_id}, Start: {self.start}, End: {self.end}, Max Elevation: {self.print_max_elevation()}\n"

class Satellite:
    def __init__(self,name, norad_id):
        tle_lines = fetch_tle(norad_id)
        satellite = EarthSatellite(tle_lines[1], tle_lines[2], tle_lines[0])
        self.name = name
        self.satellite = satellite
        self.passes = {}

    def calculate_passes(
        self, 
        ground_stations, 
        start_time=datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(utc), 
        end_time=datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(utc) + timedelta(days=7),
        altitude_degrees=5.0):
        # Define time range for pass calculations 
        # start time is current day 12AM local time, end time is next day 11:59AM local time
        # start_time = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        # start_time = start_time.astimezone(utc)
        # end_time = start_time + timedelta(days=7)

        ts = load.timescale()
        t0 = ts.utc(start_time)
        t1 = ts.utc(end_time)

        for ground_station in ground_stations:
            gs_name = ground_station.name
            gs_topos = ground_station.topos
            self.passes[gs_name]=[] #Initialise list for this groundstation

            times, events = self.satellite.find_events(gs_topos, t0, t1, altitude_degrees)

            pass_start = None
            max_elevation = 0
            pass_id = 0
            # first_pass_next_day = False

            for ti, event in zip(times, events):
                name = ('rise', 'culminate', 'set')[event]
                difference = self.satellite - gs_topos
                topocentric = difference.at(ti)
                elevation = topocentric.altaz()[0].degrees
                
                if event == 0:
                    pass_start = ti.utc_iso()
                    max_elevation = 0
                
                if elevation > max_elevation:
                    max_elevation = elevation
            
                if event == 2:  # Set event
                    pass_end = ti.utc_iso()
                    # # Check if pass is on the next day
                    # if ti.utc_datetime() > t0.utc_datetime() + timedelta(days=1) and not first_pass_next_day:            
                    #     pass_id = 0
                    #     first_pass_next_day = True
                    pass_id += 1
                    self.passes[gs_name].append(Pass(pass_start, pass_end, gs_name, round(max_elevation, 1), pass_id))

    def combine_passes(self, tolerance=180, timezone='Australia/Sydney'):
        combined_passes=[]

        new_passes = {}

        if not len(self.passes) < 2:
            ground_station_lists = list(self.passes.items())
            for i, (gs1, passes1) in enumerate(ground_station_lists):                
                for gs2, passes2 in ground_station_lists[i+1:]:    
                    remove_ids1 = []                
                    remove_ids2 = []
                    for pass1 in passes1:                                                    
                        for pass2 in passes2:
                            if abs(isoparse(pass1.start) - isoparse(pass2.start)) < timedelta(seconds=tolerance) or pass1.start < pass2.start and pass1.end > pass2.end:
                                combined_pass = Pass(
                                    start=min(pass1.start, pass2.start),
                                    end=max(pass1.end, pass2.end),
                                    ground_station=gs1,
                                    max_elevation=pass1.max_elevation[gs1][0],
                                    # ground_station=pass1.max_elevation[0].ground_station,                                       
                                    # max_elevation=pass1.max_elevation[0].elevation,
                                    pass_id=pass1.pass_id
                                )
                                combined_pass.add_max_elevation(gs2, pass2.max_elevation[gs2][0])                                
                                # combined_pass.max_elevation.append(MaxElevation(pass2.max_elevation[0].ground_station, pass2.max_elevation[0].elevation))
                                joint_pass = f"({gs1}, {gs2})"
                                if joint_pass not in new_passes:
                                    new_passes[joint_pass] = []
                                new_passes[joint_pass].append(combined_pass)
                                remove_ids1.append(pass1.pass_id)
                                remove_ids2.append(pass2.pass_id)                                    
                    self.passes[gs1] = [pass_ for pass_ in passes1 if pass_.pass_id not in remove_ids1]    
                    self.passes[gs2] = [pass_ for pass_ in passes2 if pass_.pass_id not in remove_ids2]                                    

        self.passes.update(new_passes)                                                               
    
    def create_daily_pass_id(self, timezone='Australia/Sydney'):
        # Flatten passes dictionary into a list
        all_passes = [p for passes in self.passes.values() for p in passes]
        # sort combined passes by start_time
        all_passes.sort(key=lambda x: x.start)

        # Add pass ID to passes
        pass_id = 1
        sydney_tz = pytz.timezone('Australia/Sydney')
        current_day = isoparse(all_passes[0].start).astimezone(sydney_tz).date()
        
        for pass_ in all_passes:       
            pass_date = isoparse(pass_.start).astimezone(sydney_tz).date()

            if pass_date != current_day:
                pass_id = 1
                current_day = pass_date
            
            pass_.pass_id = pass_id
            pass_id += 1
        
        # Update the passes dictionary with the new pass IDs
        self.passes = {gs: [] for gs in self.passes}
        for pass_ in all_passes:
            if len(pass_.max_elevation) > 1:
                gs = f"({', '.join(pass_.max_elevation.keys())})"
            else:
                gs = list(pass_.max_elevation.keys())[0]
            self.passes[gs].append(pass_)

        # Sort each list of passes by start time within each ground station
        for gs, passes in self.passes.items():
            passes.sort(key=lambda x: x.start)

    def create_events(self, calendar_id, service, existing_events):
        for gs, passes in self.passes.items():
            for pass_ in passes:                
                event = {
                    'summary': '%s %s (%s)' % (pass_.pass_id, self.name, pass_.print_only_max_elevation()),
                    'description': pass_.print_max_elevation(),
                    'start': {
                        'dateTime': pass_.start,
                        'timeZone': 'Australia/Sydney',
                    },
                    'end': {
                        'dateTime': pass_.end,
                        'timeZone': 'Australia/Sydney',
                    }
                }
                event_id = pass_.pass_id
                existing_event = next(
                    (
                        e for e in existing_events.values()
                        if e.get('summary', '').startswith(f"{event_id} {self.name}") and
                        abs(isoparse(e['start']['dateTime']) - isoparse(pass_.start)) <= timedelta(minutes=2)
                    ),
                    None
                )
                
                if existing_event:
                    if existing_event['summary'] == event['summary']:
                        print('Event already exists: %s' % (event['summary']))
                    else:
                        service.events().delete(calendarId=calendar_id, eventId=existing_event['id']).execute()
                        event = service.events().insert(calendarId=calendar_id, body=event).execute()
                        print('Event updated: %s' % (event.get('summary')))
                else:                
                    event = service.events().insert(calendarId=calendar_id, body=event).execute()
                    print('Event created: %s' % (event.get('summary')))
            
def get_events(service):
    # now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    # tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    # print("%s %s" % (now, tomorrow))
    start_time_0 = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    start_time = start_time_0.isoformat(timespec='microseconds')
    end_time = (start_time_0 + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec='microseconds')

    events_result = (
        service.events()
        .list(
            calendarId="820f18b8b31a6596d4ed3b04ae420de54e2591da98f2dcf573c495b534c20404@group.calendar.google.com",
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])

    if not events:
        print("No upcoming events found.")
        return

    return events

def main():
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  id_ = configparser.ConfigParser()
  id_.read("id.ini")  
  calendar_id = id_["Calendar"]["ID"]

  config = configparser.ConfigParser()
  config.read("config.ini")
  satellites_str = config["Satellites"]["Satellites"]
  satellites_init = ast.literal_eval(satellites_str)
  ground_stations_lat_long_alt_str = config["Groundstations"]["Groundstations"]
  ground_stations_lat_long_alt = ast.literal_eval(ground_stations_lat_long_alt_str)
  combine = config.getboolean("Passes", "Combine")
  tolerance = config.getint("Passes", "Tolerance") if config.has_option("Passes", "Tolerance") else None
  timezone = config.get("Passes", "TimeZone") if config.has_option("Passes", "TimeZone") else None
    
#   # Read event formats from the configuration file
#   event_formats = {
#     'default': ast.literal_eval(config["EventFormat"]["default"]),
#     'alternative': ast.literal_eval(config["EventFormat"]["alternative"])
#   }

#   # Select the desired event format
#   selected_format = event_formats['default']  # Change this to 'alternative' to use the alternative format

  print("Satellites: ", satellites_init)
  print("Groundstations: ", ground_stations_lat_long_alt[0])
  try:
    service = build("calendar", "v3", credentials=creds)
    
    satellites = [Satellite(s[0],s[1]) for s in satellites_init]
    ground_stations = [GroundStation(g[0],g[1],g[2],g[3]) for g in ground_stations_lat_long_alt]

    events = get_events(service) 
    if events is not None:                   
        existing_events = {event.get('summary', ''): event for event in events}
    else:
        existing_events = {}

    for satellite in satellites:
        satellite.calculate_passes(ground_stations) 
        if combine:
            satellite.combine_passes(tolerance, timezone)                   
        satellite.create_daily_pass_id(timezone) 
        satellite.create_events(calendar_id, service, existing_events)

  except HttpError as error:
    print(f"An error occurred: {error}")

if __name__ == "__main__":
  main()