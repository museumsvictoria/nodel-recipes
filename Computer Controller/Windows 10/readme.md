# Windows 10 Node

An variation of the **Computer Controller** which expands on existing functionality to include monitoring of volume and muting.

It utilises a work-around used in the **Application** node to build and manage a `.NET` script more suited to interfacing with the underlying OS.

## Overview

#### Functions
- reboot, shutdown, suspend
- periodic screenshots
- basic volume control of primary audio device
- CPU monitoring

The node utilises Python's `subprocess` module for the **management of system power-states**.

It also includes Java's `File` module for **monitoring system disk-space**.

Finally, the Windows specific special sauce 🍲 is `ComputerController.cs` a built-on-use .NET application for **volume control** and **CPU monitoring** and **screenshotting*.

## Requirements

This recipe has been tested on *Windows 10* with *.NET Framework 4.0* (which is explicitly referenced as part of the build) but might work with a wider variety of versions.
