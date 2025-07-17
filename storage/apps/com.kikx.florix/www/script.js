let mainScript = "neko";
// ========== ELEMENTS ==========

const $panel = $("#panel");
const $taskInputPanel = $("#task-input-panel");
const $taskInputBox = $("#task-input-box");
const $scriptName = $("#script-name");

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

//function toggleInputPanel() {
//if (AppConfig.blockUserInput && $taskInputPanel.is(":hidden")) return;
//  if (AppConfig.blockUserInput || !currentTask) return;
//  $taskInputPanel.toggle();
//}

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
  //$taskInputPanel.addClass("border-blue-500");

  if (focus) {
    $taskInputBox.focus();
  }
}

const setScriptName = name => {
  $scriptName.text(name.toUpperCase());
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

function runScript(cmd) {
  if (currentTask || !cmd) return;

  runningScript = cmd;

  const splitName = cmd.split(" ");
  let scriptName = splitName[0];

  if (splitName.length > 1) {
    scriptName = splitName[1];
  }
  const task = createTask(cmd);

  $panel.html(`
    <div class="w-full h-full bg-gray-800/40 flex flex-col justify-center items-center font-bold ">
      <div class="border-b w-6 h-6 animate-spin rounded-full"></div>
    </div>
  `);

  //const $scriptName = $("#script-name");

  setScriptName(scriptName.split("/").at(-1));

  let errorFlag = false;
  let successFlag = false;

  task.on(data => {
    switch (data.status) {
      case "started": // on running
        successFlag = true;

        // $("#panel-clear-btn").hide();

        $("#task-reload-btn").hide();
        $("#task-home-btn").hide();

        $("#task-stop-btn").show();
        $("#task-run-btn").hide();
        //$("#task-input-toggle-btn").show();
        $("#script-name-input").hide();

        $scriptName.css("color", "#66d9e8");

        currentTask = task;
        break;

      case "ended": // on stoped
        setAppDefaultConfig();
        $taskInputPanel.hide();

        $("#task-reload-btn").show();
        $("#task-home-btn").show();

        $("#task-stop-btn").hide();
        $("#task-run-btn").show();
        // $("#task-input-toggle-btn").hide();
        //  $("#panel-clear-btn").show();

        $("#script-name-input").show();
        //$("#script-name").text(`Ended: ${scriptName}`);
        //$("#script-name").html(
        // `<div class="text-red-400/80">${domPurify(scriptName)}</div>`
        //);
        if (!errorFlag) $scriptName.css("color", "#71dd8a");

        currentTask = null;
        scrollToBottom();
        break;

      case "output":
        exec(data.output);
        break;

      case "error":
        errorFlag = true;
        $scriptName.css("color", "#f28b82");
        $panel.text(`Error: ${data.output}`);
        break;
    }
  });

  task.run();
}

function runStartScript() {
  runScript(mainScript);
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

$(() => {
  $("#task-run-btn").on("click", () => {
    const cmd = $("#script-name-input").val().trim();
    if (!cmd) return;

    $("#script-name-input").val("");
    runScript(cmd);
  });

  $("#task-reload-btn").on("click", () => {
    runScript(runningScript);
  });

  $taskInputBox.on("keydown", function (event) {
    if (event.key === "Enter" || event.keyCode === 13) {
      _sendUserInput();
    }
  });
});

// ========== APP INITIALIZATION ==========

kikxApp.run(() => {
  runScript(mainScript);
});

requestWakeLock();
