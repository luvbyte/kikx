let wakeLock = null;

// Request wake lock
async function requestWakeLock() {
  try {
    wakeLock = await navigator.wakeLock.request("screen");
    console.log("Wake lock is active");

    // Listen for the release event
    wakeLock.addEventListener("release", () => {
      console.log("Wake lock was released");
    });
  } catch (err) {
    console.error(`${err.name}, ${err.message}`);
  }
}

// Release wake lock
async function releaseWakeLock() {
  if (wakeLock !== null) {
    try {
      await wakeLock.release();
      wakeLock = null;
      console.log("Wake lock released manually");
    } catch (err) {
      console.error("Failed to release wake lock:", err);
    }
  }
}

// Reacquire wake lock when the page becomes visible again
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    requestWakeLock();
  }
});

// requestWakeLock();
