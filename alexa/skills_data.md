#Invocation Name
the tv


#Intent Schema
{"intents": [
    {"intent": "AMAZON.HelpIntent"},
    {"intent": "AMAZON.CancelIntent"},
    {"intent": "AMAZON.StopIntent"},
    {"intent" : "PowerIntent",
        "slots" : [{"name":"PowerStates","type":"PowerStates"}]},
    {"intent": "MuteIntent"},
    {"intent" : "VolumeUpIntent",
        "slots":[{"name":"VolNum","type" : "AMAZON.NUMBER"}]},
    {"intent" : "VolumeDownIntent",
        "slots" : [{"name":"VolNum","type" : "AMAZON.NUMBER"}]},
    {"intent" : "PlayIntent"},
    {"intent" : "PauseIntent"},
    {"intent" : "StopIntent"},
    {"intent" : "ExitIntent"},
    {"intent" : "LoadAppIntent",
        "slots" : [{"name":"Apps", "type":"Apps"}]},
    {"intent" : "SetChannelIntent",
        "slots": [{"name":"Channels", "type":"Channels"}]},
    {"intent" : "SetInputIntent", 
        "slots" : [{"name":"Inputs", "type":"Inputs"}]}  
]}


#Custom Slots
###Apps:
    iPlayer
    Amazon Video
    Netflix
    Demand 5
    Plex
###Channels:
    Yesterday
    Classic FM
    Spike
    Film4+1
    ITV4+1
    BBC NEWS
    Channel 5+1
    5STAR
    Channel 4+1
    truTV
    KISSTORY
    ITV2
    My5
    BT Showcase
    ITV HD
    CBBC HD
    ITV +1
    Travel Channel
    Magic
    5 USA
    More 4
    Challenge
    Movie Mix
    Absolute Radio
    Film4
    BBC TWO
    BBC ONE HD
    Dave ja vu
    ITV3+1
    BBC Radio 4
    BBC 6 Music
    BBC Radio 1
    BBC Radio 3
    BBC Radio 2
    POP
    Children's Section
    Create & Craft
    BBC R1X
    movies4men
    Dave
    QUEST
    E4
    Sky News
    Channel 4+1 HD
    CBS Drama
    Drama
    Kerrang!
    CBS Action
    Blaze+1
    QUEST+1
    Home
    Channel 5 HD
    Really
    ITV4
    4seven
    ITV3
    BBC FOUR HD
    Channel 4 HD
    BBC NEWS HD
    The Hits Radio
    BBC ONE East W
    BBC FOUR
    CBS Reality
    CBBC
    4Music
    BBC Radio 4 Ex
    ITV2 +1
    VIVA
    E4+1
    The Craft Channel
    Front Runner
    ITV
    ITVBe
    Channel 4
    Channel 5
    Vintage TV
    Horror Channel
    4seven HD
    CITV
    Capital
    BBC TWO HD
    5STAR+1
    CBeebies
    5USA+1
    True Entertainment
    Tiny Pop
    Food Network
    Pick
    CBS Reality +1
    CBeebies HD
    Planet Knowledge
###Inputs:
    P.S.2
    PS 2
    PS Two
    Playstation 2
    Playstation Two
    P.S.3
    PS 3
    PS Three
    Playstation 3
    Playstation Three
    Wii
    Chromecast
    Myth
    Myth tv

###PowerStates:
    On
    Off

#Sample Utterances
PowerIntent to switch {PowerStates}
PowerIntent to power {PowerStates}
PowerIntent to turn {PowerStates}
PowerIntent {PowerStates}

MuteIntent mute
MuteIntent to mute

VolumeUpIntent turn the volume up
VolumeUpIntent volume up
VolumeUpIntent volume up {VolNum}
VolumeUpIntent turn up the volume
VolumeUpIntent turn the volume up {VolNum}
VolumeUpIntent turn the volume up by {VolNum}

VolumeDownIntent turn the volume down
VolumeDownIntent turn down the volume
VolumeDownIntent turn the volume down {VolNum}
VolumeDownIntent turn the volume down by {VolNum}
VolumeDownIntent volume down
VolumeDownIntent volume down {VolNum}

PlayIntent play
PlayIntent to play
      
PauseIntent pause
PauseIntent to pause
      
StopIntent stop
StopIntent to stop
      
ExitIntent exit
ExitIntent to exit
      
LoadAppIntent load {Apps}
LoadAppIntent to load {Apps}
LoadAppIntent {Apps}

SetInputIntent switch input to {Inputs}
SetInputIntent switch inputs to {Inputs}
SetInputIntent switch to {Inputs}
SetInputIntent change to {Inputs}
SetInputIntent change input to {Inputs}
SetInputIntent {Inputs}

SetChannelIntent switch to {Channels}
SetChannelIntent switch channel to {Channels}
SetChannelIntent to switch to {Channels}
SetChannelIntent to switch channel to {Channels}
SetChannelIntent {Channels}
SetChannelIntent to change to {Channels}
SetChannelIntent change to {Channels}
SetChannelIntent to put on {Channels}
SetChannelIntent put on {Channels}


