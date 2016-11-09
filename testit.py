#!/usr/bin/python

from bravialib import Bravia
import sys
import time
import json

tv = Bravia('192.168.42.55', 'd8:d4:3c:f4:8e:5c')

# It's up to your script to decide if the TV should be switched on
# and to wait until it's ready to receive commands.  You can use the is_available method to help.

is_telly_on = tv.is_available()

if is_telly_on is False:
    # Let's try and switch the TV on with WOL...
    w = tv.wakeonlan() 
    #w = True
    # wakeonlan is a function to turn the TV on, /but/ you need a MAC address.
    # You can specify this when you init the class, or it will be filled
    # in for you once a sucessful connection is made to the TV and will persist
    # while you script is running.  And you will probably want a long running
    # script to control the TV rather than starting it up each time, because
    # that will be very slow ( > 2 seconds before you get a response on a pi)
    if w is False:
      # Wake On Lan failed, almost certainly because there is no MAC address
      print "I need the MAC address to wake the TV"
      sys.exit(1)

    # We've switched it on, now we need to wait for it to boot, this takes an annoyingly long time.
    for x in range(10): # Try 10 times to get a connection
        is_telly_on = tv.is_available()
        if is_telly_on is True:
            break # We've got a response, we can start talking to it now
        else:
            print "Attempt "+str(x+1)+" of 10."
            print "TV not responding.  Waiting for 10 seconds and trying again..."
            time.sleep(10)

if is_telly_on is False:
    # We've been round the loop of trying to connect and it still hasn't worked.
    # So we give up trying...
    print "I wasn't able to connect to the TV despite trying to switch it on."
    print "Sorry it didn't work out."
    sys.exit(1)
    

# If we get here, then we should be good to go...

a,b = tv.connect()

if b is True:
  print "I think I am connected"
  #print tv.cookies
  #print tv.DIAL_cookie
  #tv.get_system_info()
  #print tv.system_info
  #tv.get_dmr()
  #tv.do_remote_control("power off")
  #tv.populate_apps_lookup()
  #print tv.get_app_status()
  #tv.load_app("BBC iPlayer")
  #tv.get_input_map()
  #print tv.get_input_uri_from_label('MythTV')
  tv.get_channel_list()
  #tv.set_external_input(tv.get_input_uri_from_label('Chromecast')) # You need to have labled your inputs for this to work
  #print "\n\n\n"
  tv.create_HD_chan_lookups()
  #print json.dumps(tv.dvbt_channels, sort_keys=True, indent=4)
  #chan  = tv.get_channel_uri('BBC ONE HD')
  #print chan
  #tv.set_external_input(chan)
  #print tv.dvbt_channels.keys()
  print json.dumps(tv.remote_controller_code_lookup, sort_keys=True, indent=4)

  




elif b is False:
  if type(a) is None:
    print "I couldn't connect to the tv at all"
    sys.exit()
  elif type(a) is not None:
    try:
      if a.status_code == 401:
        print "I need to pair..."
        tv.start_pair()
        pin = raw_input("Please enter PIN: ")
        y,z = tv.complete_pair(pin)
        print "Ok, try me again"
    except:
        print "Something else went wrong"




