#!/usr/bin/python
#
#  bravialib - Will Cooke - Whizzy Labs - @8none1
#  http://www.whizzy.org
#  Copyright Will Cooke 2016.  Released under the GPL.
#
#
# My attempt to talk to the Sony Bravia web API.
#
# This is designed to be used by a long running process
# So there is a potentially slow start-up time but then it should be quick enough
# at the expense of some memory usage
#
# The TV will give you access based on the device_id and nickname once you are authorised I think.
# The TV will need to be already switched on for this to work.
#
#
# Thanks:
#   https://github.com/aparraga/braviarc/
#   https://docs.google.com/viewer?a=v&pid=sites&srcid=ZGlhbC1tdWx0aXNjcmVlbi5vcmd8ZGlhbHxneDoyNzlmNzY3YWJlMmY1MjZl
#   
# Some useful resources:
#   A tidied up packet capture I did from the iphone app:  http://paste.ubuntu.com/23417464/plain/


import requests
from requests.auth import HTTPBasicAuth
import json
from xml.dom import minidom
import socket
import struct



class Bravia(object):
    def __init__(self, ip_addr):
        self.ip_addr = ip_addr
        self.mac_addr = None # You don't *have* to specify the MAC address as once we are paired via IP we can find 
        # it from the TV but it will only be stored for this session.  If the TV is off and you are running this script
        # from cold - you will need the MAC to wake the TV up.
        self.device_id = "WebInterface:001"
        self.nickname = "IoT Remote Controller Interface"
        self.endpoint = 'http://'+self.ip_addr
        self.cookies = None
        self.DIAL_cookie = {}
        self.packet_id = 1
        self.device_friendly_name = ""
        self._JSON_HEADER = {'content-type':'application/json', 'connection':'close'}
        self._TIMEOUT = 10
        self.remote_controller_code_lookup = {}
        self.app_lookup = {}
        self.input_map = {}
        self.dvbt_channels = {}

    def _debug_request(self, r):
        # Pass a Requests response in here to see what happened
        print "\n\n------What came back ----------"
        print r.status_code
        print r.headers
        print r.text
        print "------- What was sent out ---------"
        print r.request.headers
        print r.request.body
        print "------------X------------------"
        print "\n\n\n\n\n"        
        
        
    def _build_json_payload(self,method, params = [], version="1.0"):
        return {"id":self.packet_id, "method":method, "params":params, "version":version}
            

    def do_GET(self, url=None, headers=None, auth=None, cookies=None):
        if url is None: return False
        if url[0:4] != "http": url=self.endpoint+url
        if cookies is None and self.cookies is not None: cookies=self.cookies
        if headers is None:
            r = requests.get(url, cookies=cookies, auth=auth, timeout=self._TIMEOUT)
        else:
            r = requests.get(url, headers=headers, cookies=cookies, auth=auth, timeout=self._TIMEOUT)
        return r

    def do_POST(self, url=None, payload=None, headers=None, auth=None, cookies=None):
        if url is None: return False
        if type(payload) is dict: payload = json.dumps(payload)
        if url[0:4] != "http":  url = self.endpoint+url # if you want to pass just the path you can, otherwise pass a full url and it will be used
        self.packet_id += 1 # From packet captures, this increments on each request, so its a good idea to use this method all the time
        if cookies is None and self.cookies is not None:  cookies = self.cookies # If you dont give me cookies and I have some, use them
        if cookies is None and self.cookies is None:
            # We haven't got any cookies yet, and so are not authenticated
            # in which case this should be the only type of POST going on now
            # One with the BasicAuth details in order to get a cookie
            r = requests.post(url=url, data=payload, headers=headers, auth=auth, timeout=self._TIMEOUT)
            return r
        else:
            if headers == None:  # I wonder if I pass "headers=None" to requests it will break?  Do this until I test.
                r = requests.post(url, data=payload, cookies=cookies, timeout=self._TIMEOUT)
                return r
            else:
                r = requests.post(url, data=payload, headers=headers, cookies=cookies, timeout=self._TIMEOUT)
                return r

    def connect(self):
        # TODO: What if the TV is off and we can't connect?
        #
        # From looking at packet captures what seems to happen is:
        #  1. Try and connect to the accessControl interface with the "pinRegistration" part in the payload
        #  2. If you get back a 200 *and* the return data looks OK then you have already authorised
        #  3. If #2 is a 200 you get back an auth token.  I think that this token will expire, so we might need to
        #     re-connect later on - given that this script will be running for a long time. Hopefully you won't
        #     need to get a new PIN number ever.
        #  4. If #2 was a 401 then you need to authorise, and then you do that by sending the PIN on screen as 
        #     a base64 encoded BasicAuth using a blank username (e.g. "<username>:<password" -> ":1234")
        #     If that works, you should get a cookie back.
        #  5. Use the cookie in all subsequent requests.  Note there is an issue with this.  The cookie is for
        #     path "/sony/" *but* the Apps are run from a path "/DIAL/sony/" so I try and fix this by adding a
        #     second cookie with that path and the same auth data.
        #payload = { "id" : self.packet_id,
        #            "method" : "actRegister",
        #            "params" : [ {"clientid" : self.device_id,
        #                          "nickname" : self.nickname},
        #                          [ {"value" : "no",
        #                             "function" : "WOL"},
        #                            {"value" : "no",
        #                             "function" : "pinRegistration"} ]
        #                       ],
        #            "version" : "1.0"}
        payload = self._build_json_payload("actRegister", [{"clientid":self.device_id,"nickname":self.nickname},[{"value":"no","function":"WOL"},{"value":"no","function":"pinRegistration"}]])
        headers = self._JSON_HEADER
        r = self.do_POST(url='/sony/accessControl', payload=payload, headers=headers)
        if r.status_code == 200:
            # Rather handily, the TV returns a 200 if the TV is in stand-by but not really on :)
            try:
                if "error" in r.json().keys():
                    if "not power-on" in r.json()['error']:
                        # TV isn't powered up
                        r = self.wakeonlan()
                        print "TV not on!. Have sent wakeonlan, probably try again in a mo."
                        # TODO: make this less crap
            except:
                raise
            
            # If we get here then We are already paired so get the new token
            self.cookies = r.cookies
            # Also add the /DIAL/ path cookie
            # Looks like requests doesn't handle two cookies with the same name ('auth') in one jar
            # so going to have a dict for the DIAL cookie and pass around as needed. :/
            a = r.headers['Set-Cookie'].split(';') # clone the cookie from the response headers
            for each in a:
              if len(each) > 0:
                b = each.split('=')
                self.DIAL_cookie[b[0].strip()] = b[1]
            # Populate some data now automatically.  I don't do everything here, but if you try a method which has a pre-requisite then it /should/ handle it automatically
            self.get_system_info()
            self.populate_controller_lookup()
            return r,True
        elif r.status_code == 401:
            return r,False
        elif r.status_code == 404:
            # Most likely the TV hasn't booted yet
            print("TV probably hasn't booted yet")
            return r,False
        else: return None,False
            
    def start_pair(self):
        # This should prompt the TV to display the pairing screen
        #payload = { "id" : self.packet_id,
        #            "method" : "actRegister",
        #            "params" : [ {"clientid":self.device_id,
        #                          "nickname":self.nickname},
        #                          [{"value":"no","function":"WOL"}]
        #                       ],
        #            "version" : "1.0"}
        payload = self._build_json_payload("actRegister", [{"clientid":self.device_id,"nickname":self.nickname},[{"value":"no","function":"WOL"}]])
        headers = self._JSON_HEADER
        r = self.do_POST(url='/sony/accessControl', payload=payload, headers=headers)
        if r.status_code == 200:
            return r,True
        if r.status_code == 401:
            return r,False
        else:
            return None,False
            
    def complete_pair(self, pin):
        # The user should have a PIN on the screen now, pass it in here to complete the pairing process
        #payload = { "id" : self.packet_id,
        #            "method" : "actRegister",
        #            "params" : [ {"clientid" : self.device_id,
        #                           "nickname" : self.nickname},
        #                           [{"value" : "no",
        #                             "function" : "WOL"}]
        #                       ],
        #            "version" : "1.0"
        #          }
        payload = self._build_json_payload("actRegister", [{"clientid":self.device_id, "nickname":self.nickname},[{"value":"no", "function":"WOL"}]])
        auth = HTTPBasicAuth('',pin)
        headers = self._JSON_HEADER
        r = self.do_POST(url='/sony/accessControl', payload=payload, headers=headers, auth=auth)
        if r.status_code == 200:
            print("have paired")
            print(r.status_code)
            print(r.text)
            # let's call connect again to get the cookies all set up properly
            a,b = self.connect()
            if b is True:
                return r,True
            else:  return r,False
        else:
            return None,False


    def get_system_info(self):
        payload = self._build_json_payload("getSystemInformation")
        headers = self._JSON_HEADER
        r = self.do_POST(url="/sony/system", payload=payload, headers=headers, cookies=self.cookies)
        if r.status_code == 200:
            self.system_info = r.json()['result'][0]
            if self.mac_addr == None: self.mac_addr = self.system_info['macAddr']
            return self.system_info
        else:
            return False
            
    def get_input_map(self):
        payload = self._build_json_payload("getCurrentExternalInputsStatus")
        headers = self._JSON_HEADER
        r = self.do_POST(url="/sony/avContent", payload=payload, headers=headers, cookies=self.cookies)
        if r.status_code == 200:
            for each in r.json()['result'][0]:
                self.input_map[each['title']] = {'label':each['label'], 'uri':each['uri']}
            return True
        else:
            return False
            
    def get_input_uri_from_label(self, label):
        for each in self.input_map.keys():
            if self.input_map[each]['label'] == label:
                return self.input_map[each]['uri']

    def set_external_input(self, uri):
        payload = self._build_json_payload("setPlayContent", [{"uri":uri}])
        headers = self._JSON_HEADER
        r = self.do_POST(url="/sony/avContent", payload=payload, headers=headers, cookies=self.cookies)
        if r.status_code == 200:
            if "error" in r.json().keys():
                # Something didnt work.  The JSON will tell you what.
                return False
            else:
                return True
        else:
            return False
        

    def get_dmr(self):
        r = self.do_GET('http://'+self.ip_addr+':52323/dmr.xml')
        self.dmr_data = minidom.parseString(r.text)
        # XML.  FFS. :(
        self.device_friendly_name = self.dmr_data.getElementsByTagName('friendlyName')[0].childNodes[0].data
        a = self.dmr_data.getElementsByTagNameNS('urn:schemas-sony-com:av','X_IRCCCode')
        for each in a:
            name = each.getAttribute("command")
            value = each.firstChild.nodeValue
            self.remote_controller_code_lookup[name.lower()] = value
        # Not much more interesting stuff here really, but see: https://aydbe.com/assets/uploads/2014/11/json.txt
        # and https://github.com/bunk3r/braviapy
        # Maybe /sony/system/setLEDIndicatorStatus would be fun?
        #"setLEDIndicatorStatus"  -> {"mode":"string","status":"bool"}
        # Maybe mode is a hex colour? and bool is on/off?

    def populate_controller_lookup(self):
        payload = self._build_json_payload("getRemoteControllerInfo")
        headers = self._JSON_HEADER
        r = self.do_POST(url='/sony/system', payload=payload, headers=headers, cookies=self.cookies)
        if r.status_code == 200:
            for each in r.json()['result'][1]:
                self.remote_controller_code_lookup[each['name'].lower()] = each['value']
            return True
        else:
            return False

    def do_remote_control(self,action):
        # Pass in the action name, such as:
        #       "PowerOff" "Mute" "Pause" "Play"
        # You can probably guess what these would be, but if not:
        # print <self>.remote_controller_code_lookup
        action = action.lower()
        if action in self.remote_controller_code_lookup.keys():
            ircc_code = self.remote_controller_code_lookup[action]
        else: return False
        header = {'SOAPACTION': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'}
        url = "/sony/IRCC"
        body = '<?xml version="1.0"?>' # Just wow...
        body +=   '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        body +=     '<s:Body>'
        body +=        '<u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">'
        body +=          '<IRCCCode>' + ircc_code + '</IRCCCode>'
        body +=        '</u:X_SendIRCC>'
        body +=     '</s:Body>'
        body +=   '</s:Envelope>'
        r = self.do_POST(url=url, payload=body, headers=header, cookies=self.cookies)
        if r.status_code == 200:
            return True
        else:
            return False
   
    def populate_apps_lookup(self):
        # Interesting note:  If you don't do this (presumably just calling the URL is enough) then apps won't
        # actually launch and you will get a 404 error back from the TV.  Once you've called this it starts
        # working.
        self.app_lookup={}
        r = self.do_GET(url="/DIAL/sony/applist", cookies=self.DIAL_cookie)
        if r.status_code == 200:
            app_xml_data = minidom.parseString(r.text.encode('utf-8'))
            for each in app_xml_data.getElementsByTagName('app'):
                appid = each.getElementsByTagName('id')[0].firstChild.data
                appname = each.getElementsByTagName('name')[0].firstChild.data
                try: iconurl = each.getElementsByTagName('icon_url')[0].firstChild.data
                except: iconurl = None
                self.app_lookup[appname] = {'id':appid, 'iconurl':iconurl}
                #print appid, appname
            return True
        else:
            return False

    def load_app(self, app_name):
        # Pass in the name of the app, the most useful ones on my telly are:
        # "Amazon Instant Video" , "Netflix", "BBC iPlayer", "Demand 5"
        if self.app_lookup == {}: self.populate_apps_lookup() # This must happen before apps will launch
        app_id = self.app_lookup[app_name]['id']
        print "Trying to load app:", app_id
        headers = {'Connection':'close'}
        r = self.do_POST(url="/DIAL/apps/"+app_id, headers=headers, cookies=self.DIAL_cookie)
        if r.status_code == 201:
            return True
        else:
            return False
            
    def get_app_status(self):
        payload = self._build_json_payload("getApplicationStatusList")
        headers = self._JSON_HEADER
        r = self.do_POST(url="/sony/appControl", payload=payload, headers=headers, cookies=self.cookies)
        return r.text

    def get_channel_list(self):
        # This only supports dvbt for now...
        # First, we find out how many channels there are
        payload = self._build_json_payload("getContentCount", [{"target":"all", "source":"tv:dvbt"}], version="1.1")
        headers = self._JSON_HEADER
        r = self.do_POST(url="/sony/avContent", payload=payload, headers=headers)
        chan_count = int(r.json()['result'][0]['count'])
        # It seems to only return the channels in lumps of 50, and some of those returned are blank?
        loops = int(chan_count / 50) + (chan_count % 50 > 0)
        chunk = 0
        for x in range(loops):
            payload = self._build_json_payload("getContentList", [{"stIdx":chunk, "source":"tv:dvbt", "cnt":50, "target":"all" }], version="1.2")
            r = self.do_POST(url="/sony/avContent", payload=payload, headers=headers)
            a = r.json()['result'][0]
            for each in a:
                self.dvbt_channels[each['title']] = {'chan_num':each['dispNum'], 'uri':each['uri']}
            chunk += 50
        
    def get_channel_uri(self, title):
        if self.dvbt_channels == {}: self.get_channel_list()
        chan = self.dvbt_channels[title]['uri']
        return chan

    def wakeonlan(self):
        # Thanks: Taken from https://github.com/aparraga/braviarc/blob/master/braviarc/braviarc.py
        # Not using another library for this as it's pretty small...
        if self.mac_addr is not None:
            addr_byte = self.mac_addr.split(':')
            hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16),
                                  int(addr_byte[1], 16),
                                  int(addr_byte[2], 16),
                                  int(addr_byte[3], 16),
                                  int(addr_byte[4], 16),
                                  int(addr_byte[5], 16))
            msg = b'\xff' * 6 + hw_addr * 16
            socket_instance = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            socket_instance.sendto(msg, ('<broadcast>', 9))
            socket_instance.close()
            return True
        else:
            return False


        
