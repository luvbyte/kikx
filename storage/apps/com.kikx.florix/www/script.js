let mainTask = "neko";
// ========== ELEMENTS ==========

const $panel = $("#panel");

const $taskInputPanel = $("#task-input-panel");
const $taskInputBox = $("#task-input-box");

const $taskTitle = $("#task-title");

let taskInputOptions = [];
let rawOutputPanel = $panel;

// ========== GLOBAL STATE ==========

let currentTask = null;
let runningScript = "";

const AppConfig = {
  rawOutput: true,
  rawOutputHTML: false,

  blockUserKillTask: false,
  blockUserInput: true,
  blockUserClear: true
};

// ========== CONFIG HELPERS ==========

const blockUserInput = (block = true) => {
  AppConfig.blockUserInput = block;
  // $("#task-input-toggle-btn").toggle(block);
};

const blockUserClear = (block = true) => {
  AppConfig.blockUserClear = block;
  $("#panel-clear-btn").toggle(!block);
};

const setRawOutput = (enabled = true) => {
  AppConfig.rawOutput = enabled;
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

  rawOutputPanel = $panel;
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
  // console.log(outputText);

  try {
    const data = JSON.parse(outputText);
    // if (!data || data.payload === null) return;
    const event = data.event;
    const payload = data.payload;

    switch (event) {
      case "code":
        eval(payload);
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
        if (AppConfig.rawOutput) {
          if (AppConfig.rawOutputHTML) {
            rawOutputPanel.append(outputText);
          } else {
            rawOutputPanel.append($("<div>").text(outputText));
          }
        }
    }
  } catch (err) {
    if (AppConfig.rawOutput) {
      if (AppConfig.rawOutputHTML) {
        rawOutputPanel.append(outputText);
      } else {
        rawOutputPanel.append($("<div>").text(outputText));
      }
    }
  }

  scrollToBottom();
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
    //setAppDefaultConfig();
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
