#!/usr/bin/python

from bravialib import Bravia
import sys

tv = Bravia('192.168.42.55')
a,b = tv.connect()

if b is True:
  print "I think I am connected"
  #print tv.cookies
  #print tv.DIAL_cookie
  #tv.get_system_info()
  print tv.system_info
  tv.get_dmr()
  #tv.do_remote_control("mute")
  tv.populate_apps_lookup()
  tv.get_app_status()
  #tv.load_app("BBC iPlayer")
  tv.get_input_map()
  #print tv.get_input_uri_from_label('MythTV')
  tv.set_external_input(tv.get_input_uri_from_label('Chromecast')) # You need to have labled your inputs for this to work
  #tv.get_channel_list()
  #chan  = tv.get_channel_uri('Channel 4')
  print chan
  tv.set_external_input(chan)
  print tv.dvbt_channels.keys()

  




elif b is False:
  if type(a) is NoneType:
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




