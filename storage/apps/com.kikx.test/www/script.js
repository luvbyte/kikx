function notify(tp, delay) {
  kikxApp.system.notify({
    msg: "A message",
    type: tp,
    displayEvenActive: true,
    extra: {
      delay: 250,
      frames: ["(⌐■_■)", "( •_•)>⌐■-■", "(⌐■_■)"]
    },
    delay: delay
  });
}

function clearConsole() {
  $("#terminal").empty();
}
async function runCommand() {
  let inputEl = $("#cmd-input");
  let inputText = inputEl.val();
  if (inputText.length <= 0) {
    return;
  }
  inputEl.val("");
  let terminalEl = $("#terminal");
  runTask(inputText, data => {
    if (data.status === "output") {
      terminalEl.append(data.output);
    }
  });
}

kikxApp.run(() => {
  console.log("started");
});
