async function main() {
  $("#loading-screen").fadeOut();

  // $("#main").text("...Under development...");
  // $("#main").text(location.pathname.split("/")[2]);

  $("#toast").on("click", function () {
    kikxApp.system.alert({
      msg: "If you’re reading this… I just want to wish you the best of luck today 🍀✨ You’ve got everything it takes to win — the talent, the confidence, and that unstoppable energy 💪🔥 Go out there and shine like you always do 🌟 I’ll be cheering for you the whole way 💚👏"
    });
  });
  $("#toast-success").on("click", function () {
    kikxApp.system.alert({
      msg: "If you’re reading this… I just want to wish you the best of luck today 🍀✨ You’ve got everything it takes to win — the talent, the confidence, and that unstoppable energy 💪🔥 Go out there and shine like you always do 🌟 I’ll be cheering for you the whole way 💚👏",
      type: "success"
    });
  });
  $("#toast-warning").on("click", function () {
    kikxApp.system.alert({
      msg: "If you’re reading this… I just want to wish you the best of luck today 🍀✨ You’ve got everything it takes to win — the talent, the confidence, and that unstoppable energy 💪🔥 Go out there and shine like you always do 🌟 I’ll be cheering for you the whole way 💚👏",
      type: "warning"
    });
  });
  $("#toast-error").on("click", function () {
    kikxApp.system.alert({
      msg: "If you’re reading this… I just want to wish you the best of luck today 🍀✨ You’ve got everything it takes to win — the talent, the confidence, and that unstoppable energy 💪🔥 Go out there and shine like you always do 🌟 I’ll be cheering for you the whole way 💚👏",
      type: "error"
    });
  });
}

$(main);
