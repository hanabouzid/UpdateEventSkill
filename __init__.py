from __future__ import print_function
import json
import sys
from filecmp import cmp

from adapt.intent import IntentBuilder
from adapt.engine import IntentDeterminationEngine
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
from mycroft.util.parse import extract_datetime
from datetime import datetime, timedelta
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import httplib2
from googleapiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client import tools

import string
import pytz
#in the raspberry we add __main__.py for the authorization
UTC_TZ = u'+00:00'
SCOPES = ['https://www.googleapis.com/auth/calendar']
FLOW = OAuth2WebServerFlow(
    client_id='73558912455-smu6u0uha6c2t56n2sigrp76imm2p35j.apps.googleusercontent.com',
    client_secret='0X_IKOiJbLIU_E5gN3NefNns',
    scope='https://www.googleapis.com/auth/contacts.readonly',
    user_agent='Smart assistant box')
# TODO: Change "Template" to a unique name for your skill
class UpdateEventSkill(MycroftSkill):
    def __init__(self):
        super(UpdateEventSkill, self).__init__(name="UpdateEventskill")

    @property
    def utc_offset(self):
        return timedelta(seconds=self.location['timezone']['offset'] / 1000)

    def freebusy(self, mail, datestart, datend, service):
        body = {
            "timeMin": datestart,
            "timeMax": datend,
            "timeZone": 'America/Los_Angeles',
            "items": [{"id": mail}]
        }
        eventsResult = service.freebusy().query(body=body).execute()
        cal_dict = eventsResult[u'calendars']
        print(cal_dict)
        for cal_name in cal_dict:
            print(cal_name, ':', cal_dict[cal_name])
            statut = cal_dict[cal_name]
            for i in statut:
                if (i == 'busy' and statut[i] == []):
                    return True

                    # ajouter l'email de x ala liste des attendee
                elif (i == 'busy' and statut[i] != []):
                    return False

    @intent_handler(IntentBuilder("update_event_intent").require('update').require('Event').optionally('time').optionally('Location').build())
    def updateevent(self,message):
        #AUTHORIZE
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    '/opt/mycroft/skills/regskill.hanabouzid/client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

        storage = Storage('info.dat')
        credentials = storage.get()
        if credentials is None or credentials.invalid == True:
            credentials = tools.run_flow(FLOW, storage)

        # Create an httplib2.Http object to handle our HTTP requests and
        # authorize it with our good Credentials.
        http = httplib2.Http()
        http = credentials.authorize(http)

        # Build a service object for interacting with the API. To get an API key for
        # your application, visit the Google API Console
        # and look at your application's credentials page.
        people_service = build(serviceName='people', version='v1', http=http)
        # To get the person information for any Google Account, use the following code:
        # profile = people_service.people().get('people/me', pageSize=100, personFields='names,emailAddresses').execute()
        # To get a list of people in the user's contacts,
        # results = service.people().connections().list(resourceName='people/me',personFields='names,emailAddresses',fields='connections,totalItems,nextSyncToken').execute()
        results = people_service.people().connections().list(resourceName='people/me', pageSize=100,
                                                             personFields='names,emailAddresses,events',
                                                             fields='connections,totalItems,nextSyncToken').execute()
        connections = results.get('connections', [])
        print("connections:", connections)
        utt = message.data.get("utterance", None)

        # extract the location
        #location = message.data.get("Location", None)
        print(utt)
        #listname1=utt.split(" named ")
        #listname2=listname1[1].split(" with ")
        #title =listname2[0]
        lister = utt.split(" starts ")
        lister2 = lister[1].split(" in ")
        location = lister2[1]
        print(location)
        strtdate = lister2[0]
        st = extract_datetime(strtdate)
        st = st[0] - self.utc_offset
        datestart = st.strftime('%Y-%m-%dT%H:%M:00')
        datestart += UTC_TZ
        print(datestart)
        lister3=lister[0].split(" the event ")
        title=lister3[1]
        print(title)
        # liste de contacts
        nameliste = []
        adsmails = []
        for person in connections:
            emails = person.get('emailAddresses', [])
            adsmails.append(emails[0].get('value'))
            names = person.get('names', [])
            nameliste.append(names[0].get('displayName'))
        # liste of meeting rooms
        namerooms = ['midoune room', 'aiguilles room', 'barrouta room', 'kantaoui room', 'gorges room', 'ichkeul room',
                     'khemir room', 'tamaghza room', 'friguia room', 'ksour room', 'medeina room', 'thyna room']
        emailrooms = ["focus-corporation.com_3436373433373035363932@resource.calendar.google.com",
                      "focus-corporation.com_3132323634363237333835@resource.calendar.google.com",
                      "focus-corporation.com_3335353934333838383834@resource.calendar.google.com",
                      "focus-corporation.com_3335343331353831343533@resource.calendar.google.com",
                      "focus-corporation.com_3436383331343336343130@resource.calendar.google.com",
                      "focus-corporation.com_36323631393136363531@resource.calendar.google.com",
                      "focus-corporation.com_3935343631343936373336@resource.calendar.google.com",
                      "focus-corporation.com_3739333735323735393039@resource.calendar.google.com",
                      "focus-corporation.com_3132343934363632383933@resource.calendar.google.com",
                      "focus-corporation.com_@resource.calendar.google.com",
                      "focus-corporation.com_@resource.calendar.google.com",
                      "focus-corporation.com_@resource.calendar.google.com"]

        events_result = service.events().list(calendarId='primary',timeMin=datestart,
                                              maxResults=1, singleEvents=True,
                                              orderBy='startTime', q=location).execute()
        events = events_result.get('items', [])
        if not events:
            self.speak_dialog("notEvent")

        for event in events:
            eventid = event['id']
            eventend=event['end']['dateTime']
            attendees=event['attendees']

        # freerooms
        freemails = []
        freerooms = []
        for i in range(0, len(emailrooms)):
            if self.freebusy(emailrooms[i],datestart,eventend,service):
                # la liste freerooms va prendre  les noms des salles free
                freerooms.append(namerooms[i])
                freemails.append(emailrooms[i])
        suggroom = freerooms[0]
        suggmail = freemails[0]
        ask = self.get_response('what do you want to update')
        if ask == "update title":
            newtitle = self.get_response('what is the new title?')
            eventup = {
                'summary': newtitle,
            }
        elif ask == "update description":
            newdesc = self.get_response('what is the new description?')
            eventup = {
                'description': newdesc,
            }
        elif ask == "update start date time ":
            newdatestrt = self.get_response('what is the new start date time?')
            st1 = extract_datetime(newdatestrt)
            st1 = st1[0] - self.utc_offset
            newdatestart = st1.strftime('%Y-%m-%dT%H:%M:00')
            newdatestart += UTC_TZ
            eventup = {
                'start': {
                    'dateTime': newdatestart,
                    'timeZone': 'America/Los_Angeles',
                },
            }
        elif ask == "update end date time ":
            newdatd = self.get_response('what is the new start date time?')
            et1 = extract_datetime(newdatd)
            et1 = et1[0] - self.utc_offset
            newdateend = et1.strftime('%Y-%m-%dT%H:%M:00')
            newdateend += UTC_TZ
            eventup = {
                'end': {
                    'dateTime': newdateend,
                    'timeZone': 'America/Los_Angeles',
                },
            }

        elif ask=="update location":
            newlocation = self.get_response('what is the new location?')
            for i in range(len(namerooms)) :
                if namerooms[i]==newlocation:
                    roommail= emailrooms[i]
            x = self.freebusy(roommail, datestart, eventend, service)
            if x == True:
                self.speak_dialog('roomfree', data={"newlocation": newlocation})
                email = {'email':roommail}
                attendees.append(email)
                eventup = {
                    'attendees': attendees,
                }

            else:
                self.speak_dialog('roombusy', data={"newlocation": newlocation})
                self.speak_dialog("suggestionroom", data={"suggroom": suggroom})
                x = self.get_response("Do you agree making a reservation for this meeting room")
                if x == "yes":
                    newlocation= suggroom
                    email = {'email':suggmail}
                    attendees.append(email)
                else:
                    s = ",".join(freerooms)
                    # print("les salles disponibles a cette date sont", freerooms)
                    self.speak_dialog("freerooms", data={"s": s})
                    room = self.get_response('which Room do you want to make a reservation for??')
                    for i in range(0, len(freerooms)):
                        if (freerooms[i] == room):
                            # ajouter l'email de room dans la liste des attendees
                            newlocation = room
                            email = {'email':freemails[i] }
                            attendees.append(email)
                eventup = {
                    'attendees': attendees,
                }
        elif ask == "delete attendee":
            name = self.get_response("what is the attendee's name?")
            for j, e in enumerate(nameliste):
                if name == e:
                    deletemail = adsmails[j]
                    email = {'email':deletemail}
            for i in attendees:
                if(cmp(attendees[i], email)==0):
                     del (attendees[i])
            eventup = {
                'attendees': attendees,
            }
        print(eventup)
        service.events().patch(calendarId='primary', eventId=eventid,
                                   sendNotifications=True, body=eventup).execute()
        self.speak_dialog("eventUpdated")



def create_skill():
    return UpdateEventSkill()