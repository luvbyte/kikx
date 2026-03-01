//
const kikxApp = new kikxSdk.KikxApp();

const closeSession = async sessionID => {
  const res = await kikxApp.system.request(
    "info/session/close/" + sessionID,
    "POST"
  );

  if (!res.error) $(`#${sessionID}`).remove();
};

const renderInfo = data => {
  const $sessions = $("#sessions");
  $sessions.empty();

  data.sessions.forEach(sessionData => {
    $sessions.append(`
      <div
        id="${sessionData.id}"
        class="flex items-center justify-between gap-3 p-3 mb-2
               rounded-lg bg-white/30 
               shadow-sm
               border border-white/20"
      >
        <div class="flex flex-col">
          <span class="font-semibold text-sm text-white">
            Session ${sessionData.id}
          </span>
          <span class="text-xs text-white/70">
            Apps: ${sessionData.apps_count}
          </span>
        </div>

        <button
          onclick="closeSession('${sessionData.id}')"
          class="w-7 h-7 flex items-center justify-center
                 rounded-full bg-red-500/80 text-white font-bold"
          title="Close session"
        >
          ✕
        </button>
      </div>
    `);
  });
};

$("#loading-screen").hide();
//
const fetchInfo = async () => {
  const info = await kikxApp.system.info();
  if (info.data) {
    renderInfo(info.data);
  }
};

$(async () => {
  // fetch info
  await fetchInfo();
});
