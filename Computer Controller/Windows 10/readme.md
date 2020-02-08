# Windows 10 Node

An variation of the **Computer Controller** which expands on existing functionality to include monitoring of volume and muting.

It utilises a work-around used in the **Application** node to build and manage a `.NET` script more suited to interfacing with the underlying OS.

## Overview

This node utilises Python's `subprocess` module for the managment of system power-states. It includes Java's `File` module for monitoring system disk-space. Finally, `VolumeController.cs` is built-on-use .NET application for controlling and monitoring the system volume. 

## Requirements

This recipe has been tested on *Windows 10 Home 1909* with *.NET Framework 4.0* which is explicitly referenced as part of the build process.
