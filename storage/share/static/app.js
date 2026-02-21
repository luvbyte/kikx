// --------------------------------------
// UUID Utilities
// --------------------------------------
// UUID generator with fallback
function generateUUID() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r =
      (crypto.getRandomValues(new Uint8Array(1))[0] & 15) >>
      (c === "x" ? 0 : 4);
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

// --------------------------------------
// Byte and Encoding Utilities
// --------------------------------------

const base64ToBytes = base64 =>
  new Uint8Array(
    atob(base64)
      .split("")
      .map(c => c.charCodeAt(0))
  );

async function blobToText(blob) {
  return await blob.text();
}

const decodeBytes = (data, enc = "utf-8", fatal = true) =>
  new TextDecoder(enc, { fatal }).decode(data);

// --------------------------------------
// App Info Helpers
// --------------------------------------

// const getAppID = () => location.pathname.split("/")[2];
const appID = location.pathname.split("/")[2];

// --------------------------------------
// Argument Parser
// --------------------------------------

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

// --------------------------------------
// Handler Class
// --------------------------------------

class Handler {
  constructor() {
    this.handlerID = generateUUID();
    this.running = false;
    this._ondata_callbacks = new Set();

    this.events = {
      started: payload => {
        this.running = true;
        this.onstart?.(payload.output);
      },
      info: payload => this.oninfo?.(payload.output),
      output: payload => this.onmessage?.(payload.output),
      error: payload => {
        this.running = false;
        this.onerror?.(payload.output);
      },
      ended: payload => {
        this.running = false;
        this.onended?.(payload.output);
      }
    };

    this._ondata_callbacks.add(payload =>
      this.events[payload.status]?.(payload)
    );
  }

  onData(callback) {
    this._ondata_callbacks.add(callback);
  }
}

// Global handler registry
const appEventHandlers = new Map();

const createHandler = () => {
  const handler = new Handler();
  appEventHandlers.set(handler.handlerID, handler);
  return handler;
};

const removeHandler = handlerID => appEventHandlers.delete(handlerID);

// --------------------------------------
// Base Service Class
// --------------------------------------

class Service {
  constructor(name) {
    this.serviceName = name;
    this.baseURL = `/service/${this.serviceName}`;
  }

  async _request(endpoint, method, headers, body) {
    Object.assign(headers, { "kikx-app-id": appID });

    return await fetch(`${this.baseURL}/${endpoint}`, {
      method,
      headers,
      body
    });
  }

  async request(endpoint, method = "GET", body = null, isJson = true) {
    let headers = {};

    if (body && isJson) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }

    try {
      const response = await this._request(endpoint, method, headers, body);
      const contentType = response.headers.get("content-type");

      let data = null;
      if (contentType?.includes("application/json")) {
        data = await response.json();
      } else if (contentType?.includes("text/")) {
        data = await response.text();
      } else if (contentType?.includes("application/octet-stream")) {
        data = await response.blob();
      }

      return {
        ok: response.ok,
        code: response.status,
        contentType,
        data: response.ok ? data : null,
        error: response.ok ? null : data || `Error ${response.status}`
      };
    } catch (err) {
      return {
        code: 500,
        ok: false,
        data: null,
        error: err.message || "Unknown error"
      };
    }
  }
}

// --------------------------------------
// Sysyem Default Services
// --------------------------------------

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

  info = payload => this.request("info");
  notify = payload => this.request("notify", "POST", payload);
  alert = payload => this.request("alert", "POST", payload);
  sendSignal = signal => this.request(`signal?signal=${signal}`);
  getUserSettings = (setting = null) =>
    this.request(`user-settings?setting=${setting}`);
  setUserSettings = settings =>
    this.request("user-settings", "POST", { settings });
  appFunc = (name, config) =>
    this.request("app/func", "POST", { name, config });
  closeApp = () => this.request("close-app", "POST");
}

class ProxyService extends Service {
  constructor() {
    super("proxy");
  }

  fetch(url, method = "GET", headers = {}, body = null) {
    return this._request(
      `?url=${encodeURIComponent(url)}`,
      method,
      headers,
      body
    );
  }

  get = (url, headers = {}) => this.fetch(url, "GET", headers);
  post = (url, body = null, headers = {}) =>
    this.fetch(url, "POST", headers, body);
}

// --------------------------------------
// Kikx App Controller
// --------------------------------------
class KikxApp {
  constructor() {
    this.id = appID;
    this.system = new SystemService();
    this.fs = new FileSystemService();
    this.proxy = new ProxyService();

    this.ws = null;
    this.eventCallbacks = {};

    this.reconnectDelay = 1000; // ms
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this._reconnectTimer = null;

    this.appConfig = {};

    // Event: App-specific handler
    this.on("handler-data", payload => {
      appEventHandlers
        .get(payload.id)
        ?._ondata_callbacks.forEach(fn => fn(payload.data));
    });

    // Signals
    this.on("signal", signal => {
      //
    });

    this.on("reconnected", () => {
      this.reconnectAttempts = 0;
    });

    // Handle tab focus in browsers
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        try {
          this.send({ event: "ping", payload: {} });
        } catch (e) {
          // emit event
        }
      }
    });
  }

  _forceReconnect(reason = "manual trigger") {
    console.log(reason + " → forcing reconnect...");
    this._clearReconnectTimer();
    this.reconnectAttempts = 0; // reset attempts on resume
    this._connect();
  }

  _connect() {
    if (this.ws) return;

    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${location.host}/app/${this.id}`;
    console.log("Connecting to WebSocket:", url);

    this.ws = new WebSocket(url);

    this.ws.onopen = e => {
      console.log("WebSocket connection opened.");
      this._clearReconnectTimer();
      this._callEvent("ws:onopen", e);
    };

    this.ws.onmessage = e => {
      try {
        const message = JSON.parse(e.data);
        if (message.event === "connected") {
          this.appConfig = message.payload.config || {};
        }
        if (message.event) {
          this._callEvent(message.event, message.payload);
        }
      } catch (err) {
        console.error("WebSocket message parse error:", err);
      }
    };

    this.ws.onclose = e => {
      console.warn("WebSocket connection closed.");
      this.ws = null;
      this._callEvent("ws:onclose", e);
      this._scheduleReconnect();
    };

    this.ws.onerror = e => {
      console.error("WebSocket error:", e);
      this._callEvent("ws:onerror", e);
      if (this.ws) {
        this.ws.close(); // Will trigger onclose
        this.ws = null;
      }
    };
  }

  _scheduleReconnect() {
    console.log("Scheduling reconnect... Attempt:", this.reconnectAttempts);

    if (this._reconnectTimer) {
      console.log("Reconnect timer already set. Skipping.");
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn(
        `Max reconnect attempts (${this.maxReconnectAttempts}) reached.`
      );
      this._callEvent("ws:reconnect_failed");
      return;
    }

    this.reconnectAttempts += 1;
    console.log(
      `Reconnect attempt ${this.reconnectAttempts} in ${this.reconnectDelay}ms...`
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

  run(callback = null) {
    if (this.ws && this.ws.readyState < WebSocket.CLOSING) return;
    if (typeof callback === "function") {
      this.on("connected", callback);
    }
    this._connect();
  }

  on(event, callback) {
    this.addEvent(event, callback);
  }

  addEvent(event, callback) {
    if (!this.eventCallbacks[event]) {
      this.eventCallbacks[event] = [];
    }
    this.eventCallbacks[event].push(callback);
  }

  _callEvent(event, data = null) {
    if (this.eventCallbacks[event]) {
      this.eventCallbacks[event].forEach(fn => fn(data));
    }
  }

  send = data => {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn("Cannot send message. WebSocket not open.");
    }
  };

  func = (name, options) => {
    return this.system.appFunc(name, options);
  };
}

const kikxApp = new KikxApp();

// --------------------------------------
// App Task Module
// --------------------------------------

class AppTask {
  constructor(name, once = true) {
    this.name = name;
    this.handler = createHandler();
    this.task_result = null;
    this.running = false;

    this.once = once;
    this.completed = false;

    this.handler.onended = () => {
      if (this.once) {
        removeHandler(this.handler.handlerID);
      }
    };

    this.handler.onData(data => {
      if (data.status === "ended") {
        this.running = false;
        this.completed = true;
      }
    });
  }

  async __run(args = "") {
    if (this.once && this.completed) throw Error("Task already completed");

    this.task_result = await kikxApp.func("tasks.run_task", {
      args: [`${this.name} ${args}`.trim()],
      options: { handler_id: this.handler.handlerID }
    });

    if (this.task_result?.error) {
      throw new Error(this.task_result.error.detail);
    }

    return this.task_result;
  }

  run(args) {
    if (this.running) return;
    this.running = true;
    return this.__run(args);
  }

  async send(input) {
    if (!this.task_result || !input) throw Error("No input or task error");

    await kikxApp.func("tasks.send_input", {
      args: [this.task_result.data, input]
    });
  }

  on(callback) {
    this.handler.onData(callback);
  }

  async kill() {
    await kikxApp.func("tasks.kill", {
      args: [this.task_result.data]
    });
  }
}

// --------------------------------------
// Task Utility Shortcuts
// --------------------------------------

const createTask = (name, once = true) => new AppTask(name, once);

// Run task with callback
const runTask = async (name, callback) => {
  const task = createTask(name);
  task.on(callback);
  // Not required since once removes automatically
  // task.handler.onended = () => {
  // removeHandler(task.handler.handlerID);
  // };
  return await task.__run();
};

// Run task sync - Gathers stdout untill complete
// not safe for output required tasks
const runTaskSync = async name => {
  const fullData = [];
  let flag = false;

  return new Promise((resolve, reject) => {
    try {
      runTask(name, data => {
        if (data.status === "started") {
          flag = true;
        } else if (data.status === "ended") {
          resolve(fullData.join("\n").trim());
        } else if (data.status === "output") {
          const output = data.output?.trim?.() || "";
          if (flag && output.length > 0) {
            fullData.push(output);
          }
        } else if (data.status === "error") {
          reject(new Error(data.output || "Unknown error"));
        }
      });
    } catch (err) {
      reject(err);
    }
  });
};

// Quick run and return resonse of task - no realtime output
const quickTask = async (name, ...input) => {
  return await kikxApp.func("tasks.run_once", {
    args: [name],
    options: {
      task_input: input.join("\n")
    }
  });
};
