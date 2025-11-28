//
const closeSession = async sessionID => {
  const res = await kikxApp.system.request(
    "info/session/close/" + sessionID,
    "POST"
  );
  if (!res.error) $(`#${sessionID}`).remove();
};

const renderInfo = data => {
  // render sessions
  const $sessions = $("#sessions");
  data.sessions.forEach(sessionData => {
    $sessions.append(`
      <div id="${sessionData.id}" class="p-1 px-2 bg-white/20 flex justify-between gap-1">
        <h1>${sessionData.id} - ${sessionData.apps_count}</h1>
        <div onclick="closeSession('${sessionData.id}')">X</div>
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
