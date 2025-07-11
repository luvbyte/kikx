let mainScript = "neko";
// ========== ELEMENTS ==========

const $panel = $("#panel");
const $taskInputPanel = $("#task-input-panel");
const $taskInputBox = $("#task-input-box");
const $scriptName = $("#script-name");

// ========== GLOBAL STATE ==========

let currentTask = null;
let runningScript = "";

const NekoConfig = {
  rawOutput: false,
  rawOutputHTML: false,

  blockUserKillTask: false,
  blockUserInput: false,
  blockUserClear: false
};

// ========== CONFIG HELPERS ==========

const blockUserInput = (block = true) => {
  NekoConfig.blockUserInput = block;
  // $("#task-input-toggle-btn").toggle(block);
};

const blockUserClear = (block = true) => {
  NekoConfig.blockUserClear = block;
  $("#panel-clear-btn").toggle(!block);
};

const setRawOutput = (enabled = true) => {
  NekoConfig.rawOutput = enabled;
};

const blockUserKillTask = (block = true) => {
  NekoConfig.blockUserKillTask = block;
};

const setRawOutputHTML = (block = true) => {
  NekoConfig.rawOutputHTML = block;
};

const setNekoDefaultConfig = () => {
  setRawOutput(false);
  setRawOutputHTML(false);

  blockUserInput(false);
  blockUserClear(false);
  blockUserKillTask(false);
};

// ========== UI HELPERS ==========

function scrollToBottom(selector = null) {
  const el = selector ? $(selector) : $panel;
  const scrollTop = el.scrollTop();
  const scrollHeight = el.prop("scrollHeight");
  const clientHeight = el.innerHeight();

  const distanceFromBottom = scrollHeight - (scrollTop + clientHeight);
  const threshold = 100;

  if (distanceFromBottom < threshold) {
    el.scrollTop(scrollHeight);
  }
}

function clearPanel(force = false) {
  if (!NekoConfig.blockUserClear || force) {
    $panel.empty();
  }
}

function toggleInputPanel() {
  //if (NekoConfig.blockUserInput && $taskInputPanel.is(":hidden")) return;
  if (NekoConfig.blockUserInput || !currentTask) return;
  $taskInputPanel.toggle();
}

function askInput(placeholder = "") {
  if (NekoConfig.blockUserInput) {
    return sendError("Input blocked: blockUserInput is true");
  }

  kikxApp.system.notify({
    msg: `Require input - ${placeholder}`,
    type: "info"
  });

  let animation = null;
  // only animate if visible to avoid ask_input autohide property
  if ($taskInputPanel.is(":hidden")) {
    animation = "slideUp";
  }

  //$taskInputPanel.show(animation);
  $taskInputPanel.show(animation);

  $taskInputBox.attr("placeholder", placeholder);
  $taskInputPanel.addClass("border-blue-500");
}

const setScriptName = name => {
  $scriptName.text(name.toUpperCase());
};
// ========== TASK OUTPUT HANDLER ==========

function exec(outputText) {
  console.log(outputText);

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
        if (NekoConfig.rawOutput) {
          if (NekoConfig.rawOutputHTML) {
            $panel.append(outputText);
          } else {
            $panel.append($("<div>").text(outputText));
          }
        }
    }
  } catch (err) {if (NekoConfig.rawOutput) {
          if (NekoConfig.rawOutputHTML) {
            $panel.append(outputText);
          } else {
            $panel.append($("<div>").text(outputText));
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

        $scriptName.css("color", "#fffacd");

        currentTask = task;
        break;

      case "ended": // on stoped
        setNekoDefaultConfig();

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
        if (!errorFlag) $scriptName.css("color", "#b0ffb0");

        currentTask = null;
        scrollToBottom();
        break;

      case "output":
        exec(data.output);
        break;

      case "error":
        errorFlag = true;
        $scriptName.css("color", "#ffb3b3");
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
  if (currentTask && !NekoConfig.blockUserKillTask) {
    currentTask.kill();
    setNekoDefaultConfig();
  }
}

function _sendUserInput() {
  const cmd = $taskInputBox.val();
  if (!cmd || NekoConfig.blockUserInput) return;

  sendInput(cmd);
  $taskInputBox.val("");
  $taskInputPanel.removeClass("border-blue-500");

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
      // event.preventDefault();_sendUserInput
      _sendUserInput();
    }
  });
});

// ========== APP INITIALIZATION ==========

kikxApp.run(() => {
  runScript(mainScript);
});

requestWakeLock();
