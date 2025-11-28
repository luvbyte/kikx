let mainTask = "neko";

function _deepCleanObject(obj) {
  for (let key in obj) {
    if (obj.hasOwnProperty(key)) {
      let value = obj[key];

      // Recursively clean if it's an object or array
      if (typeof value === "object" && value !== null) {
        deepCleanObject(value);
      }

      // Delete the key from the parent object
      delete obj[key];
    }
  }
}

// ========== ELEMENTS ==========

const $panel = $("#panel");

const $taskInputPanel = $("#task-input-panel");
const $taskInputBox = $("#task-input-box");

const $taskTitle = $("#task-title");

let rawOutputPanel = $panel;

// ========== GLOBAL STATE ==========

let currentTask = null;
let runningScript = "";

// usefull for scripts
const tempObjects = {};
const AppConfig = {
  rawOutput: true, // stdout to panel
  rawOutputHTML: false, // adds stdout html code

  blockUserKillTask: false, // stop user kill task
  blockUserInput: true, // Blocks user input
  blockUserClear: true, // clear button at top

  autoAppendScroll: true // auto scrolls on output
};

// ========== CONFIG HELPERS ==========
const blockUserInput = (block = true) => {
  AppConfig.blockUserInput = block;
};

const blockUserClear = (block = true) => {
  AppConfig.blockUserClear = block;
  $("#panel-clear-btn").toggle(!block);
};

const setRawOutput = (enable = true) => {
  AppConfig.rawOutput = enable;
};

const setAutoAppendScroll = (enable = true) => {
  AppConfig.autoAppendScroll = enable;
};

const blockUserKillTask = (block = true) => {
  AppConfig.blockUserKillTask = block;
};

const setRawOutputHTML = (block = true) => {
  AppConfig.rawOutputHTML = block;
};

const setRawOutputPanel = selector => {
  rawOutputPanel = $(selector);
};

const setAppDefaultConfig = () => {
  setRawOutput(true);
  setRawOutputHTML(false);

  blockUserInput(true);
  blockUserClear(true);
  blockUserKillTask(false);
  setAutoAppendScroll(true);

  rawOutputPanel = $panel;
  _deepCleanObject(tempObjects);
};

// ========== UI HELPERS ==========
function scrollToBottom(selector = null) {
  const $el = selector ? $(selector) : $panel;

  const scrollHeight = $el.prop("scrollHeight");
  const scrollTop = $el.scrollTop();
  const clientHeight = $el.innerHeight();

  if (scrollHeight - (scrollTop + clientHeight) < 100) {
    $el.scrollTop(scrollHeight);
  }
}

// This is usefull for backend html code injection for vframe
function sendArgsJSON(...args) {
  sendInput(JSON.stringify(args));
}

function scrollToTop(selector) {
  $(selector).scrollTop(0);
}

// force clears even clear blocked
function clearPanel(force = false) {
  if (!AppConfig.blockUserClear || force) {
    $panel.empty();
  }
}

function hideInputPanel() {
  $taskInputPanel.hide();
}

function askInput(placeholder = "", focus = false, effect = null) {
  if (AppConfig.blockUserInput) {
    return sendError("Input blocked: blockUserInput is true");
  }

  kikxApp.system.notify({
    msg: `Require input - ${placeholder}`,
    type: "info"
  });

  effect && $taskInputPanel.addClass(`animate__animated animate__${effect}`);

  $taskInputPanel.show();
  $taskInputBox.attr("placeholder", placeholder);

  if (focus) {
    $taskInputBox.focus();
  }
}

const setTaskName = () => {
  $taskTitle.text(runningScript.split(" ")[0].toUpperCase());
};

const setSubTaskName = (name = null) => {
  setTaskName();

  if (name) {
    // Ensure no injection by using jQuery's .text() for plain text and .append() for styling
    const baseText = $taskTitle.text().split(":")[0]; // Remove any previous suffix
    $taskTitle.text(baseText); // Reset text content

    // Create a span with white text using Tailwind, safely add name
    const $styledName = $("<span></span>")
      .addClass("text-white/60")
      .text(` ${name.toUpperCase()}`);

    $taskTitle.append($styledName); // Append the styled name safely
  }
};

// ========== TASK OUTPUT HANDLER ==========
function exec(outputText) {
  // Handles non-JSON or unrecognized events
  function _defaultOutput(text) {
    if (AppConfig.rawOutput) {
      const content = AppConfig.rawOutputHTML ? text : $("<div>").text(text);
      rawOutputPanel.append(content);
    }
    if (AppConfig.autoAppendScroll) scrollToBottom();
  }

  let data;
  try {
    data = JSON.parse(outputText);
  } catch {
    return _defaultOutput(outputText);
  }

  const { event, payload } = data;

  if (!event || payload == null) return _defaultOutput(outputText);

  switch (event) {
    case "code":
      try {
        eval(payload);
      } catch (e) {
        console.error("Error in eval:", e);
      }
      break;
    case "html":
      $(payload.element).html(payload.content);
      break;
    case "text":
      $(payload.element).text(payload.content);
      break;
    case "append":
      $(payload.element).append(payload.content);
      break;
    case "clear":
      clearPanel();
      break;
    default:
      _defaultOutput(outputText);
  }
}

// ========== TASK CONTROL ==========
function sendInput(cmd) {
  try {
    if (currentTask && cmd.toString().length > 0) {
      currentTask.send(cmd.toString());
    }
  } catch (e) {
    console.log(e);
  }
}
function sendEvent(event, payload) {
  sendInput(JSON.stringify({ event, payload }));
}
function sendError(error) {
  sendEvent("error", error);
}
function runFlorixTask(cmd) {
  if (currentTask || !cmd) return;

  runningScript = cmd;
  const task = createTask(cmd);

  $panel.html(`
    <div class="w-full h-full bg-gray-800/40 flex flex-col justify-center items-center font-bold ">
      <div class="border-b w-6 h-6 animate-spin rounded-full"></div>
    </div>
  `);

  setTaskName();

  let errorFlag = false;
  let successFlag = false;

  task.on(data => {
    switch (data.status) {
      case "started": // on running
        successFlag = true;

        $("#task-reload-btn").hide();
        $("#task-home-btn").hide();

        $("#task-stop-btn").show();
        $("#task-run-btn").hide();

        $("#task-name-input").hide();

        $taskTitle.css("color", "#66d9e8");

        currentTask = task;
        break;

      case "ended": // on stoped
        setAppDefaultConfig();
        $taskInputPanel.hide();

        $("#task-reload-btn").show();
        $("#task-home-btn").show();

        $("#task-stop-btn").hide();
        $("#task-run-btn").show();

        $("#task-name-input").show();
        if (!errorFlag) $taskTitle.css("color", "#71dd8a");

        currentTask = null;
        scrollToBottom();
        break;

      case "output":
        exec(data.output);
        break;

      case "error":
        errorFlag = true;
        $taskTitle.css("color", "#f28b82");
        $panel.text(`Error: ${data.output}`);
        break;
    }
  });

  task.run();
}

function runMainTask() {
  runFlorixTask(mainTask);
}

function reloadScript() {}

function killTask() {
  if (currentTask && !AppConfig.blockUserKillTask) {
    currentTask.kill();
  }
}

function _sendUserInput() {
  const cmd = $taskInputBox.val();
  if (!cmd || AppConfig.blockUserInput) return;

  sendInput(cmd);
  $taskInputBox.val("");
  // $taskInputPanel.removeClass("border-blue-500");
  $taskInputPanel.removeClass(function (i, c) {
    return c
      .split(" ")
      .filter(className => className.startsWith("animate__"))
      .join(" ");
  });

  $taskInputBox.focus();
}

// used for
const utils = {
  getEventObject(event) {
    if (!event) return null;

    return {
      type: event.type, // e.g. 'click'
      target: {
        tagName: event.target.tagName, // e.g. 'BUTTON'
        id: event.target.id || null,
        className: event.target.className || null,
        name: event.target.name || null,
        value: event.target.value || null,
        dataset: { ...event.target.dataset } // data-* attributes
      },
      timestamp: event.timeStamp, // when the event occurred
      coordinates: {
        x: event.clientX || null, // mouse X position
        y: event.clientY || null // mouse Y position
      },
      key: event.key || null, // for keyboard events
      ctrlKey: event.ctrlKey || false,
      shiftKey: event.shiftKey || false,
      altKey: event.altKey || false,
      metaKey: event.metaKey || false
    };
  }
};
// ========== UI EVENTS ==========

const _startFlorixTask = () => {
  const cmd = $("#task-name-input").val().trim();
  if (!cmd) return;

  $("#task-name-input").val("");
  runFlorixTask(cmd);
};

$(() => {
  $("#task-run-btn").on("click", () => _startFlorixTask());

  $("#task-name-input").on("keydown", function (event) {
    if (event.key === "Enter" || event.keyCode === 13) {
      _startFlorixTask();
    }
  });

  $("#task-reload-btn").on("click", () => {
    runFlorixTask(runningScript);
  });

  $taskInputBox.on("keydown", function (event) {
    if (event.key === "Enter" || event.keyCode === 13) {
      _sendUserInput();
    }
  });
});

// ========== APP INITIALIZATION ==========

kikxApp.run(() => {
  runFlorixTask(mainTask);
});

requestWakeLock();
