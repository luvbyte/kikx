const client = new Client();
// default bg if not found other bg
const defaultBackground = "/public/ui/kui/bg.png";
let screenOrientation = "portrait";
let isBrowserFullScreen = false;
let isFullScreen = false;
// congig file
const kuiConfig = {
  filePath: "home://.config/kui/config.json",
  // default config
  config: {
    bg: defaultBackground, // only string, required
    emojis: ["💖"],
    gifs: []
  },
  async load() {
    const res = await client.fs.readFile(kuiConfig.filePath);
    if (res.data) {
      try {
        Object.assign(kuiConfig.config, JSON.parse(await blobToText(res.data)));
      } catch (e) {
        Swal.fire({
          icon: "error",
          title: "Error parsing kui config!!",
          text: e.toString(),
          footer: "using default config"
        });
      }
    }
  },
  async save() {
    try {
      await client.fs.createDirectory("home://.config/kui");
      await client.fs.writeFile(this.filePath, JSON.stringify(this.config));
    } catch (_) {}
  },
  async parse() {
    setValidBackground(kuiConfig.config.bg);
    kawaiGifsModule.config.extendGifs(kuiConfig.config.gifs);
  }
};

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
  kawaiGifsModule.removeAllGifs();
};

// set valid background-image
function setValidBackground(url, fallback = defaultBackground) {
  const img = new Image();
  img.onload = () => $("#apps").css("background-image", `url("${url}")`);
  img.onerror = () => $("#apps").css("background-image", `url("${fallback}")`);
  img.src = url;
}

const updateKuiConfig = async (fth = true) => {
  await kuiConfig.load();
  kuiConfig.parse();
};

// emojis on top header right side on kikx title
const startEmojis = () => {
  const emojis = kuiConfig.config.emojis;
  if (!Array.isArray(emojis)) return;

  if (emojis.length > 0) {
    const items = emojis.map(String); // force everything to string
    const $emoji = $("#emoji");
    $emoji.show();
    if (items.length === 1) {
      // if one element display it
      $emoji.text(items[0]);
    } else if (items.length === 2) {
      // exactly 2 → toggle
      const start = items[0];
      const end = items[1];
      setInterval(() => {
        $emoji.text(start);
        setTimeout(() => {
          $emoji.text(end);
        }, 500);
      }, 2000);
    } else if (items.length > 2) {
      // more than 2 → cycle
      let index = 0;
      setInterval(() => {
        $emoji.text(items[index]);
        index = (index + 1) % items.length;
      }, 1000);
    }
  }
};

$(function () {
  // for this ui cant auto reconnect
  client.on("ws:onclose", e => {
    if (e.code === 1008) {
      // unauthorized reload or show login screen
      location.reload();
    }
    $("#loading-message").text("RE-CONNECTING");
    $("#loading-screen").show();
  });
  client.on("reconnected", () => $("#loading-screen").fadeOut(600));
  // notify event
  client.on("app:notify", payload => {
    if (payload.name === currentApp && !payload.displayEvenActive) return;
    notifyApp.notify(payload);
  });

  client.on("app:notify", payload => {
    if (payload.name === currentApp && !payload.displayEvenActive) return;
    notifyApp.notify(payload);
  });

  client.on("app:alert", payload => {
    const isArrayMessage = Array.isArray(payload.msg);
    const message = isArrayMessage ? payload.msg.join(" ") : payload.msg;

    const notifyPayload = {
      name: payload.name,
      id: payload.id,
      title: payload.title,
      type: payload.type ?? "info",
      msg: isArrayMessage ? message : payload.msg,
      delay: payload.delay ?? 0,
      displayEvenActive: true,
      extra: {
        frames: isArrayMessage ? payload.msg : []
      }
    };

    notifyApp.notify(notifyPayload);
  });

  // closing app by app itself
  client.on("app:close", app => {
    try {
      if (appFrames[app.name].id === app.id) closeApp(app.name);
    } catch (e) {}
  });

  client.run(async payload => {
    await updateKuiConfig();
    startEmojis();

    const userRes = await client.func("user_data");
    if (userRes.data) updateUserData(userRes.data);

    loadApps(payload);
    $("#loading-screen").fadeOut(600);
  });

  initTouchGestures("#apps", {
    swipeUp: () => {
      $("#apps-menu").fadeIn();
    }
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

  $("#cc-image-settings-btn").on("click", () => {
    $controlCenter.hide();
    bgSettingsModule.open();
  });

  if (isAndroidWebView()) {
    $("#cc-browser-fullscreen-btn, #center-rotateToggleButton").hide();
  }

  // cc center bindings
  // waifu toggle button
  $("#center-waifuToggleButton").on("click", () => {
    $centerControlPanel.hide();
    kawaiGifsModule.open();
  });

  // hide cc on outside click
  $controlCenter.on("click", function (event) {
    if (event.target === this) {
      $(this).fadeOut();
    }
  });

  $("#logout-btn").on("click", function () {
    client.ws.close();
    client._closed = true;
    client.system.request("client-logout", "POST").then(res => {
      location.reload();
    });
  });
});

const createSwipeBubble = selector => {
  const $bubble = $(selector);
  const $ghostButton = $("#swb-ghost-btn");
  const $widget = $("#swipe-bubble-widget");

  let shrinkTimer = null;
  let isActive = false;
  let widgetOpen = false;

  // Tailwind class sets
  const classes = {
    inactive: "w-8 h-20 -right-4",
    active: "w-36 h-36 right-0 shadow-xl landscape:w-1/4 landscape:h-1/2",
    holdColor: "bg-red-400/60",
    transparent: "!bg-transparent"
  };

  // ---- Utility functions ----
  const shrink = () => {
    if (widgetOpen) {
      widgetOpen = false;
      $widget.hide();
      $("#swipe-bubble-frame").remove();
    }
    $bubble
      .removeClass(
        `${classes.holdColor} ${classes.active} ${classes.transparent}`
      )
      .addClass(classes.inactive);
    isActive = false;
    widgetOpen = false;
  };

  const scheduleShrink = () => {
    clearTimeout(shrinkTimer);
    shrinkTimer = setTimeout(shrink, 2000);
  };

  const expand = () => {
    clearTimeout(shrinkTimer);
    $bubble.removeClass(classes.inactive).addClass(classes.active);
    isActive = true;
    scheduleShrink();
  };

  const forceClose = () => {
    clearTimeout(shrinkTimer);
    shrink();
  };

  // ---- Event Handlers ----

  $ghostButton.on("click", () => {
    $bubble.show();
    $ghostButton.hide();
  });

  $bubble.off("click").on("click", () => {
    if (!widgetOpen) debounce(expand());
  });

  // Click/touch outside to shrink
  $bubble.parent().on("click touchstart", e => {
    if (widgetOpen) return;
    if (isActive && !$bubble.is(e.target) && !$bubble.has(e.target).length) {
      shrink();
    }
  });

  // Blur event (optional): pointer-friendly
  const handleWindowBlur = () => {
    if (!widgetOpen) shrink();
  };

  //$bubble.on("pointerenter touchstart", () => {
  window.addEventListener("blur", handleWindowBlur);
  // })

  // creates iframe on bubble long press
  const createFrame = () => {
    // Prevent duplicates
    if ($("#swipe-bubble-widget").length) return;

    $("#swipe-bubble").append(`
      <div id="swipe-bubble-widget" class="w-full h-full relative">
        <iframe
          id="swipe-bubble-frame"
          src="/public/ui/kui/widget/bubble.html"
          class="w-full h-full rounded-lg overflow-hidden"
        ></iframe>
  
        <div id="swipe-bubble-widget-close-btn" class="absolute -top-3 -left-3">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 48 48"><g fill="none" stroke-linejoin="round" stroke-width="4"><path fill="#2f88ff" stroke="#000" d="M24 44C35.0457 44 44 35.0457 44 24C44 12.9543 35.0457 4 24 4C12.9543 4 4 12.9543 4 24C4 35.0457 12.9543 44 24 44Z"/><path stroke="#fff" stroke-linecap="round" d="M29.6567 18.3432L18.343 29.6569"/><path stroke="#fff" stroke-linecap="round" d="M18.3433 18.3432L29.657 29.6569"/></g></svg>
        </div>
      </div>
    `);

    $("#swipe-bubble-widget-close-btn").on("click", () => {
      $("#swipe-bubble").empty();
      shrink();
    });
  };

  // ---- Touch Gestures ----
  initTouchGestures(selector, {
    swipeDown: () => {
      // Soft Close App show home
      showHome();
      forceClose();
    },
    swipeUp: () => {
      // Toggle active apps
      toggleRecentApps();
      forceClose();
    },
    swipeLeft: () => {
      // close app
      closeCurrentApp();
      forceClose();
    },
    swipeRight: () => {
      $centerControlPanel.fadeIn(400);
      forceClose();
    },
    longPress: () => {
      if (isActive) {
        clearTimeout(shrinkTimer);
        createFrame();
        widgetOpen = true;
        $bubble.addClass(classes.transparent);
        $widget.fadeIn();
      } else {
        $bubble.hide();
        $ghostButton.show();
      }
    }
  });
};

//requestWakeLock();
