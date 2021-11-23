# Nodel Host

A self-referential node, utilising the `Process`-toolkit to spawn and manage a _new_ node-host. The host runs on a seperate JVM instance, and is configured independently. 🐍

## Overview

Upon pointing this node to a Nodel release (e.g. `/opt/nodel/nodelhost.jar`) and a working directory (e.g. `/opt/bit/site/stablehost`) it will launch an additional node-host. The node's console acting as the usual JVM console.

![Node Console Example](https://user-images.githubusercontent.com/9277107/84974987-b8e53b80-b167-11ea-8726-232f05622781.png)

A series of common configuration options from the `bootstrap.json` are exposed as **Parameters**.

- Specify network interface(s)
- Enable program logging
- Inclusive/exclusive node filtering
- HTTP port
- Websocket port
- /nodes directory
- /recipes directory

Then they're added as arguments.

`Starting Nodel host... (params are ['java', '-jar', u'C:\\Nodel\\nodel-JARS\\nodelhost-release-2.1.1-rev389.jar', '-p', '0', '--recipes', u'C:\\nodel\\recipes\\'])`

## Features

- Manually or automatically update the `nodelhost.jar` based on the latest available version.
- Use **Actions** to manage the node-host state _without_ requiring tools provided by the OS.
- For larger deployments, configure multiple regularly updating and independent node-hosts through the Nodel web interface.
