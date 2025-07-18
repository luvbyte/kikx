// Faster UUID generation using secure browser API
const generateUUID_https = () => crypto.randomUUID();

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

// Convert Base64 to Uint8Array (Optimized)
const base64ToBytes = base64 =>
  new Uint8Array(
    atob(base64)
      .split("")
      .map(c => c.charCodeAt(0))
  );

async function blobToText(blob) {
  const text = await blob.text();
  // console.log(text);
  return text;
}

// Decode Uint8Array to String (Optimized)
const decodeBytes = (data, enc = "utf-8", fatal = true) =>
  new TextDecoder(enc, { fatal }).decode(data);

// Extract app ID from URL
const getAppID = () => location.pathname.split("/")[2];
const appID = getAppID();

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

// Global event handlers
const appEventHandlers = new Map();

const createHandler = () => {
  const handler = new Handler();
  appEventHandlers.set(handler.handlerID, handler);
  return handler;
};

const removeHandler = handlerID => appEventHandlers.delete(handlerID);

// Service class for handling requests
class Service {
  constructor(name) {
    this.serviceName = name;
    this.baseURL = `/service/${this.serviceName}`;
  }
  async _request(endpoint, method, headers, body) {
    Object.assign(headers, {
      "kikx-app-id": appID
    });

    //console.log(endpoint, method, headers, body);

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

  notify = payload => this.request("notify", "POST", payload);
  sendSignal = signal => this.request(`signal?signal=${signal}`);
  getUserSettings = () => this.request("user-settings");
  setUserSettings = settings =>
    this.request(`user-settings`, "POST", {
      settings: settings
    });

  appFunc = (name, config) =>
    this.request("app/func", "POST", { name, config });
  closeApp = () => this.request("close-app", "POST");
}

class ProxyService extends Service {
  constructor() {
    super("proxy");
  }
  fetch(url, method = "GET", headers = {}, body = null) {
    return this._request(`?url=${url}`, method, headers, body);
  }
  get = (url, headers = {}) => {
    return this.fetch(url, "GET", headers);
  };
  post = (url, body = null, headers = {}) => {
    return this.fetch(url, "POST", headers, body);
  };
}

class KikxApp {
  constructor() {
    this.id = appID;
    this.system = new SystemService();
    this.fs = new FileSystemService();
    this.proxy = new ProxyService();

    this.ws = null;
    this.eventCallbacks = {};
    this.reconnectDelay = 1000; // Exponential backoff

    // these will update on app.run call
    this.userSettings = {};
    this.appConfig = {};

    this.on("handler-data", payload =>
      appEventHandlers
        .get(payload.id)
        ?._ondata_callbacks.forEach(f => f(payload.data))
    );

    // user settings
    this.on("signal", signalData => {
      if (signalData.signal === "update_user_settings") {
        Object.assign(this.userSettings, signalData.data);
      }
    });
  }

  run(callback = null) {
    if (this.ws) return;

    // connected event
    if (typeof callback === "function") {
      this.on("connected", callback);
    }

    const url = `${location.protocol === "https:" ? "wss" : "ws"}://${
      location.host
    }/app/${appID}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = e => this._callEvent("ws:onopen", e);
    this.ws.onmessage = e => {
      try {
        const message = JSON.parse(e.data);
        // will check first
        if (message.event === "connected") {
          this.appConfig = message.payload.config;
          this.userSettings = message.payload.settings;
        }
        // later emits
        message.event && this._callEvent(message.event, message.payload);
      } catch (error) {
        console.log(this.eventCallbacks);
        console.error("WebSocket error:", error);
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this._callEvent("ws:onclose");
      // setTimeout(() => this.run(), (this.reconnectDelay *= 2)); // Exponential backoff
    };

    this.ws.onerror = e => this._callEvent("ws:onerror", e);
  }

  // this will call on any event
  _callEvent(event, data = null) {
    this.eventCallbacks[event]?.forEach(func => func(data));
  }

  on(event, callback) {
    (this.eventCallbacks[event] ||= []).push(callback);
  }
  // send event using ws
  send = data => this.ws?.send(JSON.stringify(data));
  func = (name, options) => this.system.appFunc(name, options);

  createNeuron = name => new NeuronService(name);
}

const kikxApp = new KikxApp();

// code based on above
// AppTaskModule
class AppTask {
  constructor(name) {
    this.handler = createHandler();
    this.name = name;
    this.task_result = null;
    // prevents recalling run function
    this.running = false;

    this.handler.onData(data => {
      if (data.status === "ended") {
        this.running = false;
      }
    });
  }
  async __run(args = "") {
    this.task_result = await kikxApp.func("tasks.run_task", {
      args: [`${this.name} ${args}`.trim()],
      options: {
        handler_id: this.handler.handlerID
      }
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
    // return this.task_result ? this.task_result : this.__run();
  }
  // this will send all type of data
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
// create task
const createTask = name => new AppTask(name);
// deletes handler on ended
const runTask = async (name, callback) => {
  const task = new AppTask(name);
  task.on(callback);
  // removing after completed
  task.handler.onended = payload => {
    removeHandler(task.handler.handlerID);
  };
  // running task
  return await task.__run();
};

const quickTask = async (task_cmd, task_input = []) => {
  const result = await kikxApp.func("tasks.sh", {
    args: [task_cmd.trim()],
    options: {
      task_input: task_input
    }
  });

  // Before runtime error
  if (result.err) {
    throw result.err;
  }

  // Runtime error
  if (result.data.stderr) {
    throw result.data.stderr;
  }

  return result.data.stdout;
};

const tasks = {
  create: createTask,
  run: runTask,
  sh: quickTask
};
