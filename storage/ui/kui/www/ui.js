// TODO: update this wih purifyDom
const escapeHTML = str => $("<div>").text(str).html(); // Escape potentially malicious input
const isVisible = element => {
  return $(element).is(":visible");
};

// Get references to key DOM elements
const $appsContainer = $("#apps");
const $tabsContainer = $("#app-tabs");
const $appsMenu = $("#apps-menu");
const $appsPanel = $("#apps-panel");

// notifications tabs cc
const $controlCenter = $("#control-center");
// center purple box
const $centerControlPanel = $("#center-control-panel");

let currentApp = null; // Track the currently active app
let openApps = []; // List of opened apps
let appFrames = {}; // Store iframe elements
// { iframe, name, title, icon }
let lastApp = null;

let uiSettings = {};

const closeAppsPanel = () => $appsPanel.fadeOut(300);

// Open an app in an iframe and create a tab
async function openApp(name, icon, title) {
  if (appFrames[name]) return switchApp(name); // Switch if already open

  try {
    const res = await fetch("/open-app", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: clientID, name })
    });

    const resData = await res.json();

    if (!res.ok) {
      Swal.fire({
        icon: "error",
        title: resData.detail,
        text: resData.reason
      });
    }

    const { id, url, iframe } = resData;

    // Create and configure iframe
    const $iframe = $("<iframe>", {
      "data-id": id,
      src: url,
      sandbox: iframe.sandbox,
      allowFullscreen: iframe.allowfullscreen,
      allow: iframe.allow,
      loading: iframe.loading,
      referrerPolicy: iframe.referrerpolicy,
      style: iframe.style,
      class: "app-frame w-full h-full"
    });

    // Append iframe to container
    $appsContainer.append($iframe);
    appFrames[name] = {
      iframe: $iframe[0],
      title,
      icon,
      id
    };
    openApps.push(name);

    // Create app tab

    const $tab = $(`
      <div id="tab-${escapeHTML(name)}" 
          class="app-tab snap-start min-w-[100px] min-h-[120px] relative bg-purple-400/40 border round-style shadow-lg p-4 flex flex-col items-center justify-center cursor-pointer hover:shadow-lg transition duration-200 ease-in-out">
    
        <!-- App Icon -->
        <img class="w-12 h-12 rounded-md mb-3" 
             src="${escapeHTML(icon)}" 
             alt="${escapeHTML(title)} icon" />
    
        <!-- App Title -->
        <span class="text-sm font-semibold text-center truncate w-full text-white">
          ${escapeHTML(title)}
        </span>
    
        <!-- Close Button 
          <div class="close-btn absolute top-0.5 right-0.5 text-white font-bold rounded cursor-pointer w-6 h-6">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none"><circle cx="12" cy="12" r="9" fill="currentColor" fill-opacity="0.25"/><path stroke="currentColor" stroke-linecap="round" stroke-width="1.2" d="m9 9l6 6m0-6l-6 6"/></g></svg>
          </div>
        -->
      </div>
    `);

    // ---- swipe up to close
    // ---- swipe up to close (event listeners on $tab only)
    let startY = 0;
    let isDragging = false;

    $tab.on("touchstart mousedown", e => {
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      startY = clientY;
      isDragging = true;
      $tab.css({ transition: "none" }); // Disable transition during drag
    });

    $tab.on("touchmove mousemove", e => {
      if (!isDragging) return;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const deltaY = clientY - startY;

      if (deltaY < 0) {
        $tab.css({
          transform: `translateY(${deltaY}px)`,
          opacity: 1 + deltaY / 150
        });
      }
    });

    $tab.on("touchend mouseup", e => {
      if (!isDragging) return;
      isDragging = false;

      const clientY = e.changedTouches
        ? e.changedTouches[0].clientY
        : e.clientY;
      const deltaY = clientY - startY;

      if (deltaY < -100) {
        $tab.css({
          transition: "transform 0.3s ease, opacity 0.3s ease",
          transform: "translateY(-100%)",
          opacity: 0
        });

        setTimeout(() => closeApp(name), 300);
      } else {
        $tab.css({
          transition: "transform 0.3s ease, opacity 0.3s ease",
          transform: "translateY(0)",
          opacity: 1
        });
      }
    });

    // Tab click switches app
    $tab.on("click", () => switchApp(name));

    // Close button
    $tab.find(".close-btn").on("click", event => {
      event.stopPropagation();
      closeApp(name);
    });

    // Append tab and switch to new app
    $tabsContainer.append($tab);

    switchApp(name);
  } catch (error) {
    console.error(`Failed to open app ${name}:`, error);
  }
}

async function closeApp(name) {
  if (!appFrames[name]) return;

  try {
    const appID = $(appFrames[name].iframe).data("id");
    const response = await fetch("/close-app", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app_id: appID, client_id: clientID })
    });

    if (!response.ok) throw new Error(`Failed to close app ${name}`);

    // Remove iframe
    $(appFrames[name].iframe).remove();
    delete appFrames[name];

    // Remove tab safely
    const $tab = $(`[id="tab-${name}"]`);
    if ($tab.length) {
      $tab.off("click");
      $tab.find(".close-btn").off("click");
      $tab.remove();
    }

    // Update open apps list
    openApps = openApps.filter(app => app !== name);

    // If its active app then show home
    if (currentApp === name) {
      switchApp(null);
    }

    if (openApps.length === 0) {
      closeAppsPanel();
    }
  } catch (error) {
    console.error(`Failed to close app ${name}:`, error);
  }
}
// Switch to a specific app
function switchApp(name) {
  $(".app-frame").addClass("hidden"); // Hide all iframes
  $(".app-tab").removeClass("!bg-pink-400/90"); // Remove active tab styling

  if (appFrames[name]) $(appFrames[name].iframe).removeClass("hidden");

  // Select tab safely (Escape special characters)
  const $tab = $(`[id="tab-${name}"]`);
  if ($tab.length) {
    $tab.addClass("!bg-pink-400/90"); // Highlight active tab
  }

  currentApp = name;

  // setting icon in heade
  if (currentApp) {
    let appFrame = appFrames[name];

    $("#header-app-name").text(appFrame.title);
    let iconDiv = $("<img>", {
      src: appFrame.icon,
      class: "w-full h-full"
    });
    $("#header-app-icon").html(iconDiv);
  } else {
    $("#header-app-icon").empty();
    $("#header-app-name").empty();
  }
}

// Render app launcher grid
function renderLauncherGrid(appList) {
  const $grid = $("#launcherGrid").empty();

  appList.forEach(({ name, icon, title }) => {
    const $button = $(`
      <button class="flex flex-col items-center transition">
        <div class="w-16 h-16 flex justify-center items-center rounded-lg rounded-tl-sm rounded-br-sm overflow-hidden shadow-lg">
          <img src="${escapeHTML(icon)}" class="w-full h-full" />
        </div>
        <span class="text-md truncate text-white">${escapeHTML(title)}</span>
      </button>
    `);
    $button.on("click", () => openApp(name, icon, title));
    $grid.append($button);
  });
}

// Navigation button event listeners
const toggleRecentApps = () => {
  $appsPanel.fadeToggle(300);
};
const closeCurrentApp = () => {
  closeApp(currentApp);
};
const showHome = () => {
  switchApp(null);
};

$("#nav-panel-close").on("click", () => closeAppsPanel());

$appsPanel.on("click", function (event) {
  if (event.target === $("#swipe-touch-cancel").get(0)) {
    return;
  }
  closeAppsPanel();
});

const toggleNotificationsPanel = () => {
  $("#control-center").fadeToggle();
};

// loading and rendering apps
const loadApps = async payload => {
  try {
    const res = await fetch(`/api/apps/list`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: payload.client_id })
    });
    if (res.ok) {
      const apps = await res.json();
      renderLauncherGrid(apps);
    }
  } catch (error) {
    console.error("Failed to fetch app list:", error);
  }
};

// ------------ notifications
const notifyApp = {
  notifyQueue: [], // waiting list
  isProcessing: false,
  animationAbortController: null,
  silentMode: false,

  totalCount: 0,

  // updates.ui
  updateCount() {
    const $badge = $("#notify-count");

    $badge
      .text(this.totalCount)
      .toggleClass("hidden", this.totalCount === 0)
      .toggleClass("opacity-50", this.totalCount === 0)
      .toggleClass("scale-95", this.totalCount === 0)
      .toggleClass("bg-white/20", this.totalCount === 0)
      .toggleClass("bg-white/40", this.totalCount > 0);
  },

  decreaseCount() {
    this.totalCount = Math.max(0, this.totalCount - 1);
    this.updateCount();
  },

  incrementCount() {
    this.totalCount++;
    this.updateCount();
  },

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  clearQueue() {
    this.notifyQueue = [];

    if (this.animationAbortController) {
      this.animationAbortController.abort();
    }

    this.isProcessing = false;

    $("#notify-animation")
      .stop(true, true)
      .fadeOut(200, function () {
        $(this).empty();
        $("#notify-app-title").hide();
        $("#clock-text").fadeIn(300);
        $("#status-bar-name").fadeIn(300);
      });
  },

  // Add a new payload to queue
  enqueue(payload) {
    if (this.silentMode) {
      $("#notify-count")
        .text(this.totalCount)
        .removeClass("hidden")
        .addClass("bg-white/40 scale-100 opacity-100");
    } else {
      this.notifyQueue.push(payload);
      this.processQueue();
    }
  },

  // Sequentially animate each payload in queue
  async processQueue() {
    if (this.isProcessing) return;
    this.isProcessing = true;

    while (this.notifyQueue.length > 0) {
      const payload = this.notifyQueue.shift();
      await this.animate(payload);
    }

    this.isProcessing = false;
  },

  async animate(payload) {
    // Abort any current animation
    if (this.animationAbortController) {
      this.animationAbortController.abort();
    }

    this.animationAbortController = new AbortController();
    const { signal } = this.animationAbortController;

    const $el = $("#notify-animation");
    const $clock = $("#clock-text");
    const $name = $("#status-bar-name");

    // setting app title
    const $notifyTitle = $("#notify-app-title");
    $notifyTitle.text(payload.title);
    $notifyTitle.show();

    let frames = payload.extra.frames;
    let delay = 300;

    // if frames found animate it else show msg
    if (!Array.isArray(frames) || frames.length <= 0) {
      frames = [payload.msg];
      delay = 3000;
    } else {
      delay =
        typeof payload?.extra?.delay === "number" &&
        payload.extra.delay >= 0 &&
        payload.extra.delay <= 1000
          ? payload.extra.delay
          : 300;
    }

    $clock.stop(true, true).fadeOut(150);
    $name.stop(true, true).fadeOut(150);

    try {
      $el.stop(true, true).fadeIn(150);

      for (const frame of frames) {
        if (signal.aborted) return;

        await new Promise(resolve => {
          $el.fadeOut(100, () => {
            $el.text(frame).fadeIn(200, resolve);
          });
        });

        await this.sleep(delay);
      }
    } finally {
      if (!signal.aborted) {
        await new Promise(resolve => {
          $el.fadeOut(200, () => {
            $el.empty();
            $clock.fadeIn(300);
            $name.fadeIn(400);

            $notifyTitle.hide();
            resolve();
          });
        });
      }
    }
  },

  //
  notify(payload) {
    // Append message box to panel
    $("#cc-notifications-panel")
      .append(notifyApp._createNotifyDiv(payload))
      .fadeIn(300);

    notifyApp.incrementCount();
    // adding to queue
    notifyApp.enqueue(payload);

    soundModule.notify();
  },

  _createNotifyDiv(payload) {
    // Tailwind color by type
    let color = "bg-white";
    if (payload.type === "error") color = "bg-red-200 text-black";
    else if (payload.type === "success") color = "bg-green-200 text-white";
    else if (payload.type === "warning") color = "bg-yellow-200 text-white";

    const notifyDiv = $("<div>", {
      class: `${color} rounded-sm px-3 py-2 text-sm w-full max-w-sm cursor-pointer transition-all duration-300`,
      css: {
        willChange: "transform, opacity"
      },

      click: function () {
        if (openApps.includes(payload.name)) {
          switchApp(payload.name);
          $("#control-center").hide();
        }
        $(this).remove();
        notifyApp.decreaseCount();
      }
    });

    // Title and message
    const titleEl = $("<div>", {
      class: "font-semibold mb-0.5 text-xs",
      text: payload.title
    });
    const messageEl = $("<div>", {
      text: payload.msg
    });
    notifyDiv.append(titleEl, messageEl);

    let startX = 0;
    let isSwiping = false;

    notifyDiv.on("touchstart", function (e) {
      startX = e.originalEvent.touches[0].clientX;
      isSwiping = true;
    });

    notifyDiv.on("touchmove", function (e) {
      if (!isSwiping) return;

      const currentX = e.originalEvent.touches[0].clientX;
      const diffX = currentX - startX;

      if (diffX > 0) {
        // Max distance after which it becomes fully transparent
        const maxSwipe = 100;
        const limitedDiff = Math.min(diffX, maxSwipe);
        const opacity = 1 - limitedDiff / maxSwipe;

        $(this).css({
          transform: `translateX(${limitedDiff}px)`,
          opacity: opacity
        });
      }
    });

    notifyDiv.on("touchend", function (e) {
      const endX = e.originalEvent.changedTouches[0].clientX;
      const diffX = endX - startX;

      if (diffX > 100) {
        // Animate out
        $(this).css({
          transition: "transform 0.2s ease-out, opacity 0.2s ease-out",
          transform: "translateX(400px)",
          opacity: 0
        });

        const self = this;

        setTimeout(() => {
          $(self).remove();

          // Decrease count
          notifyApp.decreaseCount();
        }, 200);
      } else {
        // Snap back
        $(this).css({
          transition: "transform 0.2s ease-out, opacity 0.2s ease-out",
          transform: "translateX(0)",
          opacity: 1
        });
      }

      isSwiping = false;
    });

    return notifyDiv;
  }
};

$("#status-bar").on("dblclick", () => {
  notifyApp.clearQueue();

  $("#status-bar")
    .addClass("bg-red-600/80")
    .removeClass("bg-gradient-to-r")
    .delay(250)
    .queue(function (next) {
      $(this).removeClass("bg-red-600/80").addClass("bg-gradient-to-r");
      next();
    });
});

$("#clear-notify-btn").on("click", function () {
  // Clear notification panelclearNotificationsPanel

  $("#cc-notifications-panel").fadeOut(300, function () {
    $(this).empty(); // clear after fadeOut completes
  });
  $("#notify-count").addClass("hidden");

  // Also clear animation queue just in case
  notifyApp.totalCount = 0;
  notifyApp.clearQueue();
});

// this will update user data
const updateUserData = userData => {
  setTimeout(() => {
    $("#user-name-text").text(userData.username).slideDown(600);
  }, 800);
};

// button highlight for
function updateToggleHighlight(option, element) {
  let $el = $(element);

  if (option) {
    // mode ON — green highlight
    $el
      .removeClass("bg-transparent text-black")
      .addClass("bg-white/60 shadow-md");
  } else {
    // mode OFF — normal look
    $el
      .removeClass("bg-white/60 shadow-md")
      .addClass("bg-transparent text-black");
  }
}

// toggle buttons in cc
function toggleNotifyMode(option) {
  // If option is explicitly passed, use it; otherwise toggle
  const silent = typeof option === "boolean" ? option : !notifyApp.silentMode;

  // Set the value
  notifyApp.silentMode = silent;

  // Update the toggle button visually
  updateToggleHighlight(!silent, $("#notify-toggle-btn"));
}

// toggle sound
function toggleSoundMode(option) {
  const silent = typeof option === "boolean" ? option : !soundModule.silent;
  // Update the toggle button visually
  soundModule.silent = silent;
  updateToggleHighlight(!silent, $("#sound-toggle-btn"));
}

// initialize
const updateControlPanel = userSettings => {
  toggleNotifyMode(userSettings.sound.silent);
  toggleSoundMode(userSettings.sound.silent);
};
