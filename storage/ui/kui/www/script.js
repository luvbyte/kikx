const client = new Client(); // Client instance
let kuiConfig = {
  bg: "bg.jpg"
};
let screenOrientation = "portrait";
let isBrowserFullScreen = false;
let isFullScreen = false;

let $centerControlPanel = $("#center-control-panel");
//let popUps = [];

const activeFullScreen = active => {
  isFullScreen = active;
  $("#top-panel").toggle(!active);
};
const toggleFullScreen = () => {
  activeFullScreen(!isFullScreen);
};

const rotateScreen = async () => {
  let orient = screenOrientation === "portrait" ? "landscape" : "portrait";
  await lockOrientation(orient);
};

// Orientation Handlers
function handleLandscape() {
  screenOrientation = "landscape";
  activeFullScreen(true);
  console.log("Landscape mode detected");
}

function handlePortrait() {
  screenOrientation = "portrait";
  // activeFullScreen(false);
  console.log("Portrait mode detected");
}

// Load and apply user config
async function updateKuiConfig() {
  // const res = await client.fs.readFile("home://.config/kui/config.json");
  const res = await client.fs.readFile(
    "storage://root/.config/kui/config.json"
  );

  if (res.data) {
    Object.assign(kuiConfig, JSON.parse(await blobToText(res.data)));
  }

  $("#apps").css("background-image", `url("${kuiConfig.bg}")`);
}

// Handle initial loading
$(function () {
  const initialHeight = window.innerHeight;

  // catching notify event
  client.on("app:notify", payload => {
    addNotify(payload, !client.userSettings.silent);
  });
  client.run(async payload => {
    const userRes = await client.func("user_data");
    if (userRes.data) updateUserData(userRes.data);

    loadApps(payload);
    await updateKuiConfig();

    $("#loading-screen").fadeOut(400, function () {
      $(this).remove();
    });
  });

  // apps open swipe up
  initTouchGestures("#apps", {
    swipeUp: () => {
      $("#apps-menu").slideDown().removeClass("hidden");
    }
  });

  // creating swipe bubble
  createSwipeBubble("#swipe-bubble");
  // orientation detection
  detectOrientation(handlePortrait, handleLandscape);

  // center rotation toogle button
  $("#center-rotateToggleButton").on("click", function () {
    rotateScreen();
    $centerControlPanel.hide();
  });
  // center fullscreen toogle button
  $("#center-fsToggleButton").on("click", function () {
    toggleFullScreen();
  });
  // center-panel hide on click outside
  $centerControlPanel.on("click", function (e) {
    // Only hide if the user clicked directly on #center-control-panel (not its children)
    if (e.target === this) {
      $(this).fadeOut(400);
    }
  });
  // browser full screen
  $("#cc-browser-fullscreen-btn").on("click", function () {
    toggleBrowserFullScreen();
  });

  // if its webview
  if (isAndroidWebView()) {
    $("#cc-browser-fullscreen-btn").hide();
    $("#center-rotateToggleButton").hide();
  }
});

const createSwipeBubble = element => {
  const $bubble = $(element);
  const $bubbleGhostButton = $("#swb-ghost-btn");

  $bubbleGhostButton.on("dblclick", function () {
    $bubble.show();
    $(this).hide();
  });

  let shrinkTimer = null;
  let bubbleActive = false;
  // this will be added on shrink
  const inactiveClasses = "w-8 h-16 -right-4 border";
  // this will added on expand
  const activeClasses = "w-32 h-32 right-0 landscape:w-1/4 landscape:h-1/2";

  const bubbleHoldColor = "bg-red-400/60";

  const shrinkBubble = () => {
    $bubble.removeClass(bubbleHoldColor).addClass("bg-blue-400/80");

    $bubble.removeClass(activeClasses).addClass(inactiveClasses);
    bubbleActive = false;
  };

  const startShrinkTimer = () => {
    clearTimeout(shrinkTimer);
    shrinkTimer = setTimeout(shrinkBubble, 2000);
  };

  const expandBubble = () => {
    clearTimeout(shrinkTimer);
    $bubble.removeClass(inactiveClasses).addClass(activeClasses);
    bubbleActive = true;
    startShrinkTimer();
  };

  const forceClose = () => {
    clearTimeout(shrinkTimer);
    shrinkBubble();
  };

  // Ensure no duplicate listeners
  //$bubble.off("click touchstart touchmove");
  // $bubble.on("click touchstart touchmove", expandBubble);
  $bubble.off("click");
  $bubble.on("click", expandBubble);

  // Optional: auto shrink after load
  // startShrinkTimer();

  // Shrink when clicking outside
  $(document).on("click touchstart", e => {
    if (
      bubbleActive &&
      !$bubble.is(e.target) &&
      $bubble.has(e.target).length === 0
    ) {
      shrinkBubble();
    }
  });
  window.addEventListener("blur", () => {
    // Possibly clicked inside iframe
    if (bubbleActive) {
      shrinkBubble();
    }
  });

  // Initialize touch gestures
  initTouchGestures(element, {
    swipeDown: () => {
      if (typeof showHome === "function") {
        closeCurrentApp();
        forceClose();
      }
    },
    swipeUp: () => {
      if (typeof toggleRecentApps === "function") {
        toggleRecentApps();
        forceClose();
      }
    },
    swipeLeft: () => {
      if (typeof closeCurrentApp === "function") {
        showHome();
        forceClose();
      }
    },
    swipeRight: () => {
      // switchLastApp();
      //toggleAppsMenu();
      // forceClose();
      $centerControlPanel.fadeIn(400);
      forceClose();
    },
    longPress: () => {
      if (bubbleActive) {
        clearTimeout(shrinkTimer);
        $bubble.removeClass("bg-blue-400/80").addClass(bubbleHoldColor);
      } else {
        $bubble.hide();
        $bubbleGhostButton.show();
      }
    }
  });
};
