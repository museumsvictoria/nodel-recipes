## Disappearing member support
Disappearing members are those which may disappear naturally i.e. those running on hosts that may naturally 
power on and off and "disappear" from the network

When disappearing members are used, the following additional signals / actions are provided:
* **"Disappearing MEMBER" remote signals / status**: these must be wired to the actual nodes that may disappear.
* **"Assumed MEMBER" local signals / status**: these aggregate the Power state and binding state of the device

Then the usual remote state/status signals need to be looped-back into their respective "assumed" states.
