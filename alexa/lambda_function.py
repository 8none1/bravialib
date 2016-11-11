"""
Talk to the Bravia proxy, which in turn talks to the Bravia REST server.

"""

from __future__ import print_function
import requests
import secrets # A file to hold things like basic auth usernames/passwords and the location of your proxy
import datetime
import json

service_endpoint = secrets.service_endpoint
username = secrets.username
password = secrets.password
cert = "selfcert.pem" # Bundle your self-signed cert if you're using one


# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Hello!  I can control your Sony Bravia TV. What would you like to do?"
    reprompt_text = "You can say tell tv to switch input to Chromecast, or change channel to BBC One."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def fail_response():
    return build_response({}, build_speechlet_response(
        "Sony Bravia", "Sorry, I couldn't do that.", "", True))        

def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Good bye!"
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def dispatch_request(data):
    auth = requests.auth.HTTPBasicAuth(username,password)
    r = requests.post(service_endpoint, data=data, 
                        auth=auth, verify=cert) # verify = False if you want to ignore all cert problems
    print(r)
    print(r.headers)
    print(r.text)
    if r.status_code == 200:
        a = r.json()
        if a['status'] == True:
            return build_response({}, build_speechlet_response(
            "Bravia Controller", "OK!", None, True))
        else:
            return fail_response()
    else:
        print("Requests to endpoint failed.")
        return fail_response()

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])
          
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    appid = session['application']['applicationId']
    print(intent)
    print(intent_name)
    if 'slots' in intent:
        print(intent['slots'])
    else:
        print("No slots passed")
    # Dispatch to your skill's intent handlers
    if intent_name == "PowerIntent":
        try:
            state = intent['slots']['PowerStates']['value'].lower()
            if state == "on":
                data = {'action':'Power', 'value':True}
                print(data)
            else:
                data = {'action':'Power', 'value':False}
                print(data)
        except KeyError:
            print("Couldnt find power state in slots")
            return fail_response()
        except:
            raise

    elif intent_name == "MuteIntent":
        print("Mute intent")
        data = {'action':'Mute'}
        print(data)

    elif intent_name == "VolumeUpIntent":
        print("Doing Vol Up")
        try:
            offset = intent['slots']['VolNum']['value']
        except KeyError:
            offset = 1
        data = {'action':'VolUp', 'value':offset}
        print(data)

    elif intent_name == "VolumeDownIntent":
        print("Doing Vol Down")
        try:
            offset = intent['slots']['VolNum']['value']
        except KeyError:
            offset = 1
        data = {'action':'VolDown', 'value':offset}
        print(data)

    elif intent_name == "PlayIntent":
        data = {'action':'Play'}
        print(data)

    elif intent_name == "PauseIntent":
        data = {'action':'Pause'}
        print(data)

    elif intent_name == "StopIntent":
        data = {'action':'Stop'}
        print(data)

    elif intent_name == "ExitIntent":
        data = {'action':'Exit'}
        print(data)

    elif intent_name == "LoadAppIntent":
        try:
            appname = intent['slots']['Apps']['value']
            data = {'action':'App', 'value':appname}
            print(data)
        except KeyError:
            return fail_response()

    elif intent_name == "SetChannelIntent":
        try:
            channel = intent['slots']['Channels']['value']
            data = {'action':'Channel', 'value':channel}
            print(data)
        except:
            return fail_response()
        
    elif intent_name == "SetInputIntent":
        try:
            inputname = intent['slots']['Inputs']['value']
            data = {'action':'Input', 'value':inputname}
            print(data)
        except KeyError:
            return fail_response()

    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")
    
    response = dispatch_request(data)
    return response


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    #appid = event['session']['application']['applicationId']
    #if appid != "amzn1.ask.skill.c56f17c4-1273-4331-8df5-c7dda6d06595":
    #    raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])



