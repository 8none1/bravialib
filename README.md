# bravialib
Python 2 library for talking to some Sony Bravia TVs

This is a very early version but it does pretty much everything I need now.

Most of the information about how to talk to the TV's API came from looking at packet captures.

There is a script called "testit.py" that will give you a few clues about how to use it, but I've left a lot of comments in the code which should help you.

I think that really you should import this script in to a long running Python app rather than call it every time you want to change something on the TV as it takes a few seconds to load (on a Pi at least, Requests takes a while to load).  I'll be working on something with an HTTP server exposing a simple REST API which would be more suitable for integrating with a Home Automation system.

The first time you run the "connect" method you will need to be able to pass back the PIN code displayed on your TV.  After that it shouldn't prompt you again.

Caveats:
It doesn't deal with the TV being off at all well at the moment.
I don't know what happens when the cookies expire.
I have no idea what I'm doing.

