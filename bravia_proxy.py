#!/usr/bin/python

import requests
import os
import cgi
import json
import logging
import datetime



commander_endpoint = '<where bravia_rest.py is running>'
ask_app_id = '<your app id in case you want to check it'

ok = False

inputs = {'crime cast':'Chromecast', 'crime post':'Chromecast', 'me':'MythTV', 'week':'Wii',
          'P.S. 2':'PS2', 'my TV':'MythTV'}

channels = {'BBC world':'BBC ONE HD', 'BBC1':'BBC ONE HD', 'BBC2':'BBC TWO HD', 'BBC4':'BBC FOUR HD',
            'itv':'ITV HD', 'CBBC':'CBBC HD', 'cbeebies':'CBeebies HD', 'the date':'Dave',
            'channel 5':'Channel 5 HD', 'fill 4':'Film4', 'quest':'QUEST', 'Tony Pop':'Tiny Pop'}



logging.basicConfig(filename='/tmp/braviaproxy.log', level=logging.DEBUG)
def log(message):
  logging.debug(message)

def dispatch_to_commander(url):
  #return {'status':True}
  r = requests.post(commander_endpoint+'/'+url)
  if r.status_code == 200:
    return r.json()
  else:
    return {'status':False}


def failed():
  print json.dumps({'status':False})
  ok = False

print "Content-Type: application/json"
print

log("\n\n\nStarting now....")
log(datetime.datetime.now())

if "REQUEST_METHOD" in os.environ and os.environ['REQUEST_METHOD'] == "POST":
    form = cgi.FieldStorage()
    log(form)
    try:
      action = form['action'].value
      if 'value' in form:
          value = form['value'].value
      else: value = None
      log("Got data from form ok")
    except:
      failed()
      log("Failed trying to decode form data")
      sys.exit()
elif "REQUEST_METHOD" in os.environ.keys() and os.environ['REQUEST_METHOD'] is not "POST":
    # Unsupported method.
    failed()
    log("Got unsupported method")
else:
  # Here for cli testing only.  Can be removed or commented out later
  action = "Mute"
  value = None

log("action: "+action)
if value is not None: log("value: " + value)
action = action.lower()
if action == "power":
    if value == True:
        r = dispatch_to_commander('set/power/on')
    else:
        r = dispatch_to_commander('set/power/off')
elif action == "mute":
    r = dispatch_to_commander('set/send/mute')
elif action == "volup":
    r = dispatch_to_commander('set/volumeup/'+value)
elif action == "voldown":
    r = dispatch_to_commander('set/volumedown/'+value)
elif action == "play":
    r = dispatch_to_commander('set/send/play')
elif action == "pause":
    r = dispatch_to_commander('set/send/pause')
elif action == "stop":
    r = dispatch_to_commander('set/send/stop')
elif action == "exit":
    r = dispatch_to_commander('set/send/exit')
elif action == "app":
    # Translate Alexa in to apps
    translate = {'I player':'BBC iPlayer', 'Lodi player':'BBC iPlayer', 'amazon video':'Amazon Instant Video',
                'demand 5':'Demand 5'}
    if value in translate: value = translate[value]
    log("Recevied this app name")
    log(value)
    r = dispatch_to_commander('set/loadapp/'+value)
elif action == "channel":
    log("Received this channel")
    log(value)
    if value in inputs:
        # Sometimes it sends these through as channels instead of inputs
        value = inputs[value]
        r = dispatch_to_commander('set/input'+value)
    elif value in channels:
        value = channels[value]
        r = dispatch_to_commander('set/channel/'+value)
    else:
        r = dispatch_to_commander('set/channel/'+value)
elif action == "input":
    translate = {}
    if value in inputs: value = inputs[value]
    log("Received this input")
    log(value)
    r = dispatch_to_commander('set/input'+value)
else:
    log("Something went wrong parsing the actions")
    r = {'status':False}
response_dict = json.dumps(r)
log("sending back...")
log(response_dict)
print response_dict

log("Finished now....")
log(datetime.datetime.now())
log("\n\n\n")
