let userSettings = {};
$(document).ready(async function () {
  $("#save-btn").on("click", async function () {
    // Deep copy and update the object
    userSettings = getUpdatedSettings(userSettings);

    // Optional: Save to localStorage or send to server here
    $(this).hide();
    let res = await kikxApp.system.setUserSettings(userSettings);
    if (res.data) $(this).show();
  });

  // Optional enum for dropdowns
  //  const settingOptions = {
  //"user.theme": ["light", "dark"],
  // "user.language": ["en", "es", "fr"]
  // };

  // Recursively render settings
  function renderSettings(settings, parentKey = "") {
    const container = $("<div class='space-y-2'></div>");

    for (const key in settings) {
      const fullKey = parentKey ? `${parentKey}.${key}` : key;
      const value = settings[key];

      if (typeof value === "boolean") {
        container.append(renderCheckbox(fullKey, key, value));
      } else if (typeof value === "string" || typeof value === "number") {
        const options = settingOptions[fullKey];
        if (options) {
          container.append(renderSelect(fullKey, key, value, options));
        } else {
          container.append(renderTextInput(fullKey, key, value));
        }
      } else if (typeof value === "object" && value !== null) {
        const group = $("<fieldset class='border p-2 rounded-md'>");
        group.append(
          `<legend class="text-sm font-semibold capitalize">${key}</legend>`
        );
        group.append(renderSettings(value, fullKey));
        container.append(group);
      }
    }

    return container;
  }

  function renderCheckbox(id, label, value) {
    const safeId = id.replace(/\./g, "-");
    return `
      <div class="flex items-center justify-between p-3 border rounded bg-white dark:bg-slate-700">
        <label for="${safeId}" class="capitalize">${label}</label>
        <input type="checkbox" id="${safeId}" data-key="${id}" ${
          value ? "checked" : ""
        }>
      </div>
    `;
  }

  function renderSelect(id, label, value, options) {
    const safeId = id.replace(/\./g, "-");
    const optionsHTML = options
      .map(
        opt =>
          `<option value="${opt}" ${
            opt === value ? "selected" : ""
          }>${opt}</option>`
      )
      .join("");

    return `
      <div class="p-3 border rounded bg-white dark:bg-slate-700">
        <label for="${safeId}" class="block mb-1 capitalize">${label}</label>
        <select id="${safeId}" data-key="${id}" class="w-full p-1 border rounded">
          ${optionsHTML}
        </select>
      </div>
    `;
  }

  function renderTextInput(id, label, value) {
    const safeId = id.replace(/\./g, "-");
    return `
      <div class="p-3 border rounded bg-white dark:bg-slate-700">
        <label for="${safeId}" class="block mb-1 capitalize">${label}</label>
        <input type="text" id="${safeId}" data-key="${id}" value="${value}" class="w-full p-1 border rounded" />
      </div>
    `;
  }

  function getUpdatedSettings(original) {
    const updated = JSON.parse(JSON.stringify(original));

    $("[data-key]").each(function () {
      const key = $(this).data("key");
      const keys = key.split(".");
      let obj = updated;

      for (let i = 0; i < keys.length - 1; i++) {
        obj = obj[keys[i]];
      }

      const lastKey = keys[keys.length - 1];
      if ($(this).is(":checkbox")) {
        obj[lastKey] = $(this).is(":checked");
      } else {
        obj[lastKey] = $(this).val();
      }
    });

    return updated;
  }

  kikxApp.run(() => {
    // Initial render
    userSettings = kikxApp.userSettings;
    const rendered = renderSettings(userSettings);
    $("#ui-container").append(rendered);

    $("html").toggleClass("dark", userSettings.display.dark);

    $("#loading-screen").fadeOut(400, function () {
      $(this).remove();
    });
  });

  // Hide loading screen
  //$("#loading-screen").fadeOut();
});

kikxApp.on("signal", signalData => {
  if (signalData.signal === "update_user_settings") {
    $("html").toggleClass("dark", signalData.data.display.dark);
  }
});
