# bravialib
A Python library for talking to some Sony Bravia TVs, and an accompanying Alexa Skill to let you control the TV by voice.  If you like that sort of thing.

These scripts make use of the excellent Requests module.  You'll need to install that first.

## bravialib itself
This is a fairly simple library which allows you to "pair" the script with the TV and will then send cookie-authenticated requests to the TVs own web API to control pretty much everything.  You can:

* Set up the initial pairing between the script and the TV
* Retrieve system information from the TV (serial, model, mac addr etc)
* Enumerate the available TV inputs (HDMI1,2,3,4 etc)
* Switch to a given input
* Enumerate the remote control buttons
* Virtually press those buttons
* Find out what Smart TV apps are available
* Start those apps
* Enumerate the available DVB-T channels
* Switch to those channels
* Send Wake On Lan packets to switch the TV on from cold (assuming you've enabled that)
* A couple of convenience functions

The library tries to hide the complexity and pre-requisites and give you an easy to use API.

I built this for a couple of reasons:
1.  Because the TV had an undocumented API, and that tickles me
2.  I quite fancied hooking it up to Alexa for lols

Most of the information about how to talk to the TV's API came from looking at packet captures from the iPhone app "TV Sideview".

There is a script called ```testit.py``` that will give you a few clues about how to use it, but it's a bit of a mess. I've left a lot of comments in the code for the library which should help you.

Really, I think that this library should be imported in to a long-running process rather than be called every time you want to press a remote control button.  On a Raspberry Pi, Requests can take a while (a couple of seconds) to import, and then `bravialib` pre-populates a few data sources, and all of that takes time, like about 20 seconds - so you really don't want to use this library if you just want to fire a few remote control commands.  Also - be aware that the TV takes a long time to boot and accept commands.  From cold you're talking about a minute maybe two, it's really annoying.

## The aforementioned long running process - ```bravia_rest.py```

As the main library takes a while to start and needs a certain amount of data from the TV to work properly it really makes sense to start it up once and then leave it running as long as you can.  The ```bravia_rest.py``` script does exactly that, and also exposes some of the functionality as a very crude REST interface that you can easily hook it in to various home automation systems.

First you need to add the IP address and MAC address (needed to turn on the TV the first time the script is run, it can be discovered automatically if you just power the TV on for a few minutes before you run the script).

Then run ```bravia_rest.py```.

If this is the first time you have run it you will need to pair with the TV.  You will be told to point your browser at the IP address of the machine where the script is running on port 8090 (by default).  Doing this will make the script attempt to pair with the TV.  If it works you will see a PIN number on the TV screen, you will need to enter this in to the box in your browser.  After a few seconds, and with a bit of luck, pairing will now complete.  This shouldn't take too long.

If you are now paired, in your browser go to /dumpinfo for a view in to what the script knows about the TV.

Once everything is running you can ```POST``` to these URLs for things to happen (no body is required):

* ```/set/power/[on|off]``` - turns the telly on and off
* ```/set/send/<button>``` - e.g. mute, play, pause, up, down.  See dumpinfo for all the key names.
* ```/set/volumeup/3``` - turn the volume up 3 notches.  You MUST pass a number, even it it's just 1.
* ```/set/volumedown/1``` - as above.
* ```/set/loadapp/<app name>``` - e.g. Netflix, iplayer. Again /dumpinfo will show you what apps are available.
* ```/set/channel/<channel>``` - e.g. BBC ONE, BBC TWO
* ```/set/input/<input label>``` - You need to have given your inputs labels on the TV, then pass the label here.


## Hooking it up to Alexa
Now we can poke the TV through a simplified REST interface, it's much easier to hook in to other things, like Alexa for example.  Setting up a custom skill in AWS/Lambda is beyond the scope of what I can write up at lunchtime, I'm sure there are lots of other people who have done it better than I could.  You'll need to create a custom app and upload a **Python Deployment Package** to Lambda including my `lambda_function.py` script (see inside the `Alexa` directory), a ```secrets.py``` file with your info in it, a copy of the Requests library (you need to create a Python **Virtual Environment** - it's quite easy) and possibly a copy of your PEM for a self signed HTTPS certificate.  I've also included the skills data such as the utterances that I'm using.  These will need to be adjusted for your locale.

You can read more about Python deployment packages and AWS here:
http://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html
http://docs.aws.amazon.com/lambda/latest/dg/with-s3-example-deployment-pkg.html#with-s3-example-deployment-pkg-python

Here's how it works:

![block diagram](https://raw.githubusercontent.com/8none1/bravialib/master/docs/Alexa%20Bravia%20Block%20Diagram.png "Alexa Block Diagram")

1. You issue the command to Alexa: ```Alexa tell The TV to change to channel BBC ONE```.
2. Your voice is sent to AWS (the green lines) decoded and the utterances and intents etc are sent to the Lambda script.
3. The Lambda script works out what the requested actions are and sends them back out (the orange lines) to a web server running in your home (in my case a Raspberry Pi running Apache and the `bravia_proxy.py` script).  You need to make that Apache server accessible to the outside world so that AWS can POST data to it.  I would recommend that you configure Apache to use SSL and you put at least BASIC Auth in front of the proxy script.
4. The `bravia_proxy.py` script receives the POSTed form from AWS and in turn POSTs to the `bravia_rest.py` script having done a quick bit of sanity checking and normalisation.  The proxy and the rest scripts could live on different hosts (and probably should, there are no security considerations in either script - so ya know, don't use them.)
5. `bravia_rest.py` uses `bravialib` to poke the TV in the right way and returns back a yes or a no which then flows back (the blue lines) to AWS and your Lambda function.
6.  If everything worked you should hear "OK" from Alexa and your TV should do what you told it.


I could have put `bravia_rest.py` straight on the web an implemented some basic auth and SSL there - but I think this is something better handled by Apache (or whichever server you prefer), not some hacked up script that I wrote.



Caveats:
* It doesn't deal with the TV being off at all well at the moment.
* I don't know what happens when the cookies expire.
* I haven't done much testing.
* I have no idea what I'm doing.


