$(document).ready(function () {
  const notif = $("#notifications");
  const control = $("#controlCenter");
  let startY = 0,
    endY = 0;

  // GSAP defaults
  gsap.defaults({ duration: 0.5, ease: "power3.out" });

  // Open/close notification
  $("#closeNotif").click(() => {
    gsap.to(notif, { top: "-100%" });
  });

  // Open/close control center
  $("#closeControl").click(() => {
    gsap.to(control, { bottom: "-100%" });
  });

  // Swipe gesture detection
  $("#phone").on("touchstart", e => {
    startY = e.touches[0].clientY;
  });

  $("#phone").on("touchend", e => {
    endY = e.changedTouches[0].clientY;
    const diff = endY - startY;

    if (diff > 100) {
      // Swipe down -> Notifications
      gsap.to(notif, { top: 0 });
      gsap.to(control, { bottom: "-100%" });
    } else if (diff < -100) {
      // Swipe up -> Control Center
      gsap.to(control, { bottom: 0 });
      gsap.to(notif, { top: "-100%" });
    }
  });

  // Tap on dock center icon opens apps launcher
  $(".dock-center").click(() => {
    gsap.to("#appLauncher", { scale: 1, opacity: 1 });
  });
});
