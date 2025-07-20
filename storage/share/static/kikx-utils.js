// Utility: Debounce function
function debounce(func, delay) {
  let timer;
  return function () {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, arguments), delay);
  };
}

function isAndroidWebView() {
  const ua = navigator.userAgent || "";
  return (
    /\bwv\b/.test(ua) ||
    (/Version\/[\d.]+/.test(ua) && /Chrome\/[\d.]+/.test(ua))
  );
}

function detectOrientation(portraitCallback, landscapeCallback) {
  const orientationQuery = window.matchMedia("(orientation: landscape)");
  // modern orientation detection
  orientationQuery.addEventListener("change", e => {
    e.matches ? landscapeCallback() : portraitCallback();
  });
}

// Works only in fullscreen on some mobile browsers
async function lockOrientation(orient) {
  await document.documentElement.requestFullscreen();
  screen.orientation.lock(orient); // or "portrait"
}

// toggle full scree on browser
function toggleBrowserFullScreen() {
  const doc = window.document;
  const docEl = doc.documentElement;

  const requestFullScreen =
    docEl.requestFullscreen ||
    docEl.mozRequestFullScreen ||
    docEl.webkitRequestFullscreen ||
    docEl.msRequestFullscreen;
  const cancelFullScreen =
    doc.exitFullscreen ||
    doc.mozCancelFullScreen ||
    doc.webkitExitFullscreen ||
    doc.msExitFullscreen;

  if (
    !doc.fullscreenElement &&
    !doc.mozFullScreenElement &&
    !doc.webkitFullscreenElement &&
    !doc.msFullscreenElement
  ) {
    requestFullScreen.call(docEl);
  } else {
    cancelFullScreen.call(doc);
  }
}
