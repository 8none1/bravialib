#!/usr/bin/python
#
# Provides a simple REST interface to interact with certain Bravia TVs
# Uses bravialib from: https://github.com/8none1/bravialib
#
#

import bravialib
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
import json
import time
import sys
import urllib


PORT_NUMBER = 8090

class MockResponse(object):
    def __init__(self, status_code):
        self.status_code = status_code


class BraviaHandler(BaseHTTPRequestHandler):
    sys_version = "0.00"
    server_version = "Whizzy Labs Bravia Server/"

    def _send_headers(self, code, content_type, content_length=None):
        self.send_response(code)
        self.send_header("Content-Type",content_type)
        self.send_header("Access-Control-Allow-Origin", "*")        
        if content_length is not None:
            self.send_header("Content-Length",content_length)
        self.end_headers()

    def send_reply(self, code, payload, content_type="application/json"):
        if type(payload) is dict:  payload = json.dumps(payload)
        content_len = len(payload)
        self._send_headers(code, content_type, content_len)
        self.wfile.write(payload)

    def do_GET(self):
        print self.path
        if tv.paired is False:
            if self.path == "/":
                self.start_pairing()
            elif self.path[0:4] == "/pin":
                pin = self.path.split("=")[-1]
                a = self.enter_pin(pin)
        else:
            if self.path == "/":
                icon = "http://"+tv.ip_addr+":52323/MediaRenderer_HM_ME_120x120.png"
                html = """
                        <html>
                            <head>
                                <link rel="icon" type="image/png" href="{0}" />
                            </head>
                            <body>
                                <center>
                                    <img src="{0}" />
                                </center>
                                <hr />
                                <p>
                                    The connection to the TV is established.
                                </p>
                            </body>
                        </html>
                """
                self.send_reply(200, html.format(icon), "text/html")
            elif self.path == "/dumpinfo":
                html = "<html><head></head><body>"
                html += "<pre>"
                html += json.dumps(tv.system_info, sort_keys=True, indent=4)
                html +="</pre><pre>"
                html +=json.dumps(tv.input_map, sort_keys=True, indent=4)
                html +="</pre><pre>"
                html +=str(tv.dmr_data)
                html +="</pre><pre>"
                html +=json.dumps(tv.remote_controller_code_lookup, sort_keys=True, indent=4)
                html +="</pre><pre>"
                html +=json.dumps(tv.app_lookup, sort_keys=True, indent=4)
                html +="</pre><pre>"
                html +=json.dumps(tv.dvbt_channels, sort_keys=True, indent=4)
                html += "</pre></body></html>"
                self.send_reply(200,html, "text/html")
                
            else:
                html = """
                        <html>
                            <head>
                            </head>
                            <body>
                                <hr />
                                <p>
                                    The connection to the TV is established.
                                </p>
                            </body>
                        </html>                   
                """

    def do_POST(self):
        # API ideas:
        #   Power On
        #   Power Off
        #   Mute
        #   Volume Up <n>
        #   Volume Down <n>
        #   Play
        #   Pause
        #   Stop
        #   App - iPlayer
        #   App - Netflix
        #   Channel - <name>
        #   Input - <name> 
        #   Exit
        #
        #
        # REST interface spec:
        #  /set/<function>/<argument>
        # /set/send/play
        # /set/power/on
        # /set/volumeup/1
        # /set/volumedown/3
        # /set/power/off
        # /set/app/iplayer
        if tv.paired is not True:
            print "POST request received but TV is not paired."
            self.send_response(401,{"status":False})
            return None
        request = self.path.split('/')
        print request
        if len(request) != 4:
            self.send_response(400,{'status':False})
            return None
        if request[1] != "set":
            self.send_response(400,{'status':False})
            return None
        fn = getattr(self, "POST_%s" % (request[2]), None)
        if not fn: raise Exception("Couldnt match function")
        code, data = fn(request[3])
        self.send_reply(code, data)
        
    def POST_power(self, action):
        print action
        if action == "on":
            a = tv.poweron()
            if a is True:
                return(200, {"status":True})
            else:
                return(500, {"status":False})
        if action == "off":
            a = tv.do_remote_control("poweroff")
            if a is True:
                return(200,{"status":True})
            else:
                return(500, {"status":False})
                
    def POST_send(self, key):
        a = tv.do_remote_control(key)
        if a is True:
            return(200, {"status":True})
        else:
            return(500, {"status":False})

    def POST_volumeup(self, count):
        count = int(count)
        for a in range(count):
            r = tv.do_remote_control("volumeup")
        if r is True:
            return(200, {"status":True})
        else:
            return(500, {"status":False})

    def POST_volumedown(self, count):
        count = int(count)
        for a in range(count):
            r = tv.do_remote_control("volumedown")
        if r is True:
            return(200, {"status":True})
        else:
            return(500, {"status":False})

    def POST_loadapp(self, appname):
        tv.poweron()
        appname = urllib.unquote(appname).decode('utf8')        
        a = tv.load_app(appname)
        if a is True:
            return(200, {"status":True})
        else:
            return(500, {"status":False})

    def POST_channel(self, channame):
        tv.poweron()
        channame = urllib.unquote(channame).decode('utf8')
        try:
            data = tv.dvbt_channels[channame]
        except KeyError:
            # Channel does not exist in our list
            print "Channel '"+channame+"' not found in list."
            return(500, {'status':False})
        if 'hd_uri' in data: uri = data['hd_uri']
        else: uri = data['uri']
        print "Channel URI is: " + uri
        a = tv.set_external_input(uri)
        if a is True: return(200, {"status":True})
        else: return(500, {"status":False})

    def POST_input(self, inputname):
        inputname = urllib.unquote(inputname).decode('utf8')        
        tv.poweron()
        uri = tv.get_input_uri_from_label(inputname)
        if uri is not None:
            print "URI is: " + uri
            a = tv.set_external_input(uri)
        else:
            a = False
        if a is True: return(200, {"status":True})
        else: return(500, {"status":False})

    def POST_wakeonlan(self, mac):
        mac = urllib.unquote(mac).decode('utf8')
        a = tv.wakeonlan(mac)
        if a is True:
            return(200,{"status":True})
        else:
            return(500, {"status":False})


    def start_pairing(self):
        response, state = tv.connect()
        if type(response) is not None:
            try:
                if response.status_code == 401:
                    # Ok, we do need to pair, so...
                    tv.start_pair()
                    icon = "http://"+tv.ip_addr+":52323/MediaRenderer_HM_ME_120x120.png"
                    html = """
                    <html>
                        <head>
                            <link rel="icon" type="image/png" href="{0}" />
                        </head>
                        <body>
                            <center>
                                <img src="{0}" />
                            </center>
                            <hr />
                            <h1>Enter the PIN number displayed on your TV and click submit.</h1>
                            <form action="pin" method="get">
                                PIN: <input type="text" name="pin">
                                <input type="submit" value="Submit">
                            </form>
                        </body>
                    </html>
                    """
                    self.send_reply(200, html.format(icon), "text/html")
                elif response.status_code == 200:
                    html = """<html><body><h1>Seem to be paired now</h1></body></html>"""
                    self.send_reply(200, html, "text/html")
                else:
                    html = """<html><body><h1>Something went wrong here.  Sorry.</h1><h2>Response code problem</h2></body></html>"""
                    self.send_reply(500, html, "text/html")
            except:
                html = """<html><body><h1>Something went wrong here.  Sorry.</h1><h2>Exception</h2></body></html>"""
                self.send_reply(500, html, "text/html")
        else:
            html = """<html><body><h1>Something went wrong here.  Sorry.</h1><h2>Response type problem</h2></body></html>"""
            self.send_reply(500, html, "text/html")

    def enter_pin(self, pin):
        # This might take a while to return because it's looking up all the info from the TV.
        # If we start getting timeouts on this, then, do this first..
        #self.send_reply(200, "Trying to do it now.  Maybe we could meta refesh this page?")
        r,status = tv.complete_pair(pin)
        if status is True:
            data = json.dumps(tv.system_info, sort_keys=True, indent=4)
            icon = "http://"+tv.ip_addr+":52323/MediaRenderer_HM_ME_120x120.png"
            html = """
            <html>
                <head>
                    <link rel="icon" type="image/png" href="{0}" />
                </head>
                <body>
                    <h1>Sucessfully pair to the TV</h1>
                    <hr />
                    <h2> System info:</h2>
                    <pre>{1}</pre>
                </body>
            </html>
            """
            self.send_reply(200, html.format(icon,data), "text/html")
        else:
            self.send_reply(500, "Something went wrong in the pairing process.", "text/text")
        
        
        
                     
if __name__ == "__main__":
    tv = bravialib.Bravia('192.168.42.55','d8:d4:3c:f4:8e:5c')
    tv.device_id = "WhizzyLabsController:001"
    tv.nickname = "Whizzy Remote Control"
    # The TV needs to be on when we run this for the first time...
    if not tv.is_available():
        tv.wakeonlan()
        print "TV needs to be on when this script is initialised. Sent WOL."
        for x in range(10):
            # The TV takes ages to boot
            telly_on = tv.is_available()
            if telly_on is True:
                break
            else:
                print "Attempt %s of 10" % str(x+1)
                print "TV is not responding. Waiting for 10 seconds and trying again..."
                time.sleep(10)

        if telly_on is False:
            # TV still not available after retrying
            print "Sorry, I couldn't connect to the TV."
            print "Maybe it's not on, maybe the IP address is wrong, maybe it's an unsupported model."
            sys.exit(1)
            
    if tv.is_available():
        # In theory the TV is powered on and responding to requests, but
        # we don't know if we are actually paired or not yet. This should
        # be good enough to start the HTTP server and the rest can be done
        # from there.
        try:
            print "Starting server..."
            server = HTTPServer(('', PORT_NUMBER), BraviaHandler)
            response,state = tv.connect()
            if state is True:
                print "Already paired and connected to the TV."
                print "Ready to serve requests."
            else:
                print "TV is on and accepting requests, but I don't seem to be paired."
                print "You should now point a browser at:"
                url = "http://" + tv.get_client_ip() + ":" + str(PORT_NUMBER) + "/"
                print "\t" + url
                print "to initialise and complete pairing."
            server.serve_forever()
        except:
            print "Something happened, stopping."
            server.socket.close()
            raise

