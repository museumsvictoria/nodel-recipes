# OSC Server Node

An implementation of pyOSC used to match patterns and monitor messages.

## Parameters

**Port** specifices the port to bind our OSC packet listener.
**Patterns** contains an array of OSC address patterns in the form of `/foo/bar` and their corresponding labels.
**Display non-parameterised messages** toggles the display of OSC messages that **don't** have an associated pattern listed in the parameters.

## Events

Events are generated from the *Patterns* parameter.

Events are collected from child nodes (end or group), aggregated, and then passed up to any parent nodes.

| Events  |  Node  | Event
| --------|--------|--------
| Member PC Muting | PC Node | Muting
| Member PC Power  | PC Node | Power
| Member App Power | App Node | Power

One issue with this is that when the power is turned off, the events from the child devices will stop.

This can be mitigated by using disappearing member, which provides a mechanism for the group node to keep track of the last (assumed) status.

To use this enable `Disappears when power is off` in the members section of the advanced screen for the group node.

When disappearing members are used, the following additional signals / actions are provided:
* **"Disappearing MEMBER" remote signals / status**: these must be wired to the actual nodes that may disappear.
* **"Assumed MEMBER" local signals / status**: these aggregate the Power state and binding state of the device

Then the usual remote state/status signals need to be looped-back into their respective "assumed" states.

Note that this is only required in group nodes when a child node will disappear when the power is off.

The child nodes are wired like this:

| Events                 |  Node     | Event
| -----------------------|-----------|--------
| Member PC Muting       | This Node | MemberPCAssumedMuting
| Member PC Power        | This Node | MemberPCAssumedPower
| Member PC Status       | This Node | MemberPCAssumedStatus
| PC Disappearing Muting | PC        | Muting
| PC Disappearing Power  | PC        | Power
| PC Disappearing Status | PC        | Status

The signal flow looks like this:

```
 ┌─ PC Node ─┐    ┌──────────            This Group Node                ──────────┐   ┌─ parent group or dashboard ─┐
    Status     ->   Disappearing Status -> Member Assumed Status -> Member Status   ->    Event wiring
```
