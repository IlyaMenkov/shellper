import datetime
import os

from apiclient.discovery import build
import argparse
import httplib2
import oauth2client
import pygoogle
import re
import rfc3339


APPLICATION_NAME = 'Shellper'
CLIENT_SECRET_FILE = 'etc/client_secret.json'
CREDENTIALS_PATH = 'etc/calendar-api.json'
SCOPES = 'https://www.googleapis.com/auth/calendar'


# Base class for working of app
class Base(object):
    def __init__(self):
        self.page_number = 1
        self.service = None

    def _init_service(self):
        credentials = self.authentication()
        return build('calendar', 'v3',
                     http=credentials.authorize(httplib2.Http()))

    def convert_to_rfc3339(self, datelist, timelist, inc=0):
        return rfc3339.rfc3339(datetime.datetime(datelist[2],
                                                 datelist[1],
                                                 datelist[0],
                                                 hour=timelist[0]+inc,
                                                 minute=timelist[1]))

    # Search query in google.com
    def search_query(self, query):
        request = pygoogle.pygoogle(query)
        request.pages = self.page_number
        return request.get_urls()

    # Check of available access to user calendar,
    # if access unavailable - request access
    def authentication(self):
        flags = argparse.ArgumentParser(
            parents=[oauth2client.tools.argparser]).parse_args()
        home_dir = os.path.expanduser('shellper')
        credential_dir = os.path.join(home_dir, 'etc/.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)

        store = oauth2client.file.Storage(CREDENTIALS_PATH)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = oauth2client.client.flow_from_clientsecrets(
                CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = oauth2client.tools.run_flow(flow, store, flags)
            else:
                credentials = oauth2client.tools.run(flow, store)
            print 'Storing credentials to ' + CREDENTIALS_PATH
        return credentials

    # List of events from available account
    def get_event_list(self):
        self.service = self._init_service()
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        print 'Getting the upcoming 10 events'
        eventsResult = self.service.events().list(
            calendarId='primary',
            maxResults=10, singleEvents=True, timeMin=now,
            orderBy='startTime').execute()
        events = eventsResult.get('items', [])

        if not events:
            return 'No upcoming events found.'
        for event in events:
            start = event['start'].get('dateTime')
            return start, event['summary']

    # Create event from file etc/template.yaml
    # Parse date format 00-00-0000, 00/00/0000, 00.00.0000; time formats 00.00,
    # 00-00, 00:00
    # TODO(esikachev): fix comment when implement UI

    def create_event(self, config):
        if self.service is None:
            self.service = self._init_service()
        datelist = re.split(r'[./-]', config["date"])
        datelist = map(int, datelist)
        timelist = re.split(r'[.:-]', config["time"])
        timelist = map(int, timelist)
        try:
            datelist[2]
        except IndexError:
            datelist.append(datetime.date.today().year)
        event = {
            'summary': config["summary"],
            'start': {
                'dateTime': self.convert_to_rfc3339(datelist, timelist)
            },
            'end': {
                'dateTime': self.convert_to_rfc3339(datelist, timelist, inc=1)
            },
            'description': ' '.join(config["description"][0]).replace(" ",
                                                                      "\n")
        }

        created_event = self.service.events().insert(calendarId='primary',
                                                     body=event).execute()
        return created_event['id']

    # Delete event on id
    def delete_event(self, eventId):
        self.service.events().delete(calendarId='primary',
                                     eventId=eventId).execute()
