document.addEventListener("DOMContentLoaded", () => {
  const frame = document.getElementById("frame");
  const loadingScreen = document.getElementById("loading-screen");

  frame.addEventListener("load", () => {
    loadingScreen.style.display = "none";
  });
});