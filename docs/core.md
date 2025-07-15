core.py - DOCS

📘 Kikx API Documentation
✅ API Overview

🔐 Authentication Endpoints

GET /login

Description:
Serves the login HTML page.


---

POST /login

Description:
Authenticates user and issues a JWT token in cookies.

Request:

Form: username, password (via OAuth2PasswordRequestForm)


Response:

{
  "message": "Login successful"
}


---

GET /logout

Description:
Clears the JWT cookie and redirects to the homepage.


---

📦 App Management

POST /api/apps/list

Description:
Returns a list of installed apps for a given client, optionally filtered by category.

Request Body:

{
  "client_id": "string"
}

Query Parameter:

category (optional)


Response:

[
  {
    "name": "app_name",
    "title": "App Title",
    "icon": "/path/to/icon.png"
  }
]


---

POST /open-app

Description:
Opens an app instance for the client.

Request Body:

{
  "client_id": "string",
  "name": "app_name"
}

Response:

{
  "id": "app_id",
  "url": "/app/app_id/index.html?starting=true",
  "iframe": {}    // iframe config permissions of app
}


---

POST /close-app

Description:
Closes the app instance.

Request Body:

{
  "app_id": "string",
  "client_id": "string"
}

Response:

{ "res": "ok" }


---

🗂 App Files & Routing

GET /app/{app_id}/{path:path}

Description:
Serves app files based on app ID. Supports secure access to app root files via _app/.


---

GET /public/app/{name}/{path:path}

Description:
Serves public app assets like icons and media files.


---

🎛️ UI Management

GET /ui/{ui_name}/{path:path}

Description:
Serves UI frontend files. Requires JWT if require_auth is true.


---

🔗 Shortlink Redirection

GET /sl/{path:path}

Description:
Redirects using stored shortlinks.


---

🏠 Root Endpoint

GET /

Description:
Redirects to the user’s default UI page.


---

🔌 WebSocket Endpoints

WebSocket /client

Description:
Establishes a persistent client connection. Authenticates using the cookie token.

On Connect Response:

{
  "client_id": "string",
  "settings": { ... }
}


---

WebSocket /app/{app_id}

Description:
WebSocket connection for a running app instance.

Events:

On Connect: connected event with app config and user settings

On Data: Custom event handler core.on_app_data(...)



---

⚙️ Core API Behavior

Core.open_app(client_id, name)

Launches and registers an app instance.

Core.close_app(client, app)

Gracefully shuts down an app instance and removes it from app_index.

Core.get_client_app_by_id(app_id)

Fetches a client and app pair by app ID.

Core.on_client_disconnect(client)

Handles cleanup when a client disconnects.

Core.on_app_disconnect(client, app)

Handles cleanup when an app disconnects (currently a placeholder).


---

🧩 Plugins and Services

Lifecycle Hooks:

core.plugins.before_startup(...)

core.plugins.after_startup(...)

core.plugins.shutdown()


Plugins are loaded dynamically from paths defined in core.config.kikx.plugins.


---

🛑 Shutdown

Core.on_close()

Cleans up services, shuts down plugins, and optionally runs shutdown.sh.


---

📁 Static File Mounts

/share: Exposes files from core.config.share_path

/public/app/...: Publicly accessible app files

/ui/...: UI static files, user-specific



---

🧾 Models Overview

AppManifestModel
  title: str
  icon: str
  category: Optional[str]

