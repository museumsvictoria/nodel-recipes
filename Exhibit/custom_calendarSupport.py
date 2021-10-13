# Override incoming args in local_action.
# e.g. an 'On' (str) arg is used instead of a {'state':'On'} (list) arg.

# This should enable the use of the calendar node. The remote actions
# should be bound to the "Power" or "Muting" local actions.

# A group node would also un-select "Is a Group?" when referencing this node.

@after_main
def filter_power_and_muting_call():

    def getStateValue(arg):
        if hasattr(arg, 'get'): # does it have the '.get' function i.e. dict/map-like
            return arg['state']
        elif isinstance(arg, basestring):
            return arg
        else:
            return None

    power_action = lookup_local_action('Power')
    if power_action:
        power_action.addCallFilter(getStateValue)

    muting_action = lookup_local_action('Muting')
    if muting_action:
        muting_action.addCallFilter(getStateValue)
