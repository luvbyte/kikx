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

function initTouchGestures(selector, callbacks, options = {}) {
  const {
    threshold = 10,
    edgeThreshold = 30,
    tapMaxDelay = 300,
    longPressDelay = 500,
    pinchThreshold = 15 // distance change to trigger pinch
  } = options;

  let startX, startY;
  let lastTapTime = 0;
  let longPressTimeout = null;
  let longPressTriggered = false;
  let isTwoFinger = false;

  let pinchStartDist = 0;
  let twoFingerStart = [];

  function getDistance(t1, t2) {
    return Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
  }

  $(selector).on("touchstart", function (e) {
    longPressTriggered = false;
    isTwoFinger = e.touches.length === 2;

    if (isTwoFinger) {
      const [t1, t2] = e.touches;
      pinchStartDist = getDistance(t1, t2);
      twoFingerStart = [
        { x: t1.clientX, y: t1.clientY },
        { x: t2.clientX, y: t2.clientY }
      ];
      startX = (t1.clientX + t2.clientX) / 2;
      startY = (t1.clientY + t2.clientY) / 2;
    } else if (e.touches.length === 1) {
      const touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;

      if (typeof callbacks.longPress === "function") {
        longPressTimeout = setTimeout(() => {
          longPressTriggered = true;
          callbacks.longPress(e);
        }, longPressDelay);
      }

      const currentTime = new Date().getTime();
      if (currentTime - lastTapTime < tapMaxDelay) {
        if (typeof callbacks.doubleTap === "function") {
          callbacks.doubleTap(e);
        }
        lastTapTime = 0;
      } else {
        lastTapTime = currentTime;
      }
    }

    if (typeof callbacks.touch === "function") {
      callbacks.touch(e);
    }
  });

  $(selector).on("touchmove", function (e) {
    if (longPressTimeout && e.touches.length === 1) {
      const touch = e.touches[0];
      const deltaX = touch.clientX - startX;
      const deltaY = touch.clientY - startY;
      if (Math.abs(deltaX) > 10 || Math.abs(deltaY) > 10) {
        clearTimeout(longPressTimeout);
        longPressTimeout = null;
      }
    }
  });

  $(selector).on("touchend", function (e) {
    if (longPressTimeout) {
      clearTimeout(longPressTimeout);
      longPressTimeout = null;
    }

    if (longPressTriggered) {
      lastTapTime = 0;
      return;
    }

    if (isTwoFinger && e.touches.length < 2) {
      const changed = e.changedTouches;
      if (changed.length < 2) return;

      const [t1, t2] = changed;
      const pinchEndDist = getDistance(t1, t2);

      const pinchDelta = pinchEndDist - pinchStartDist;

      if (Math.abs(pinchDelta) > pinchThreshold) {
        if (pinchDelta > 0 && typeof callbacks.pinchOut === "function") {
          callbacks.pinchOut();
        } else if (pinchDelta < 0 && typeof callbacks.pinchIn === "function") {
          callbacks.pinchIn();
        }
      } else {
        // Check for two-finger swipe
        const delta1X = t1.clientX - twoFingerStart[0].x;
        const delta1Y = t1.clientY - twoFingerStart[0].y;
        const delta2X = t2.clientX - twoFingerStart[1].x;
        const delta2Y = t2.clientY - twoFingerStart[1].y;

        const avgDeltaX = (delta1X + delta2X) / 2;
        const avgDeltaY = (delta1Y + delta2Y) / 2;

        const absX = Math.abs(avgDeltaX);
        const absY = Math.abs(avgDeltaY);

        if (absX > absY) {
          if (
            avgDeltaX > threshold &&
            typeof callbacks.twoFingerSwipeRight === "function"
          ) {
            callbacks.twoFingerSwipeRight();
          } else if (
            avgDeltaX < -threshold &&
            typeof callbacks.twoFingerSwipeLeft === "function"
          ) {
            callbacks.twoFingerSwipeLeft();
          }
        } else {
          if (
            avgDeltaY > threshold &&
            typeof callbacks.twoFingerSwipeDown === "function"
          ) {
            callbacks.twoFingerSwipeDown();
          } else if (
            avgDeltaY < -threshold &&
            typeof callbacks.twoFingerSwipeUp === "function"
          ) {
            callbacks.twoFingerSwipeUp();
          }
        }
      }
      return;
    }

    // Single-finger swipe
    if (e.changedTouches.length === 0) return;
    const touch = e.changedTouches[0];
    const endX = touch.clientX;
    const endY = touch.clientY;

    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    const edgeInfo = {
      fromLeftEdge: startX <= edgeThreshold,
      fromRightEdge: window.innerWidth - startX <= edgeThreshold,
      fromTopEdge: startY <= edgeThreshold,
      fromBottomEdge: window.innerHeight - startY <= edgeThreshold,
      isTwoFinger: false
    };

    if (absDeltaY > absDeltaX) {
      if (deltaY < -threshold && callbacks.swipeUp) {
        callbacks.swipeUp(edgeInfo);
      } else if (deltaY > threshold && callbacks.swipeDown) {
        callbacks.swipeDown(edgeInfo);
      }
    } else {
      if (deltaX < -threshold && callbacks.swipeLeft) {
        callbacks.swipeLeft(edgeInfo);
      } else if (deltaX > threshold && callbacks.swipeRight) {
        callbacks.swipeRight(edgeInfo);
      }
    }
  });
}

function createTouchSwiper__(selector, callbacks, options = {}) {
  const {
    threshold = 10,
    edgeThreshold = 30,
    tapMaxDelay = 300,
    longPressDelay = 500
  } = options;

  let startX,
    startY,
    isTwoFinger = false,
    lastTapTime = 0,
    longPressTimeout = null,
    longPressTriggered = false;

  $(selector).on("touchstart", function (e) {
    isTwoFinger = e.touches.length === 2;
    longPressTriggered = false;

    if (isTwoFinger) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      startX = (touch1.clientX + touch2.clientX) / 2;
      startY = (touch1.clientY + touch2.clientY) / 2;
    } else if (e.touches.length === 1) {
      const touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;

      // Start long press timer
      if (typeof callbacks.longPress === "function") {
        longPressTimeout = setTimeout(() => {
          longPressTriggered = true;
          callbacks.longPress(e);
        }, longPressDelay);
      }

      // Check for double tap
      const currentTime = new Date().getTime();
      if (currentTime - lastTapTime < tapMaxDelay) {
        if (typeof callbacks.doubleTap === "function") {
          callbacks.doubleTap(e);
        }
        lastTapTime = 0;
      } else {
        lastTapTime = currentTime;
      }
    }

    if (typeof callbacks.touch === "function") {
      callbacks.touch(e);
    }
  });

  $(selector).on("touchend", function (e) {
    if (longPressTimeout) {
      clearTimeout(longPressTimeout);
      longPressTimeout = null;
    }

    // Prevent swipe if long press was triggered
    if (longPressTriggered) {
      return;
    }

    if (isTwoFinger && e.touches.length > 0) return;

    const touch = e.changedTouches[0];
    const endX = touch.clientX;
    const endY = touch.clientY;

    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    const isFromLeftEdge = startX <= edgeThreshold;
    const isFromRightEdge = window.innerWidth - startX <= edgeThreshold;
    const isFromTopEdge = startY <= edgeThreshold;
    const isFromBottomEdge = window.innerHeight - startY <= edgeThreshold;

    const edgeInfo = {
      fromLeftEdge: isFromLeftEdge,
      fromRightEdge: isFromRightEdge,
      fromTopEdge: isFromTopEdge,
      fromBottomEdge: isFromBottomEdge,
      isTwoFinger
    };

    if (absDeltaY > absDeltaX) {
      if (deltaY < -threshold && callbacks.swipeUp) {
        callbacks.swipeUp(edgeInfo);
      } else if (deltaY > threshold && callbacks.swipeDown) {
        callbacks.swipeDown(edgeInfo);
      }
    } else {
      if (deltaX < -threshold && callbacks.swipeLeft) {
        callbacks.swipeLeft(edgeInfo);
      } else if (deltaX > threshold && callbacks.swipeRight) {
        callbacks.swipeRight(edgeInfo);
      }
    }
  });
}

function createTouchSwiper_(selector, callbacks, options = {}) {
  const {
    threshold = 10,
    edgeThreshold = 30,
    tapMaxDelay = 300,
    longPressDelay = 500
  } = options;

  let startX,
    startY,
    isTwoFinger = false,
    lastTapTime = 0,
    longPressTimeout = null;

  $(selector).on("touchstart", function (e) {
    isTwoFinger = e.touches.length === 2;

    if (isTwoFinger) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      startX = (touch1.clientX + touch2.clientX) / 2;
      startY = (touch1.clientY + touch2.clientY) / 2;
    } else if (e.touches.length === 1) {
      const touch = e.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;

      // Start long press timer
      if (typeof callbacks.longPress === "function") {
        longPressTimeout = setTimeout(() => {
          callbacks.longPress(e);
          longPressTimeout = null;
        }, longPressDelay);
      }

      // Check for double tap
      const currentTime = new Date().getTime();
      if (currentTime - lastTapTime < tapMaxDelay) {
        if (typeof callbacks.doubleTap === "function") {
          callbacks.doubleTap(e);
        }
        lastTapTime = 0;
      } else {
        lastTapTime = currentTime;
      }
    }

    if (typeof callbacks.touch === "function") {
      callbacks.touch(e);
    }
  });

  $(selector).on("touchend", function (e) {
    if (longPressTimeout) {
      clearTimeout(longPressTimeout);
      longPressTimeout = null;
    }

    if (isTwoFinger && e.touches.length > 0) return;

    const touch = e.changedTouches[0];
    const endX = touch.clientX;
    const endY = touch.clientY;

    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);

    const isFromLeftEdge = startX <= edgeThreshold;
    const isFromRightEdge = window.innerWidth - startX <= edgeThreshold;
    const isFromTopEdge = startY <= edgeThreshold;
    const isFromBottomEdge = window.innerHeight - startY <= edgeThreshold;

    const edgeInfo = {
      fromLeftEdge: isFromLeftEdge,
      fromRightEdge: isFromRightEdge,
      fromTopEdge: isFromTopEdge,
      fromBottomEdge: isFromBottomEdge,
      isTwoFinger
    };

    if (absDeltaY > absDeltaX) {
      if (deltaY < -threshold && callbacks.swipeUp) {
        callbacks.swipeUp(edgeInfo);
      } else if (deltaY > threshold && callbacks.swipeDown) {
        callbacks.swipeDown(edgeInfo);
      }
    } else {
      if (deltaX < -threshold && callbacks.swipeLeft) {
        callbacks.swipeLeft(edgeInfo);
      } else if (deltaX > threshold && callbacks.swipeRight) {
        callbacks.swipeRight(edgeInfo);
      }
    }
  });
}
