let config = null;


function renderUI(config) {
  const $container = $("#ui-container").empty();

  config.kikx.forEach(element => {
    const $wrapper = $('<div class="space-y-1 mb-4"></div>');
    const $label = $(
      `<label class="block font-medium text-gray-700 dark:text-gray-200" for="${element.id}">${element.label}</label>`
    );
    let $input;

    switch (element.type) {
      case "textarea":
        $input = $(
          `<textarea id="${element.id}" class="border rounded p-2 w-full bg-white dark:bg-gray-800 dark:text-white">${element.value}</textarea>`
        );
        break;

      case "select":
        $input = $(`<select id="${element.id}" class="border rounded p-2 w-full bg-white dark:bg-gray-800 dark:text-white"></select>`);
        element.options.forEach(opt => {
          const $opt = $(`<option value="${opt}">${opt}</option>`);
          if (opt === element.value) $opt.prop("selected", true);
          $input.append($opt);
        });

        $input.on("change", function () {
          updateConfigValue(element.id, $(this).val());
        });
        break;

      case "radio":
        $input = $(`<div class="flex gap-4" id="${element.id}"></div>`);
        element.options.forEach(opt => {
          const inputId = `${element.id}_${opt}`;
          const $radio = $(`
            <div class="flex items-center gap-2">
              <input type="radio" id="${inputId}" name="${element.id}" value="${opt}" class="form-radio text-blue-600"
                ${opt === element.value ? "checked" : ""}>
              <label for="${inputId}" class="text-gray-700 dark:text-gray-200">${opt}</label>
            </div>
          `);
          $input.append($radio);
        });

        $input.on("change", "input[type=radio]", function () {
          updateConfigValue(element.id, $(this).val());
        });
        break;

      case "checkbox":
        $input = $(`
          <div class="flex items-center gap-2">
            <input type="checkbox" id="${element.id}" class="form-checkbox text-blue-600" ${element.value ? "checked" : ""}>
            <label for="${element.id}" class="text-gray-700 dark:text-gray-200">${element.label}</label>
          </div>
        `);

        $input.find("input[type=checkbox]").on("change", function () {
          updateConfigValue(element.id, $(this).is(":checked"));
        });
        break;

      case "text":
        $input = $(
          `<input type="text" id="${element.id}" class="border rounded p-2 w-full bg-white dark:bg-gray-800 dark:text-white" value="${element.value}">`
        );
        break;

      default:
        $input = $(
          `<input type="${element.type}" id="${element.id}" class="border rounded p-2 w-full bg-white dark:bg-gray-800 dark:text-white" value="${element.value}">`
        );
    }

    // Generic input listener for non-checkbox, non-radio, non-select types
    if (!["radio", "checkbox", "select"].includes(element.type)) {
      $input.on("input change", function () {
        updateConfigValue(element.id, $(this).val());
      });
    }

    $wrapper.append($label).append($input);
    $container.append($wrapper);
  });

  updateOutput();
}


function updateConfigValue(id, newValue) {
  config.kikx = config.kikx.map(el =>
    el.id === id ? { ...el, value: newValue } : el
  );
  updateOutput();
}

function updateOutput() {
  $("#config-output").text(JSON.stringify(config, null, 2));
}

async function saveCurrentSettings() {
  if (!config) return;

  $(this).addClass("hidden");

  let settings = {};
  config.kikx.forEach(setting => {
    settings[setting["id"]] = setting["value"];
  });

  const res = await kikxApp.system.setUserSettings(settings);

  if (res.data) {
    $(this).removeClass("hidden");
  }
}

$("#save-btn").on("click", function () {
  saveCurrentSettings();
});

$(async () => {
  const res = await kikxApp.system.getUserSettings(true);

  if (res.err) {
    throw Error(res.err);
  }

  config = res.data;
  renderUI(config);

  kikxApp.run(() => {
    $("html").toggleClass("dark", kikxApp.userSettings.dark_mode);

    $("#loading-screen").fadeOut(400, function () {
      $(this).remove();
    });
  });
});

kikxApp.on("signal", signalData => {
  if (signalData.signal === "update_user_settings") {
    $("html").toggleClass("dark", signalData.data.dark_mode);

  }
  });
