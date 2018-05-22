# OSC Server Node

An implementation of pyOSC used to match patterns and monitor messages.

*OSC overview@* https://www.music.mcgill.ca/~gary/306/week9/osc.html

*pyOSC package @* https://pypi.org/project/pyOSC/

## Parameters

**Port** specifices the port to bind our OSC packet listener.

**Patterns** contains an array of OSC address patterns in the form of `/foo/bar` and their corresponding labels.

**Display non-parameterised messages** toggles the display of OSC messages that *don't* have an associated pattern listed in the parameters.

## Events

Events are generated from the *Patterns* parameter.

The events provide bindable data streams from the OSC messages filtered by their specified patterns. These can then be propagated around the Nodel network to meet specific requirements.
