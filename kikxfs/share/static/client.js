function generateUUID() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r =
      (crypto.getRandomValues(new Uint8Array(1))[0] & 15) >>
      (c === "x" ? 0 : 4);
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const getCookie = name =>
  document.cookie
    .split("; ")
    .find(row => row.startsWith(name + "="))
    ?.split("=")[1] || null;

const setCookie = (name, value) => {
  document.cookie = `${name}=${value}; path=/`;
};

async function blobToText(blob) {
  const text = await blob.text();
  // console.log(text);
  return text;
}

function parseArgsAndKwargs(...args) {
  if (
    args.length &&
    typeof args[args.length - 1] === "object" &&
    !Array.isArray(args[args.length - 1])
  ) {
    return { args: args.slice(0, -1), options: args[args.length - 1] };
  }
  return { args, options: {} };
}

let clientID = null;
const getClientID = () => {
  return clientID;
};

class Service {
  constructor(name) {
    this.serviceName = name;
    this.baseURL = `/service/${this.serviceName}`;
  }
  async _request(endpoint, method, headers, body) {
    Object.assign(headers, {
      "kikx-client-id": clientID
    });
    return await fetch(`${this.baseURL}/${endpoint}`, {
      method,
      headers,
      body
    });
  }
  async request(endpoint, method = "GET", body = null, isJson = true) {
    let headers = {};

    // Prepare headers and body if JSON is expected
    if (body && isJson) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }

    try {
      // Call the internal request method
      const response = await this._request(endpoint, method, headers, body);
      let data = null;

      // Check if Content-Type header is present
      const contentType = response.headers.get("content-type");

      // Parse response data based on content type
      if (contentType) {
        if (contentType.includes("application/json")) {
          data = await response.json();
        } else if (contentType.includes("text/")) {
          data = await response.text();
        } else if (contentType.includes("application/octet-stream")) {
          data = await response.blob(); // or .arrayBuffer() depending on use case
        }
        // Add more types if needed
      }

      return {
        ok: response.ok,
        code: response.status,
        contentType: contentType,
        data: response.ok ? data : null,
        error: response.ok ? null : data || `Error ${response.status}`
      };
    } catch (err) {
      // Catch network or parsing errors
      return {
        code: 500,
        ok: false,
        data: null,
        error: err.message || "Unknown error"
      };
    }
  }
}

class FileSystemService extends Service {
  constructor() {
    super("fs");
  }

  listFiles = (directory = "") =>
    this.request(`list?directory=${encodeURIComponent(directory)}`);
  readFile = filename =>
    this.request(`read?filename=${encodeURIComponent(filename)}`);
  writeFile = (filename, content) =>
    this.request("write", "POST", { filename, content });
  uploadFile = file => {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("upload", "POST", formData, false);
  };
  deleteFile = filename =>
    this.request(`delete?filename=${encodeURIComponent(filename)}`, "DELETE");
  createDirectory = dirname =>
    this.request("create_directory", "POST", { dirname });
  deleteDirectory = dirname =>
    this.request(
      `delete_directory?dirname=${encodeURIComponent(dirname)}`,
      "DELETE"
    );
  copy = (source, destination) =>
    this.request("copy", "POST", { source, destination });
  move = (source, destination) =>
    this.request("move", "POST", { source, destination });
  serve = file => this.request(`serve?filename=${encodeURIComponent(file)}`);
}

class SystemService extends Service {
  constructor() {
    super("system");
  }
  clientFunc = (name, config) =>
    this.request("client/func", "POST", {
      name,
      config
    });
}

class Client {
  constructor() {
    this.clientID = clientID; // global
    this.eventCallbacks = {};
    this.system = new SystemService();
    this.fs = new FileSystemService();
    this.ws = null;

    // Auto-reconnect
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // ms
    this._reconnectTimer = null;

    this._closed = false;

    // Heartbeat
    // this.heartbeatDelay = 3000; // 3 seconds
    // this._heartbeatTimer = null;

    // Listen for signals
    this.on("signal", signalData => {
      //
    });

    this.on("reconnected", () => {
      this.reconnectAttempts = 0;
    });

    window.addEventListener("app:exit", async () => {
      // app exit
      await this.system.request("info/session/close/" + clientID, "POST");
    });

    // Browser tab focus
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        // this._forceReconnect("Tab became visible");
        // this._startHeartbeat();
        try {
          this.send({ event: "ping", payload: {} });
        } catch (e) {
          alert("kikx disconnected refresh");
        }
      }
    });
  }

  _forceReconnect(reason = "manual trigger") {
    console.log(reason + " → forcing reconnect...");
    this._clearReconnectTimer();
    this.reconnectAttempts = 0;
    this._connect();
  }

  _connect() {
    if (this.ws || this._closed) return;

    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${location.host}/client?client_id=${this.clientID}`;
    console.log("Connecting to WebSocket:", url);

    this.ws = new WebSocket(url);

    this.ws.onopen = e => {
      console.log("WebSocket connection opened.");
      this._clearReconnectTimer();
      this._callEvent("ws:onopen", e);
      //this._startHeartbeat();
    };
    this.ws.onmessage = e => {
      try {
        const message = JSON.parse(e.data);
        if (message.event === "connected") {
          this.clientID = message.payload.client_id;
          clientID = message.payload.client_id;
        }
        if (message.event) this._callEvent(message.event, message.payload);
      } catch (err) {
        console.error("WebSocket parse error:", err);
      }
    };
    this.ws.onclose = e => {
      console.warn("WebSocket closed.", e);
      this.ws = null;
      this._callEvent("ws:onclose", e);
      this._scheduleReconnect();
      // this._stopHeartbeat();
    };
    this.ws.onerror = e => {
      console.error("WebSocket error:", e);
      this._callEvent("ws:onerror", e);
      if (this.ws) {
        this.ws.close();
        this.ws = null;
      }
    };
  }
  _scheduleReconnect() {
    if (this._reconnectTimer) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn("Max reconnect attempts reached.");
      this._callEvent("ws:reconnect_failed");
      return;
    }
    this.reconnectAttempts += 1;
    console.log(
      `Reconnect attempt ${this.reconnectAttempts} in ${this.reconnectDelay}ms`
    );
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._connect();
    }, this.reconnectDelay);
  }
  _clearReconnectTimer() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }

  // Heartbeat: check WS every 3 seconds
  // Heartbeat: ping/pong system
  // will he removed
  _startHeartbeat() {
    this._stopHeartbeat(); // clear existing timers

    const sendPing = () => {
      if (!this.ws) {
        console.log("Heartbeat: WS not open, reconnecting...");
        this._forceReconnect("heartbeat");
        return;
      }

      // Send ping as JSON
      this.ws.send(JSON.stringify({ event: "ping", timestamp: Date.now() }));

      // Wait for pong within 3 seconds
      this._heartbeatTimer = setTimeout(() => {
        console.warn("No pong received in 3 seconds. Reconnecting...");
        this._forceReconnect("heartbeat timeout");
      }, this.heartbeatDelay);
    };

    // Send initial ping immediately
    sendPing();
  }
  // will he removed
  _stopHeartbeat() {
    if (this._heartbeatTimer) {
      clearTimeout(this._heartbeatTimer);
      this._heartbeatTimer = null;
    }
    if (this._heartbeatInterval) {
      clearInterval(this._heartbeatInterval);
      this._heartbeatInterval = null;
    }
  }

  run(callback) {
    if (this.ws && this.ws.readyState < WebSocket.CLOSING) return;
    if (typeof callback === "function") this.on("connected", callback);
    this._connect();
  }

  addEvent(event, callback) {
    if (!this.eventCallbacks[event]) this.eventCallbacks[event] = [];
    this.eventCallbacks[event].push(callback);
  }

  on(event, callback) {
    this.addEvent(event, callback);
  }

  _callEvent(event, data = null) {
    if (this.eventCallbacks[event]) {
      this.eventCallbacks[event].forEach(fn => fn(data));
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn("Cannot send. WebSocket not open.");
    }
  }

  func(name, ...args) {
    const parsed = parseArgsAndKwargs(...args);
    return this.system.clientFunc(name, {
      args: parsed.args,
      options: parsed.options
    });
  }
}
