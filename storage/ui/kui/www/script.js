const client = new Client();
let kuiConfig = { bg: "bg.png" };
let screenOrientation = "portrait";
let isBrowserFullScreen = false;
let isFullScreen = false;

const setFullScreen = active => {
  isFullScreen = active;
  $("#top-panel").toggle(!active);
  $("#control-center").hide();
};

const toggleFullScreen = () => setFullScreen(!isFullScreen);

const rotateScreen = async () => {
  const newOrientation =
    screenOrientation === "portrait" ? "landscape" : "portrait";
  await lockOrientation(newOrientation);
};

const handleOrientation = orientation => {
  $("#control-center").hide();
  screenOrientation = orientation;
  setFullScreen(orientation === "landscape");
  console.log(
    `${
      orientation.charAt(0).toUpperCase() + orientation.slice(1)
    } mode detected`
  );
};

// set valid background-image
function setValidBackground(url, fallback = "bg.png") {
  const img = new Image();
  img.onload = () => $("#apps").css("background-image", `url("${url}")`);
  img.onerror = () => $("#apps").css("background-image", `url("${fallback}")`);
  img.src = url;
}

const updateKuiConfig = async (fth = true) => {
  if (fth) {
    const res = await client.fs.readFile("home://.config/kui/config.json");

    if (res.data)
      try {
        Object.assign(kuiConfig, JSON.parse(await blobToText(res.data)));
      } catch (_) {
        // TODO: show error as alert notfy
      }
  }
  // setting default bg if not found
  setValidBackground(kuiConfig.bg);
  //$("#apps").css("background-image", `url("${kuiConfig.bg}")`);
};

$(function () {
  client.on("app:notify", payload => {
    addNotify(payload, !client.userSettings.silent);
  });

  client.run(async payload => {
    const userRes = await client.func("user_data");
    if (userRes.data) updateUserData(userRes.data);

    loadApps(payload);
    await updateKuiConfig();
    $("#loading-screen").fadeOut(400, () => $(this).remove());
  });

  initTouchGestures("#apps", {
    swipeUp: () => $("#apps-menu").fadeIn()
  });

  $appsMenu.on("click", function () {
    $(this).fadeOut(250);
  });

  createSwipeBubble("#swipe-bubble");
  detectOrientation(
    () => handleOrientation("portrait"),
    () => handleOrientation("landscape")
  );

  $("#center-rotateToggleButton").on("click", () => {
    rotateScreen();
    $centerControlPanel.hide();
  });

  $("#center-fsToggleButton").on("click", toggleFullScreen);

  $centerControlPanel.on("click", e => {
    if (e.target === e.currentTarget) $(e.currentTarget).fadeOut(400);
  });

  $("#cc-browser-fullscreen-btn").on("click", () => {
    toggleBrowserFullScreen();
  });

  if (isAndroidWebView()) {
    $("#cc-browser-fullscreen-btn, #center-rotateToggleButton").hide();
  }

  // hide cc on outside click
  $controlCenter.on("click", function (event) {
    if (event.target === this) {
      $(this).fadeOut();
    }
  });
});

const createSwipeBubble = selector => {
  const $bubble = $(selector);
  const $ghostButton = $("#swb-ghost-btn");

  let shrinkTimer = null;
  let isActive = false;

  const inactiveClasses = "border w-8 h-20 -right-4";
  const activeClasses = "w-36 h-36 right-0 landscape:w-1/4 landscape:h-1/2";
  const bubbleHoldColor = "bg-red-400/60";

  const shrink = () => {
    $bubble
      .removeClass(bubbleHoldColor)
      .removeClass(activeClasses)
      .addClass(inactiveClasses);
    isActive = false;
  };

  const scheduleShrink = () => {
    clearTimeout(shrinkTimer);
    shrinkTimer = setTimeout(shrink, 2000);
  };

  const expand = () => {
    clearTimeout(shrinkTimer);
    $bubble.removeClass(inactiveClasses).addClass(activeClasses);
    isActive = true;
    scheduleShrink();
  };

  const forceClose = () => {
    clearTimeout(shrinkTimer);
    shrink();
  };

  $ghostButton.on("click", () => {
    $bubble.show();
    $ghostButton.hide();
  });

  $bubble.off("click").on("click", expand);

  $(document).on("click touchstart", e => {
    if (isActive && !$bubble.is(e.target) && !$bubble.has(e.target).length) {
      shrink();
    }
  });

  window.addEventListener("blur", () => isActive && shrink());

  initTouchGestures(selector, {
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
      $centerControlPanel.fadeIn(400);
      forceClose();
    },
    longPress: () => {
      if (isActive) {
        clearTimeout(shrinkTimer);
        $bubble.removeClass("bg-blue-400/80").addClass(bubbleHoldColor);
      } else {
        $bubble.hide();
        $ghostButton.show();
      }
    }
  });
};

requestWakeLock();
