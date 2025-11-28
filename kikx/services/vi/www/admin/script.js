function generateUID(len = 16) {
  const chars =
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  return Array.from(crypto.getRandomValues(new Uint8Array(len)))
    .map(x => chars[x % chars.length])
    .join("");
}

const escapeHTML = str => $("<div>").text(str).html(); // Escape potentially malicious input

function pop(obj, key) {
  const value = obj[key];
  delete obj[key];
  return value;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isBaseDirectory(path) {
  return !path.includes("/");
}

function getParentPath(path) {
  const hasLeadingSlash = path.startsWith("/");
  const parts = path.replace(/^\/+|\/+$/g, "").split("/");
  parts.pop();
  const parent = parts.join("/");
  return hasLeadingSlash ? "/" + parent : parent || "/";
}

function onKeyboardChange(callback) {
  let initialHeight = window.innerHeight;
  let keyboardOpen = false;

  function handleResize() {
    const diff = initialHeight - window.innerHeight;
    const isOpen = diff > 150; // threshold in px, adjust as needed
    if (isOpen !== keyboardOpen) {
      keyboardOpen = isOpen;
      callback(keyboardOpen);
    }
  }

  window.addEventListener("resize", handleResize);
}

class Events {
  constructor() {
    this.events = {}; // { eventName: [callbacks...] }
  }

  // Register a callback for an event
  on(eventName, callback) {
    if (!this.events[eventName]) {
      this.events[eventName] = [];
    }
    this.events[eventName].push(callback);
  }

  // Emit (trigger) an event with optional arguments
  emit(eventName, ...args) {
    if (this.events[eventName]) {
      this.events[eventName].forEach(callback => callback(...args));
    }
  }

  // Remove a specific callback or all callbacks for an event
  off(eventName, callback) {
    if (!this.events[eventName]) return;
    if (!callback) {
      delete this.events[eventName];
    } else {
      this.events[eventName] = this.events[eventName].filter(
        cb => cb !== callback
      );
    }
  }
}

class VISClient {
  constructor(authKey) {
    this.authKey = authKey;
    this.activeClients = {};
    this.events = new Events();
    this.resolveListCallbacks = {};
  }
  _connect() {
    this.ws = new WebSocket(
      `ws://localhost:8000/service/vi/sclient?key=${this.authKey}`
    );
    // connection open
    this.ws.onopen = e => {
      console.log("connected");
      this.events.emit("ws:open", e);
    };
    this.ws.onmessage = event => {
      const data = JSON.parse(event.data);
      this.onData(data);
      this.events.emit("ws:data", data);
    };
    this.ws.onclose = e => {
      this.events.emit("ws:close", e);
    };
  }
  sendJson(data) {
    this.ws.send(JSON.stringify(data));
  }
  onData(data) {
    if (data.event === "connected") {
      this.activeClients = data.payload;
      this.events.emit("connected", data.payload);
    } else if (data.event === "client:connected") {
      this.activeClients[data.payload.cid] = data.payload;
      this.events.emit("client:connected", data.payload);
    } else if (data.event === "client:disconnected") {
      pop(this.activeClients, data.payload);
      this.events.emit("client:disconnected", data.payload);
    } else if (data.event === "exec") {
      // response resolve
      const callback = pop(this.resolveListCallbacks, data.id);
      callback(data.payload);
    } else {
      console.log(data);
    }
  }
  execCommand(cid, command, callback) {
    const uid = generateUID();
    this.sendJson({
      event: "exec",
      payload: {
        cid: cid,
        command: command,
        id: uid
      }
    });
    this.resolveListCallbacks[uid] = callback;
  }
  on(...args) {
    this.events.on(...args);
  }
  run() {
    this._connect();
  }
}

function scrollToBottom($element) {
  if ($element && $element.length) {
    $element.scrollTop($element[0].scrollHeight);
  }
}

// icon sets
const ICONS = {
  linux: "assets/icons/linux.svg",
  Linux: "assets/icons/linux.svg"
};

const scriptIcon = ext => {
  return {
    ".js":
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 16 16"><path fill="currentColor" d="M5.15 7.15a.5.5 0 0 1 .707 0l2 2a.5.5 0 0 1 0 .707l-2 2a.5.5 0 0 1-.707-.707L6.8 9.5L5.15 7.85a.5.5 0 0 1 0-.707zM11 11.5a.5.5 0 0 0-.5-.5h-2a.5.5 0 0 0 0 1h2a.5.5 0 0 0 .5-.5"/><path fill="currentColor" fill-rule="evenodd" d="M4 1c-1.1 0-2 .895-2 2v10c0 1.1.895 2 2 2h8c1.1 0 2-.895 2-2V5.5a.5.5 0 0 0-.146-.354l-4-4A.5.5 0 0 0 9.5 1zM3 3a1 1 0 0 1 1-1h5v3.5a.5.5 0 0 0 .5.5H13v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zm9.29 2L10 2.71V5z" clip-rule="evenodd"/></svg>',
    "": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path fill="currentColor" fill-opacity="0" stroke-dasharray="64" stroke-dashoffset="64" d="M12 7h8c0.55 0 1 0.45 1 1v10c0 0.55 -0.45 1 -1 1h-16c-0.55 0 -1 -0.45 -1 -1v-11Z"><animate fill="freeze" attributeName="fill-opacity" begin="0.8s" dur="0.15s" values="0;0.3"/><animate fill="freeze" attributeName="stroke-dashoffset" dur="0.6s" values="64;0"/></path><path d="M12 7h-9v0c0 0 0.45 0 1 0h6z" opacity="0"><animate fill="freeze" attributeName="d" begin="0.6s" dur="0.2s" values="M12 7h-9v0c0 0 0.45 0 1 0h6z;M12 7h-9v-1c0 -0.55 0.45 -1 1 -1h6z"/><set fill="freeze" attributeName="opacity" begin="0.6s" to="1"/></path></g></svg>'
  }[ext];
};

// show active list of clients (UI)
const showActiveList = () => {
  $("#device-frame").hide();
  $("#devices-list-panel").fadeIn();
};

/// ========== ///
async function main(app) {
  let activeClient = null; //
  let currentScriptsPath = null;

  let $console = $("#console");

  // run command in client
  const runCommand = (command, callback) => {
    // return when no active and null command
    if (!activeClient || command.length <= 0) return;
    app.execCommand(activeClient, command, callback);
  };

  const asyncRunCommand = command => {
    return new Promise((resolve, reject) => {
      if (!activeClient || command.length <= 0) {
        return reject(new Error("Invalid command or no active client"));
      }

      app.execCommand(activeClient, command, data => {
        resolve(data);
      });
    });
  };

  const vi = {
    scr: {
      append: txt => $console.append(txt),
      clear: () => $console.empty(),
      print: text => $console.append(escapeHTML(text))
    },
    script: {
      asyncRun: asyncRunCommand,
      run: runCommand
    }
  };

  const runScript = async path => {
    if (!activeClient) return;

    const res = await fetch(`/service/vi/script/${path}?key=${app.authKey}`);
    const code = await res.text();
    try {
      eval(code);
    } catch (e) {
      // toast message
      console.error(e);
    }
  };
  // Load scripts based on path
  const loadScripts = async path => {
    currentScriptsPath = path;

    // show or hide back button
    $("#scripts-path").text(currentScriptsPath);
    $("#back-btn").toggle(!isBaseDirectory(path));

    $scriptsListEl = $("#scripts-list");
    $scriptsListEl.empty();

    const res = await fetch(
      `/service/vi/list-scripts/${path}?key=${app.authKey}`
    );
    // [ { items: {}, path: str } ]
    const data = await res.json();

    // looping throuh directory
    data.items.forEach(item => {
      const $el = $(`
        <div class="p-1.5 border-b border-gray-400 ${
          item.isdir ? "bg-gray-400/40" : ""
        } flex items-center gap-1 active:bg-orange-400/60">
          <div>${scriptIcon(escapeHTML(item.ext))}</div>
          <div>${escapeHTML(item.name)}</div>
        </div>
      `);

      $el.on("click", () => {
        if (!item.isdir) {
          runScript(item.path);
        } else {
          loadScripts(item.path);
        }
      });

      $scriptsListEl.append($el);
    });
  };

  // back button bind
  $("#back-btn").on("click", () => {
    loadScripts(getParentPath(currentScriptsPath));
  });

  const setActiveClient = cid => {
    $("#devices-list-panel").fadeOut();
    $("#device-frame").fadeIn();
    // if client already active then dont update values
    // if (cid === activeClient) return;

    activeClient = cid;
    // updating device meta values
    runCommand("whoami", data => {
      $("#device-name").text(data.stdout.trim());
    });
    runCommand("uname", data => {
      const osName = data.stdout.trim().toLowerCase();
      // setting icon and os name
      $("#device-icon").attr("src", ICONS[osName]);
      $("#device-meta").text(osName);

      loadScripts(osName);
    });
    $("#device-cid").text(cid);
  };

  // update active clients panel
  const updateActiveClientsUI = () => {
    // Clear existing list before re-rendering
    $("#active-list").empty();

    Object.keys(app.activeClients).forEach(cid => {
      // Create a div for each client
      const clientDiv = $(`
      <div 
        class="w-full border rounded cursor-pointer active:bg-white/20 overflow-hidden"
        data-cid="${cid}"
      >
        <div class="bg-blue-400/60 text-center p-1">${cid}</div>
        <div class="p-2 bg-blue-400/20">${escapeHTML(
          app.activeClients[cid].name
        )}</div>
      </div>
    `);

      // Attach click handler
      clientDiv.on("click", () => {
        setActiveClient(cid);
        console.log("Active client set to:", activeClient);
      });
      // Adding to dom
      $("#active-list").append(clientDiv);
    });
  };

  // ----------------- start here
  app.on("connected", clients => {
    // on sclient connected
    updateActiveClientsUI();
  });
  app.on("client:connected", () => {
    // on new client connected
    updateActiveClientsUI();
  });
  app.on("client:disconnected", cid => {
    // adding offline chip after device-name
    if (activeClient === cid) {
      $("#device-name").append(
        "<span class='text-white bg-red-400/60 px-2 mx-2 text-xs rounded'>OFFLINE</span>"
      );
    }
    activeClient = null;
    // on new client connected
    updateActiveClientsUI();
    // if its active
  });

  // --------- input send bindings
  const sendCommand = () => {
    const $inputEl = $("#input-el");

    const command = $inputEl.val().trim();
    $inputEl.val("");

    if (command === "clear") {
      // clearing
      return $("#console").empty();
    }

    runCommand(command, data => {
      // check for Error
      if (data.returncode === 0) {
        $("#console").append(
          `<div class="text-md">${escapeHTML(data.stdout)}</div>`
        );
      } else {
        // some error
        $("#console").append(
          `<div class="text-md"><span class="text-red-400">Error: (${escapeHTML(
            data.returncode
          )})</span> ${escapeHTML(data.stderr)}</div>`
        );
      }
      scrollToBottom($("#console"));
    });
  };

  $("#input-send-btn").on("click", () => sendCommand());
  // Example 1: Binding Enter on a specific input
  $("#input-el").on("keypress", function (e) {
    if (e.which === 13) {
      // 13 is the Enter key
      e.preventDefault(); // prevent form submission if needed
      sendCommand();
      // Add your custom code here
    }
  });

  // hide dock on input-el focus
  onKeyboardChange(active => {
    $("#dock").toggle(!active);
  });

  // start
  app.run();
}

$(() => {
  const params = new URLSearchParams(window.location.search);

  const authKey = params.get("key"); //

  main(new VISClient(authKey));
});
