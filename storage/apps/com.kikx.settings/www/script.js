let config = null;

function renderUI(config) {
  const $container = $("#ui-container").empty();

  config.kikx.forEach(element => {
    const $wrapper = $('<div class="space-y-1 mb-4"></div>');
    const $label = $(
      `<label class="block font-medium" for="${element.id}">${element.label}</label>`
    );
    let $input;

    switch (element.type) {
      case "textarea":
        $input = $(
          `<textarea id="${element.id}" class="border rounded p-2 w-full">${element.value}</textarea>`
        );
        break;

      case "select":
        $input = $(
          `<select id="${element.id}" class="rounded p-2 w-full"></select>`
        );
        element.options.forEach(opt => {
          const $opt = $(`<option value="${opt}">${opt}</option>`);
          if (opt === element.value) $opt.prop("selected", true);
          $input.append($opt);
        });

        // Apply jQuery UI selectmenu
        setTimeout(() => {
          $input.selectmenu({
            change: function (event, ui) {
              updateConfigValue(element.id, ui.item.value);
            }
          });
        }, 0);
        break;

      case "radio":
        $input = $('<div class="flex gap-4" id="' + element.id + '"></div>');
        element.options.forEach(opt => {
          const inputId = `${element.id}_${opt}`;
          const $radio = $(`
            <input type="radio" id="${inputId}" name="${
              element.id
            }" value="${opt}" ${opt === element.value ? "checked" : ""}>
            <label for="${inputId}">${opt}</label>
          `);
          $input.append($radio);
        });

        // Apply jQuery UI checkboxradio
        setTimeout(() => {
          $input.find("input[type=radio]").checkboxradio();
        }, 0);

        $input.on("change", "input[type=radio]", function () {
          updateConfigValue(element.id, $(this).val());
        });
        break;

      case "checkbox":
        $input = $(`
          <input type="checkbox" id="${element.id}" ${
            element.value ? "checked" : ""
          }>
          <label for="${element.id}">${element.label}</label>
        `);

        // Wrap in div for spacing
        $input = $(`<div></div>`).append($input);

        // Apply jQuery UI checkboxradio
        setTimeout(() => {
          $input.find("input[type=checkbox]").checkboxradio();
        }, 0);
        break;

      case "text":
        if (element.ui === "datepicker") {
          $input = $(
            `<input type="text" id="${element.id}" class="border rounded p-2 w-full">`
          ).datepicker({ dateFormat: "yy-mm-dd" });
          $input.val(element.value);
        } else {
          $input = $(
            `<input type="text" id="${element.id}" class="border rounded p-2 w-full" value="${element.value}">`
          );
        }
        break;

      default:
        $input = $(
          `<input type="${element.type}" id="${element.id}" class="border rounded p-2 w-full" value="${element.value}">`
        );
    }

    // Generic event handling for non-radio inputs
    if (!["radio", "select"].includes(element.type)) {
      const $actualInput =
        element.type === "checkbox"
          ? $input.find("input[type=checkbox]")
          : $input;

      $actualInput.on("input change", function () {
        const val =
          element.type === "checkbox" ? $(this).is(":checked") : $(this).val();
        updateConfigValue(element.id, val);
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
