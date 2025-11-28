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
