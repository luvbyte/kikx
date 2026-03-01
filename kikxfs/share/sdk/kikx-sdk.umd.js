(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
  typeof define === 'function' && define.amd ? define(['exports'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.kikxSdk = {}));
})(this, (function (exports) { 'use strict';

  let customApiUrl = null;
  let customWsUrl = null;

  let customAppID = location.pathname.split("/")[2];

  function getAppID() {
    return customAppID;
  }

  const configureUrls = options => {
    const { apiUrl, wsUrl, appID } = options;

    if (apiUrl) customApiUrl = apiUrl;
    if (wsUrl) customWsUrl = wsUrl;
    if (appID) customAppID = appID;
  };

  const getDefaultBase = () => {
    const { protocol, hostname, port } = window.location;
    return `${protocol}//${hostname}${port ? `:${port}` : ""}`;
  };

  const apiUrl = () => customApiUrl || getDefaultBase();

  const getWsUrl = () => {
    if (customWsUrl) return customWsUrl;

    const { protocol, hostname, port } = window.location;
    return `${protocol === "https:" ? "wss:" : "ws:"}//${hostname}${port ? `:${port}` : ""}`;
  };

  const getUrl = end => {
    let endUrl = end.startsWith("/") ? end : "/" + end;
    return apiUrl() + endUrl;
  };

  async function request(
    endpoint,
    method = "GET",
    body = null,
    isJson = true,
    headers = {}
  ) {
    headers = { ...headers };

    if (body && isJson) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }

    try {
      const response = await fetch(getUrl(endpoint), {
        method,
        headers,
        body
      });

      const contentType = response.headers.get("content-type");
      let data = null;

      if (response.status !== 204) {
        if (contentType?.includes("application/json")) {
          data = await response.json();
        } else if (contentType?.includes("text/")) {
          data = await response.text();
        } else if (contentType?.includes("application/octet-stream")) {
          data = await response.blob();
        }
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
        ok: false,
        code: 500,
        data: null,
        error: err.message || "Unknown error"
      };
    }
  }

  async function fetchAppConfig(appID) {
    const res = await request(`/api/app/config?app_id=${appID}`);

    if (res.error) {
      throw Error(res.error);
    }

    return res.data;
  }

  function generateUUID() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
      const r =
        (crypto.getRandomValues(new Uint8Array(1))[0] & 15) >>
        (c === "x" ? 0 : 4);
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  // Event handler
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

  class Service {
    constructor(name) {
      this.appID = getAppID();
      this.serviceName = name;
      this.baseURL = `/service/${this.serviceName}`;
    }

    async request(endpoint, method = "GET", body = null, isJson = true) {
      let headers = {};

      Object.assign(headers, { "kikx-app-id": this.appID });

      return await request(
        `${this.baseURL}/${endpoint}`,
        method,
        body,
        isJson,
        headers
      );
    }
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

  class KikxApp {
    constructor() {
      this.id = getAppID();

      this.system = new SystemService();

      // config
      this.config = null;
    }
    async run(callback = null) {
      this.config = await fetchAppConfig(this.id);

      if (callback && typeof callback === "function") {
        await callback();
      }
    }
    func(name, options) {
      return this.system.appFunc(name, options);
    }
  }

  class KikxAppClient extends KikxApp {
    constructor() {
      super();

      this.appEventHandlers = new Map();

      this.ws = null;
      this.eventCallbacks = {};

      this.reconnectDelay = 1000; // ms
      this.reconnectAttempts = 0;
      this.maxReconnectAttempts = 13;
      this._reconnectTimer = null;

      // Signals
      this.on("signal", signal => {
        //
      });

      // Event: App-specific handler
      this.on("handler-data", payload => {
        this.appEventHandlers
          .get(payload.id)
          ?._ondata_callbacks.forEach(fn => fn(payload.data));
      });

      this.on("reconnected", () => {
        this.reconnectAttempts = 0;
      });

      // Handle tab focus in browsers
      document.addEventListener("visibilitychange", () => {
        if (this.ws && document.visibilityState === "visible") {
          try {
            this.send({ event: "app:focus", payload: { app_id: this.id } });
          } catch (_) {}
        }
      });
    }

    createHandler() {
      const handler = new Handler();

      console.log("Handler created: ", handler.handlerID);

      this.appEventHandlers.set(handler.handlerID, handler);
      return handler;
    }

    removeHandler(handlerID) {
      this.appEventHandlers.delete(handlerID);
      console.log("Handler Removed: ", handlerID);
    }

    _forceReconnect(reason = "manual trigger") {
      console.log(reason + " → forcing reconnect...");
      this._clearReconnectTimer();
      this.reconnectAttempts = 0; // reset attempts on resume
      this._connect();
    }

    _connect() {
      if (this.ws) return;

      //  const protocol = location.protocol === "https:" ? "wss" : "ws";
      const url = `${getWsUrl()}/app/${this.id}`;
      // const url = `${protocol}://${location.host}/app/${this.id}`;
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
            this.config = message.payload.config;
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

    on(event, callback) {
      this.addEvent(event, callback);
    }

    off(event, callback) {
      if (!this.eventCallbacks[event]) return;
      this.eventCallbacks[event] = this.eventCallbacks[event].filter(
        fn => fn !== callback
      );
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

    async run(callback = null) {
      if (this.ws && this.ws.readyState < WebSocket.CLOSING) return;
      if (typeof callback === "function") {
        this.on("connected", callback);
      }
      this._connect();
    }
  }

  class AppTask {
    constructor(name, handler, func, once = true) {
      this.name = name;
      this.handler = handler;
      this.func = func;

      this.task_result = null;
      this.running = false;

      this.once = once;
      this.completed = false;

      this.handler.onData(data => {
        if (data.status === "ended") {
          this.running = false;
          this.completed = true;
        }
      });
    }

    async __run(args = "") {
      if (this.once && this.completed) throw Error("Task already completed");

      this.task_result = await this.func("tasks.run_task", {
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

      await this.func("tasks.send_input", {
        args: [this.task_result.data, input]
      });
    }

    on(callback) {
      this.handler.onData(callback);
    }

    async kill() {
      await this.func("tasks.kill", {
        args: [this.task_result.data]
      });
    }
  }

  class AppTasks {
    constructor(app) {
      if (!app) {
        throw Error("AppTasks must require KikxApp, KikxAppClient");
      }

      this.app = app;
    }

    runFunc = (name, options) => {
      return this.app.func(name, options);
    };

    createTask(name, once = true) {
      if (!this.app.func) {
        throw Error("KikxAppClient is required as app to create task");
      }

      const handler = this.app.createHandler();

      if (once) {
        handler.onended = () => {
          this.app.removeHandler(handler.handlerID);
        };
      }

      return new AppTask(name, handler, this.runFunc, once);
    }

    async runTask(name, callback) {
      const task = this.createTask(name);
      task.on(callback);

      return await task.__run();
    }

    async runTaskSync(name) {
      const fullData = [];
      let flag = false;

      return new Promise((resolve, reject) => {
        try {
          this.runTask(name, data => {
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
    }

    async quickTask(name, ...input) {
      return await this.runFunc("tasks.run_once", {
        args: [name],
        options: {
          task_input: input.join("\n")
        }
      });
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

  // TODO: recreate
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

  class AppInstaller {
    constructor(app) {
      this.app = app;
      this.tempId = null;
      this.manifest = null;
    }

    async prepare(file) {
      const formData = new FormData();
      formData.append("file", file);

      const res = await this.app.system.request(
        "app/prepare-install",
        "POST",
        formData,
        false
      );

      if (!res.ok) {
        throw new Error(res.error);
      }

      this.tempId = res.data.temp_id;
      this.manifest = res.data.manifest;

      return res.data;
    }

    async prepare_github(owner, repo, tag = null) {
      const payload = { owner, repo };
      if (tag) payload.tag = tag;

      const res = await this.app.system.request(
        "app/prepare-install/github",
        "POST",
        payload
      );

      if (!res.ok) {
        throw new Error(res.error);
      }

      this.tempId = res.data.temp_id;
      this.manifest = res.data.manifest;

      return res.data;
    }

    async install() {
      if (!this.tempId) {
        throw new Error("No prepared installation session");
      }

      const res = await this.app.system.request(
        `app/confirm-install?temp_id=${this.tempId}`,
        "POST"
      );

      if (!res.ok) {
        throw new Error(res.error);
      }

      this.tempId = null;
      return res.data;
    }

    async cancel() {
      if (!this.tempId) {
        return { res: "already_cancelled" };
      }

      const res = await this.app.system.request(
        `app/cancel-install?temp_id=${this.tempId}`,
        "POST"
      );

      this.tempId = null;

      if (!res.ok) {
        throw new Error(res.error);
      }

      return res.data;
    }
  }

  class AppUninstaller {
    constructor(app, name) {
      this.app = app;
      this.name = name;
    }

    async uninstall() {
      const res = await this.app.system.request(
        `app/uninstall?app_name=${this.name}`,
        "DELETE"
      );

      if (!res.ok) {
        throw new Error(res.error);
      }

      return res.data;
    }
  }

  exports.AppInstaller = AppInstaller;
  exports.AppTasks = AppTasks;
  exports.AppUninstaller = AppUninstaller;
  exports.FileSystemService = FileSystemService;
  exports.KikxApp = KikxApp;
  exports.KikxAppClient = KikxAppClient;
  exports.ProxyService = ProxyService;
  exports.Service = Service;
  exports.SystemService = SystemService;
  exports.apiUrl = apiUrl;
  exports.configureUrls = configureUrls;
  exports.getAppID = getAppID;
  exports.getUrl = getUrl;
  exports.getWsUrl = getWsUrl;

}));
