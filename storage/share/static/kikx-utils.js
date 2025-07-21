// Utility: Debounce function
function debounce(func, delay) {
  let timer;
  return function () {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, arguments), delay);
  };
}

// return value or return default


const getValue = (value, options = {}) => {
  const {
    default: defaultValue,
    type,               // e.g., "string", "number", "object", "boolean", "array"
    validate,           // custom validation function: (value) => boolean
    allowed,            // list of allowed values: ["foo", "bar"]
    required = false    // whether null/undefined should fail
  } = options;

  try {
    // Required check
    if (required && (value === undefined || value === null)) {
      return defaultValue;
    }

    // Skip further checks if value is nullish
    if (value === undefined || value === null) {
      return defaultValue;
    }

    // Type check
    if (type) {
      if (type === "array" && !Array.isArray(value)) {
        return defaultValue;
      }
      if (type !== "array" && typeof value !== type) {
        return defaultValue;
      }
    }

    // Allowed values check
    if (allowed && !allowed.includes(value)) {
      return defaultValue;
    }

    // Custom validation function
    if (validate && typeof validate === "function" && !validate(value)) {
      return defaultValue;
    }

    // Passed all checks
    return value;

  } catch {
    return defaultValue;
  }
};

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
