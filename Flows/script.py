'''###Cues###

*Used to send an array of specified actions.*

**Title:** Title of the Cue, will also be the title of the associated Local Action.

<ins>**Actions**</ins>

- **Title:** This will be the name of the remote Action, which you can then bind to another Node.

- **Argument:** Optional: If used, the Remote Action will send an argument to the bound Node. For example, 'On' or 'Off' to a remote 'Power' Action.

- **Delay:** Optional: If used, the Cue will wait the specified duration before sending this Action. Useful for sequencing.

###Flows###

*Used to trigger a series of logical checks, to test whether a Cue is allowed to be actioned.*

**Title:** Title of the Flow, will also be the title of the associated Local Action.

**Remote Event Trigger**: Optional: If used, the Flow will automatically be activated upon receiving the specified Remote Event.

<ins>**Outcomes**</ins>

- **Outcome:** The name of a Cue or another Flow which will be activated if the specified checks all pass.

- **Trigger Argument:** Optional: If used, when the Remote Event Trigger receives a message, this Outcome will only be activated if the specified argument matches. For example, if the Remote Event Trigger is a GPIO input from a BrightSign, you may only want to activate the Outcome if the GPIO is being turned on (i.e. button press), and ignore the command if the GPIO is being turned off (i.e. button release).

  <ins>**Conditions**</ins>

  - **Event:** A Remote Event which will be checked each time the Outcome is asked to run, which will need to match...

  - **Argument:** ...the argument specified here.

'''

# Parameters

# Setting options for the Cues
param_Cues = Parameter({'title': 'Cues', 'order': '1', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'Title': {'order': '1', 'type': 'string'}, 
          'Actions': {'order': '2', 'type': 'array', 'items': {'type': 'object', 'properties': {
            'title': {'order': '1', 'title': 'Title', 'type': 'string'},
            'argument': {'order': '2', 'title': 'Argument (Optional)', 'type': 'string', 'hint': 'Enter argument to send with action (eg. On/Off)'},
            'delay': {'order': '3', 'title': 'Delay Time (Optional)', 'type': 'number', 'hint': 'Enter time in seconds'}}}}
            }}}})

# Setting up options for creating Flows
param_Flows = Parameter({'title': 'Flows', 'order': '3', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'Title': {'order': '1', 'hint': 'Flow title', 'type': 'string'},
          'Trigger': {'order': '2', 'title': 'Remote Event Trigger (Optional)', 'type': 'string', 'hint': 'When received, this Remote Event will activate the Flow'}, 
          'Outcomes': {'order': '4', 'type': 'array', 'items': {'type': 'object', 'properties': {
            'Cue': {'order': '2', 'title': 'Outcome', 'type': 'string', 'hint': 'Cue or Flow title to activate if conditions are met.'},
            'TriggerArgument': {'order': '3', 'title': 'Trigger Argument (Optional)', 'type': 'string', 'hint': 'Activate this outcome when the given argument matches'},
            'Conditions': {'order': '4', 'title': 'Conditions (Optional)', 'type': 'array', 'items': {'type': 'object', 'properties': {
              'RemoteEvent': {'order': '1', 'title': 'Event', 'type': 'string', 'hint': 'Remote Event to check...'},
              'Argument': {'order': '2', 'title': 'Argument', 'type': 'string', 'hint': 'Check if the Event matches this argument'}}}}
            }}}
            }}}})

# Create all the remote actions and events for each step of each sequence
def main():

  # Function to create local and remote Events for Triggers
  def CreateTriggerEvents(FlowName, EventName, flowtriggerdict):

    # Function to emit the remote events to a local event, activate any Flows that have Triggers set for that Event
    def remoteEventHandler(arg = None):
      lookup_local_event(EventName).emit(str(arg))

      # Check the dictionary for multiple Flows with the same Event source
      for x in flowtriggerdict:
        if flowtriggerdict[x] == EventName:
          lookup_local_action(x).call(str(arg))

    # If the event doesn't exist yet, make it
    if EventName != None:
      if lookup_local_event(EventName) == None:
        remoteEvent = create_remote_event(EventName, remoteEventHandler)
        create_local_event(EventName, {'title': EventName, 'group': 'Events', 'schema': {'type': 'string'}})

  # Function to create local and remote Events for Conditions
  def CreateConditionEvents(EventName):
    def remoteEventHandler(arg = None):
      lookup_local_event(EventName).emit(str(arg))

    if lookup_local_event(EventName) == None:
      remoteEvent = create_remote_event(EventName, remoteEventHandler)
      create_local_event(EventName, {'title': EventName, 'group': 'Events', 'schema': {'type': 'string'}})
  
  # Setting up the remote actions - Cues
  if param_Cues != None:
    for EachCue in param_Cues:
      CueName = EachCue['Title']
      
      makelocalAction(CueName)
      for EachItem in EachCue['Actions']:
        ItemLabel = EachItem['title']
        if lookup_remote_action(ItemLabel) == None:
          create_remote_action(ItemLabel)

  # Function for creating each Flow Action
  def CreateFlow(FlowName, TriggerArgumentList):
    # Setting all the information we need
    # Find the correct flow
    for EachFlow in param_Flows:
      if FlowName == EachFlow['Title']:

        # Get the Remote Event Trigger
        if EachFlow['Trigger'] != None:
          TriggerEvent = EachFlow['Trigger']

    def FlowHandler(arg):
      print('Flow \"%s\" - Activated with Argument \"%s\"' % (FlowName, arg))
      
      # Find the correct Flow
      for EachFlow in param_Flows: 
        if FlowName == EachFlow['Title']:
          ArgumentMatch = []

          # Check the Conditions
          for EachOutcome in EachFlow['Outcomes']:
            
            # First, check the Trigger Argument
            TriggerArgument = EachOutcome['TriggerArgument']
            if TriggerArgument == None or arg == TriggerArgument:
              ArgumentMatch.append('True')
              
              # Now if that's a match, check the Conditions
              ConditionCheck = []
              if EachOutcome['Conditions'] != None:
                for EachCondition in EachOutcome['Conditions']:
                  if lookup_local_event(EachCondition['RemoteEvent']).getArg() == EachCondition['Argument']:
                    ConditionCheck.append('True')
                  else:
                    ConditionCheck.append('False')
              if 'False' in ConditionCheck:    
                print('Flow \"%s\" - Conditions not met for Outcome \"%s\". Not running...' % (FlowName, EachOutcome['Cue']))
              
              # If the conditions pass
              else:
                EachCue = (EachOutcome['Cue'])
                
                # Check that the Outcome actually exists
                if EachCue == None:
                  console.error('Flow \"%s\" - No Cue defined for Outcome \"%s\"' % (FlowName, EachOutcome['Cue']))
                else:
                  if lookup_local_action(EachCue):
                    lookup_local_action(EachCue).call()
                  else:
                    # If the Outcome isn't in the list of Cues or Flows
                    console.error('Flow \"%s\" - Local Action \"%s\" does not exist.' % (FlowName, EachCue))
          if ArgumentMatch == []:
            print('Flow \"%s\" - No Outcome mapped for Argument \"%s\", stopping...' % (FlowName, arg))

                  
    # Create Local Action
    if TriggerArgumentList == [None]:
      Action(FlowName, FlowHandler, {'title': FlowName, 'group': 'Flows'})
    else:
      Action(FlowName, FlowHandler, {'title': FlowName, 'group': 'Flows', 'schema': {'type': 'string', 'enum': TriggerArgumentList}})


  #################### Flows Step 1 ##########################

  # Check if there are any flows
  if param_Flows != None:

    # Create a list of flows - this will be used in the FlowHandler
    FlowList = []
    TriggerList = []
    flowtriggerdict = {}
    for EachFlow in param_Flows:
      FlowName = EachFlow['Title']
      FlowList.append(FlowName)
      
      # Get information which we need to create Remote Events
      EventName = EachFlow['Trigger']
      TriggerList.append(EventName)

      # Making a dictionary here in case multiple Flows use the same event
      flowtriggerdict[FlowName] = EventName

      # Function for creating the events
      CreateTriggerEvents(FlowName, EventName, flowtriggerdict)

      # Get data per Outcome
      Data = EachFlow['Outcomes']
      TriggerArgumentList = []
      for EachItem in Data:
        TriggerArgumentList.append(EachItem['TriggerArgument'])      
        c = EachItem['Conditions']
        if c!= None:
          ConditionList = []
          for EachCondition in EachItem['Conditions']:
            ConditionEvent = EachCondition['RemoteEvent']
            CreateConditionEvents(ConditionEvent)

      CreateFlow(FlowName, TriggerArgumentList)
    

# Create local actions
def makelocalAction(CueName):
  if lookup_local_action(CueName) == None:
    handler = lambda ignore: GoCue(CueName)
    create_local_action(CueName, handler, {'group': 'Cues', 'title': CueName})
        
# Cue each action in turn
def start(CueName):
  for EachCue in param_Cues:
    if CueName == EachCue['Title']:
      for EachItem in EachCue['Actions']:
        kickOffItem(EachItem)

def GoCue(CueName):
  for EachCue in param_Cues:
    if CueName == EachCue['Title']:
      start(CueName)
      console.info('Sending \"%s\"...' % CueName)

# Start each action item within the cue
def kickOffItem(item):
  label = item['title']

  # Check if there's a delay set
  if item['delay'] != None:
    time = item['delay']
  else:
    time = 0
  if item['argument'] != None:
    arg = str(item['argument'])
  else:
    arg = None

  ra = lookup_remote_action(label)
  call(lambda: lookup_remote_action(label).call(arg), time)
