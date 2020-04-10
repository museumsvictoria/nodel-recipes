# Windows 10 Node

An variation of the **Computer Controller** which expands on existing functionality to include monitoring of volume and muting.

It utilises a work-around used in the **Application** node to build and manage a `.NET` script more suited to interfacing with the underlying OS.

## Overview

#### Functions
- reboot, shutdown, suspend
- periodic screenshots
- basic volume control of primary audio device
- audio signal metering (dbFS and scalar)
- CPU monitoring

#### Components

The node utilises `Process` from Nodel Toolkit for the **management of system power-states**.

It also includes Java's `File` module for **monitoring system disk-space**.

Finally, the Windows specific special sauce 🍲 is `ComputerController.cs` a built-on-use .NET application for:

- **volume control**
- **audio signal metering**
- **CPU monitoring**
- **screenshotting**

## Requirements

#### Process Sandbox

It's **highly recommended** to use the `ProcessSandbox.exe`. It's available on the [release page](https://github.com/museumsvictoria/nodel/releases). This will ensure the .NET isn't left hanging as a result of the nodehost's closure.

The ProcessToolkit responsible for managing the .NET component will automatically search 🔍 the node's directory and the nodehost root directory for the executable.

#### Testing

This recipe has been tested on *Windows 10* with *.NET Framework 4.0* (which is explicitly referenced as part of the build) but might work with a wider variety of versions.

It has also been tested with Nodel's `r389`, but should support any version where the ProcessToolkit is available.

