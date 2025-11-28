function generateUUID() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r =
      (crypto.getRandomValues(new Uint8Array(1))[0] & 15) >>
      (c === "x" ? 0 : 4);
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const ADB = {
  // Returns devices list in object
  devices: async () => {
    const result = await runTaskSync("devices");

    // Split output by lines and clean up
    const lines = result.trim().split("\n");

    // Skip the first line ("List of devices attached")
    const devices = lines
      .slice(1)
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .map(line => {
        const [id, status] = line.split(/\s+/);
        return { id, status };
      });

    // For each device, get additional info
    for (const device of devices) {
      if (device.status === "device") {
        try {
          const [manufacturer, model, androidVersion] = await Promise.all([
            runTaskSync(
              `-s ${device.id} shell getprop ro.product.manufacturer`
            ),
            runTaskSync(`-s ${device.id} shell getprop ro.product.model`),
            runTaskSync(
              `-s ${device.id} shell getprop ro.build.version.release`
            )
          ]);

          device.manufacturer = manufacturer.trim();
          device.model = model.trim();
          device.androidVersion = androidVersion.trim();
        } catch (err) {
          console.error(`Failed to get info for device ${device.id}:`, err);
        }
      }
    }

    return devices;
  },
  // takes ss and returns ssid ( saves in app_path )
  screenshot: async device => {
    const ssid = generateUUID();
    await runTaskSync(`-s ${device.id} shell screencap -p /sdcard/${ssid}.png`);
    await runTaskSync(`-s ${device.id} pull /sdcard/${ssid}.png ./${ssid}.png`);
    await runTaskSync(`-s ${device.id} shell rm /sdcard/${ssid}.png`);
    return ssid;
  }
};

// devices in array
var devicesList = null;
// device with id + data
var activeDevice = null;

const UI = {
  async fetchDevices() {
    const $activeList = $("#active-list");
    devicesList = await ADB.devices();
    devicesList.forEach(device => {
      const imgID = generateUUID();
      // updating
      $activeList.empty();
      $activeList.append(`
        <div class="w-full h-1/2 border p-2 rounded flex gap-3">
          <img id="${imgID}" class="h-full w-1/2 object-contain shadow-lg bg-black/20 border-0 outline-none">
          <div class="flex flex-col h-full gap-2 flex-1">
            <!-- half device details -->
            <div class="w-full flex flex-col gap-1">
              <div class="w-full bg-blue-400/60 p-1 rounded"><strong>ID</strong> ${
                device.id
              }</div>
              <div class="w-full bg-pink-400/60 p-1 rounded"><strong>Status</strong> ${
                device.status
              }</div>
              ${
                device.status === "device"
                  ? `
                <div class="w-full bg-blue-400/60 p-1 rounded"><strong>Manufacturer</strong> ${
                  device.manufacturer || "Unknown"
                }</div>
                <div class="w-full bg-pink-400/60 p-1 rounded"><strong>Model</strong> ${
                  device.model || "Unknown"
                }</div>
                <div class="w-full bg-blue-400/60 p-1 rounded"><strong>Android</strong> ${
                  device.androidVersion || "Unknown"
                }</div>
              `
                  : `
                <div class="text-gray-500 text-sm">Device not available (status: ${device.status})</div>
              `
              }
            </div>
            
            <div class="flex-1 rounded"></div>
          </div>
        </div>
      `);
      //ADB.screenshot(device).then(ssid => {
      //$(`#${imgID}`).attr("src", `/app-data/${kikxApp.id}/${ssid}.png`);
      //});
    });
  }
};

async function main() {
  await UI.fetchDevices();
}

// utils
function onKeyboardChange(callback) {
  let initialHeight = window.innerHeight;
  let keyboardOpen = false;

  function handleResize() {
    const diff = initialHeight - window.innerHeight;
    const isOpen = diff > 150; // threshold in px, adjust as needed
    if (isOpen !== keyboardOpen) {
      keyboardOpen = isOpen;
      callback(keyboardOpen);
    }
  }

  window.addEventListener("resize", handleResize);
}

kikxApp.run(async () => {
  $("#loading-screen").hide();
  // await main();
  // hide dock on input-el focus
  onKeyboardChange(active => {
    $("#dock").toggle(!active);
  });
});
