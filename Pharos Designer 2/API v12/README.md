## Pharos Designer 2 API v12

<<<<<<< Updated upstream
Nodel integration for Pharos lighting/media show controllers via the Pharos Designer HTTP API.
=======
Nodel integration for Pharos lighting controllers via the Pharos Designer HTTP API.
>>>>>>> Stashed changes

- API version 12.0 (Pharos Designer 2.16.2)
- Optional authentication using username/password
- Automatically generates actions/events from desired objects (Scenes, Timelines, Triggers), sorted by their Pharos groups
- Updates events with state from Pharos as part of status checking, with a default 2s delay for fade

### Setup
- **Pharos Config**: set the controller's IP address and port (default `80`).
- **Pharos Login**: enable if the controller requires authentication, and supply the username/password (defaults `admin`/`admin`).
- **Pharos Objects**: choose which object types (Scenes, Timelines, Triggers) to generate actions/events for.

For each enabled object type, creates an action/event per object (e.g. `1SceneName`) and per group (e.g. `SceneGroup1`).

### Ingredients

<<<<<<< Updated upstream
Optional scripts that add extra (mostly frontend) conveniences on top of the normal script. They can be used independently.
=======
Optional scripts that add extra (mostly frontend) conveniences on top of the normal script. They can be used independently. To use, remove the underscore from the start of the filename.
>>>>>>> Stashed changes

#### `ingredient_Pharos_ObjectsOnOff.py`
- Adds an **On/Off** action and event for every Scene and Timeline (e.g. `1SceneNameOnOff`).

#### `ingredient_Pharos_ObjectGroupDynamicSelect.py`
- Adds a **Select** action and event for each object group (e.g. `SceneGroup1Select`).

### Manual
- [Pharos API Documentation](https://pharos-designer-controller-api.readthedocs.io/en/latest/http-api/index.html)

See the revision history in `script.py` for version notes.
