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
#
#
# TODO:
#       Move logging out of prints and in to logging
#

import requests
from requests.auth import HTTPBasicAuth
import json
from xml.dom import minidom
import socket
import struct
import time


class MockResponse(object):
    def __init__(self, status_code):
        self.status_code = status_code

class Bravia(object):
    def __init__(self, hostname = None, ip_addr = None, mac_addr = None):
        self.ip_addr = ip_addr
        self.hostname = hostname
        self.mac_addr = mac_addr # You don't *have* to specify the MAC address as once we are paired via IP we can find 
        # it from the TV but it will only be stored for this session.  If the TV is off and you are running this script
        # from cold - you will need the MAC to wake the TV up.
        if self.ip_addr is None and self.hostname is not None:
            self.ip_addr = self._lookup_ip_from_hostname(self.hostname)
        self.device_id = "WebInterface:001"
        self.nickname = "IoT Remote Controller Interface"
        self.endpoint = 'http://'+self.ip_addr
        self.cookies = None
        self.x_auth_psk = None # If you're using PSK instead of cookies you need to set this.
        self.DIAL_cookie = {}
        self.packet_id = 1
        self.device_friendly_name = ""
        self._JSON_HEADER = {'content-type':'application/json', 'connection':'close'}
        self._TIMEOUT = 10
        self.remote_controller_code_lookup = {}
        self.app_lookup = {}
        self.input_map = {}
        self.dvbt_channels = {}
        self.paired = False

    def _debug_request(self, r):
        # Pass a Requests response in here to see what happened
        print "\n\n\n"
        print "------- What was sent out ---------"
        print r.request.headers
        print r.request.body
        print "---------What came back -----------"
        print r.status_code
        print r.headers
        print r.text
        print "-----------------------------------"
        print "\n\n\n"

    def _lookup_ip_from_hostname(self, hostname):
        ipaddr = socket.gethostbyname(hostname)
        if ipaddr is not '127.0.0.1':
            return ipaddr
        else:
            # IP lookup failed
            return False

    def _build_json_payload(self,method, params = [], version="1.0"):
        return {"id":self.packet_id, "method":method, "params":params,
                "version":version}

    def is_available(self):
        # Try to find out if the TV is actually on or not.  Pinging the TV would require
        # this script to run as root, so not doing that.  This function return True or
        # False depending on if the box is on or not.
        payload = self._build_json_payload("getPowerStatus")
        try:
            # Using a shorter timeout here so we can return more quickly
            r = self.do_POST(url="/sony/system", payload = payload, timeout=2)
            data = r.json()
            if data.has_key('result'):
                if data['result'][0]['status'] == "standby":
                    # TV is in standby mode, and so not on.
                    return False
                elif data['result'][0]['status'] == "active":
                    # TV really is on
                    return True
                else:
                    # Assume it's not on.
                    print "Uncaught result"
                    return False
            if data.has_key('error'):
                if 404 in data['error']:
                    # TV is probably booting at this point - so not available yet
                    return False
                elif 403 in data['error']:
                    # A 403 Forbidden is acceptable here, because it means the TV is responding to requests
                    return True
                else:
                    print "Uncaught error"
                    return False
            return True
        except requests.exceptions.ConnectTimeout:
            print "No response, TV is probably off"
            return False
        except requests.exceptions.ConnectionError:
            print "TV is certainly off."
            return False
        except requests.exceptions.ReadTimeout:
            print "TV is on but not accepting commands yet"
            return False
        except ValueError:
            print "Didn't get back JSON as expected"
            # This might lead to false negatives - need to check
            return False
        

    def do_GET(self, url=None, headers=None, auth=None, cookies=None, timeout=None):
        if url is None: return False
        if url[0:4] != "http": url=self.endpoint+url
        if cookies is None and self.cookies is not None: cookies=self.cookies
        if self.x_auth_psk is not None: headers['X-Auth-PSK']=self.x_auth_psk
        if timeout is None: timeout = self._TIMEOUT
        if headers is None:
            r = requests.get(url, cookies=cookies, auth=auth, timeout=timeout)
        else:
            r = requests.get(url, headers=headers, cookies=cookies, auth=auth, timeout=timeout)
        return r

    def do_POST(self, url=None, payload=None, headers=None, auth=None, cookies=None, timeout=None):
        if url is None: return False
        if type(payload) is dict: payload = json.dumps(payload)
        if headers is None: headers = self._JSON_HEADER # If you don't want any extra headers pass in ""
        if cookies is None and self.cookies is not None: cookies=self.cookies
        if self.x_auth_psk is not None: headers['X-Auth-PSK']=self.x_auth_psk
        if timeout is None: timeout = self._TIMEOUT
        if url[0:4] != "http":  url = self.endpoint+url # if you want to pass just the path you can, otherwise pass a full url and it will be used
        self.packet_id += 1 # From packet captures, this increments on each request, so its a good idea to use this method all the time
        if auth is not None:
            r = requests.post(url, data=payload, headers=headers, cookies=cookies, auth=self.auth, timeout=timeout)
        else:
            r = requests.post(url, data=payload, headers=headers, cookies=cookies, timeout=timeout)
        print r
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
        if self.x_auth_psk is None: # We have not specified a PSK therefore we have to use Cookies
            payload = self._build_json_payload("actRegister",
                [{"clientid":self.device_id,"nickname":self.nickname},
                [{"value":"no","function":"WOL"},
                {"value":"no","function":"pinRegistration"}]])
            try:
                r = self.do_POST(url='/sony/accessControl', payload=payload)            
            except requests.exceptions.ConnectTimeout:
                print "No response, TV is probably off"
                return None, False
            except requests.exceptions.ConnectionError:
                print "TV is certainly off."
                return None, False

            if r.status_code == 200:
                # Rather handily, the TV returns a 200 if the TV is in stand-by but not really on :)
                try:
                    if "error" in r.json(): #.keys():
                        if "not power-on" in r.json()['error']:
                            # TV isn't powered up
                            r = self.wakeonlan()
                            print "TV not on! Have sent wakeonlan, probably try again in a mo."
                            # TODO: make this less crap
                            return None,False
                except:
                    raise
                
                # If we get here then We are already paired so get the new token
                self.paired = True
                self.cookies = r.cookies
                # Also add the /DIAL/ path cookie
                # Looks like requests doesn't handle two cookies with the same name ('auth') in one jar
                # so going to have a dict for the DIAL cookie and pass around as needed. :/
                a = r.headers['Set-Cookie'].split(';') # copy the cookie data headers
                for each in a:
                  if len(each) > 0:
                    b = each.split('=')
                    self.DIAL_cookie[b[0].strip()] = b[1]
            elif r.status_code == 401:
                print "We are not paired!"
                return r,False
            elif r.status_code == 404:
                # Most likely the TV hasn't booted yet
                print("TV probably hasn't booted yet")
                return r,False
            else: return None,False
                
        else: # We are using a PSK
            self.paired = True
            self.cookies = None
            self.DIAL_cookie = None
            r = None

        # Populate some data now automatically.
        print "Getting DMR info..."
        self.get_dmr()
        print "Getting sysem info..."
        self.get_system_info()
        print "Populating remote control codes..."
        self.populate_controller_lookup()
        print "Enumerating TV inputs..."
        self.get_input_map()
        print "Populating apps list..."
        self.populate_apps_lookup()
        print "Populating channel list..."
        self.get_channel_list()
        print "Matching HD channels..."
        self.create_HD_chan_lookups() # You might not want to do this if you don't use Freeview in the UK
        print "Done initialising TV data."
        return r,True

            
    def start_pair(self):
        # This should prompt the TV to display the pairing screen
        payload = self._build_json_payload("actRegister", 
            [{"clientid":self.device_id,"nickname":self.nickname},
            [{"value":"no","function":"WOL"}]])
        r = self.do_POST(url='/sony/accessControl', payload=payload)
        if r.status_code == 200:
            print "Probably already paired"
            return r,True
        if r.status_code == 401:
            return r,False
        else:
            return None,False
            
    def complete_pair(self, pin):
        # The user should have a PIN on the screen now, pass it in here to complete the pairing process
        payload = self._build_json_payload("actRegister", 
            [{"clientid":self.device_id, "nickname":self.nickname},
            [{"value":"no", "function":"WOL"}]])
        self.auth = HTTPBasicAuth('',pin) # Going to keep this in the object, just in case we need it again later
        r = self.do_POST(url='/sony/accessControl', payload=payload, auth=self.auth)
        if r.status_code == 200:
            print("have paired")
            self.paired = True
            # let's call connect again to get the cookies all set up properly
            a,b = self.connect()
            if b is True:
                return r,True
            else:  return r,False
        else:
            return None,False


    def get_system_info(self):
        payload = self._build_json_payload("getSystemInformation")
        r = self.do_POST(url="/sony/system", payload=payload)
        if r.status_code == 200:
            self.system_info = r.json()['result'][0]
            if self.mac_addr == None: self.mac_addr = self.system_info['macAddr']
            return self.system_info
        else:
            return False
            
    def get_input_map(self):
        payload = self._build_json_payload("getCurrentExternalInputsStatus")
        r = self.do_POST(url="/sony/avContent", payload=payload)
        if r.status_code == 200:
            for each in r.json()['result'][0]:
                self.input_map[each['title']] = {'label':each['label'], 'uri':each['uri']}
            return True
        else:
            return False
            
    def get_input_uri_from_label(self, label):
        for each in self.input_map:
            if self.input_map[each]['label'] == label:
                return self.input_map[each]['uri']
        print "Didnt match the input name."
        return None

    def set_external_input(self, uri):
        payload = self._build_json_payload("setPlayContent", [{"uri":uri}])
        r = self.do_POST(url="/sony/avContent", payload=payload)
        if r.status_code == 200:
            if "error" in r.json():
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
        r = self.do_POST(url='/sony/system', payload=payload)
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
        if action in self.remote_controller_code_lookup: #.keys():
            ircc_code = self.remote_controller_code_lookup[action]
        else: return False
        header = {'SOAPACTION': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'}
        url = "/sony/IRCC"
        body = '<?xml version="1.0"?>' # Look at all this crap just to send a remote control code...
        body +=   '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        body +=     '<s:Body>'
        body +=        '<u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">'
        body +=          '<IRCCCode>' + ircc_code + '</IRCCCode>'
        body +=        '</u:X_SendIRCC>'
        body +=     '</s:Body>'
        body +=   '</s:Envelope>'
        try:
            r = self.do_POST(url=url, payload=body, headers=header)
        except requests.exceptions.ConnectTimeout:
            print("Connect timeout error")
            r = MockResponse(200)
        except requests.exceptions.ConnectionError:
            print("Connect error")
            r = MockResponse(200)
        if r.status_code == 200:
            return True
        else:
            return False
   
    def populate_apps_lookup(self):
        # Interesting note:  If you don't do this (presumably just calling the
        # URL is enough) then apps won't actually launch and you will get a 404
        # error back from the TV.  Once you've called this it starts working.
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
            return True
        else:
            return False

    def load_app(self, app_name):
        # Pass in the name of the app, the most useful ones on my telly are:
        # "Amazon Instant Video" , "Netflix", "BBC iPlayer", "Demand 5"
        if self.app_lookup == {}: self.populate_apps_lookup() # This must happen before apps will launch
        try:
            app_id = self.app_lookup[app_name]['id']
        except KeyError:
            return False
        print "Trying to load app:", app_id
        headers = {'Connection':'close'}
        r = self.do_POST(url="/DIAL/apps/"+app_id, headers=headers,
            cookies=self.DIAL_cookie)
        print r.status_code
        print r.headers
        print r
        if r.status_code == 201:
            return True
        else:
            return False
            
    def get_app_status(self):
        payload = self._build_json_payload("getApplicationStatusList")
        r = self.do_POST(url="/sony/appControl", payload=payload)
        return r.json()

    def get_channel_list(self):
        # This only supports dvbt for now...
        # First, we find out how many channels there are
        payload = self._build_json_payload("getContentCount", 
            [{"target":"all", "source":"tv:dvbt"}], version="1.1")
        r = self.do_POST(url="/sony/avContent", payload=payload)
        chan_count = int(r.json()['result'][0]['count'])
        # It seems to only return the channels in lumps of 50, and some of those returned are blank?
        chunk_size = 50
        loops = int(chan_count / chunk_size) + (chan_count % chunk_size > 0) # Sneaky round up trick, the mod > 0 evaluates to int 1
        chunk = 0
        for x in range(loops):
            payload = self._build_json_payload("getContentList",
                [{"stIdx":chunk, "source":"tv:dvbt", "cnt":chunk_size,
                "target":"all" }], version="1.2")
            r = self.do_POST(url="/sony/avContent", payload=payload)
            a = r.json()['result'][0]
            for each in a:
                if each['title'] == "": continue # We get back some blank entries, so just ignore them
                if self.dvbt_channels.has_key(each['title']):
                    # Channel has already been added, we only want to keep the one with the lowest chan_num.
                    # The TV seems to return channel data for channels it can't actually receive (e.g. out of
                    # area local BBC channels). Trying to tune to these gives an error.
                    if int(each['dispNum']) > int(self.dvbt_channels[each['title']]['chan_num']):
                        # This is probably not a "real" channel we care about, so skip it.
                        continue
                        #self.dvbt_channels[each['title']] = {'chan_num':each['dispNum'], 'uri':each['uri']}
                else:
                    self.dvbt_channels[each['title']] = {'chan_num':each['dispNum'], 'uri':each['uri']}
            chunk += chunk_size
            
    def create_HD_chan_lookups(self):
        # This should probably be in the script that imports this library not in
        # the library itself, but I wanted this feature, so I'm chucking it in
        # here.  This probably only works for Freeview in the UK.
        # Use case to demonstrate why this is here:  You want to use Alexa to
        # switch the channel.  Naturally, you want the HD channel if there is 
        # one but you don't want to have to say "BBC ONE HD" because that would
        # be stupid.  So you just say "BBC ONE" and the script does the work to
        # find the HD version for you.
        for each in self.dvbt_channels.iteritems():
            hd_version = "%s HD" % each[0] # e.g. "BBC ONE" -> "BBC ONE HD"
            if hd_version in self.dvbt_channels:
                # Extend the schema by adding a "hd_uri" key
                self.dvbt_channels[each[0]]['hd_uri'] = self.dvbt_channels[hd_version]['uri']
        
    def get_channel_uri(self, title):
        if self.dvbt_channels == {}: self.get_channel_list()
        try:
            return self.dvbt_channels[title]['uri']
        except KeyError:
            return False

    def wakeonlan(self, mac=None):
        # Thanks: Taken from https://github.com/aparraga/braviarc/blob/master/braviarc/braviarc.py
        # Not using another library for this as it's pretty small...
        if mac is None and self.mac_addr is not None:
            mac = self.mac_addr
        print "Waking MAC: " + mac
        addr_byte = mac.split(':')
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
        
    def poweron(self):
        # Convenience function to switch the TV on and block until it's ready
        # to accept commands.
        if self.paired is False:
            print "You can only call this function once paired with the TV"
            return False
        elif self.paired is True:
            ready = False
            if self.is_available() is True:
                # If we're already on, return now.
                return True
            self.wakeonlan()
            for x in range(10):
                if self.is_available() is True:
                    print "TV now available"
                    return True
                else:
                    print "Didn't get a response. Trying again in 10 seconds. (Attempt "+str(x+1)+" of 10)" 
                    time.sleep(10)
            if ready is False:
                print "Couldnt connect in a timely manner. Giving up"
                return False
            else:
                return True

    def get_client_ip(self):
        host_ip = [(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        return host_ip

