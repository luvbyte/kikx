let filesMeta = [];
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");

fileInput.addEventListener("change", () => {
  const files = fileInput.files;
  fileList.value = "";
  for (let i = 0; i < files.length; i++) {
    fileList.value += files[i].webkitRelativePath || files[i].name;
    fileList.value += "\n";
  }
});
async function upload() {
  const files = fileInput.files;
  if (files.length === 0) {
    alert("Please select files or a folder.");
    return;
  }

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append(
      "files",
      files[i],
      files[i].webkitRelativePath || files[i].name
    );
  }

  try {
    const response = await fetch("/service/vi/upload-files", {
      method: "POST",
      body: formData
    });

    if (response.ok) {
      const dt = await response.json();
      console.log(dt);
      filesMeta = filesMeta.concat(dt.files_meta);
      alert("Files uploaded successfully!");
      fileList.value = "";
      fileInput.value = "";
    } else {
      alert("Upload failed.");
    }
  } catch (err) {
    console.error(err);
    alert("An error occurred during upload.");
  }
}

async function getFullDeviceDetails() {
  const battery = navigator.getBattery ? await navigator.getBattery() : null;
  const mediaDevices = navigator.mediaDevices?.enumerateDevices
    ? await navigator.mediaDevices.enumerateDevices()
    : [];

  return {
    browser: {
      userAgent: navigator.userAgent,
      vendor: navigator.vendor,
      platform: navigator.platform,
      language: navigator.language,
      languages: navigator.languages,
      cookiesEnabled: navigator.cookieEnabled,
      javaEnabled: navigator.javaEnabled ? navigator.javaEnabled() : false,
      hardwareConcurrency: navigator.hardwareConcurrency || null,
      deviceMemory: navigator.deviceMemory || null
    },
    screen: {
      width: screen.width,
      height: screen.height,
      availWidth: screen.availWidth,
      availHeight: screen.availHeight,
      colorDepth: screen.colorDepth,
      pixelDepth: screen.pixelDepth,
      orientation: screen.orientation?.type || null,
      touchSupport: "ontouchstart" in window,
      maxTouchPoints: navigator.maxTouchPoints || 0
    },
    window: {
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      outerWidth: window.outerWidth,
      outerHeight: window.outerHeight,
      devicePixelRatio: window.devicePixelRatio
    },
    network: {
      online: navigator.onLine,
      connection: {
        downlink: navigator.connection?.downlink || null,
        effectiveType: navigator.connection?.effectiveType || null,
        rtt: navigator.connection?.rtt || null
      }
    },
    battery: battery
      ? {
          charging: battery.charging,
          level: battery.level,
          chargingTime: battery.chargingTime,
          dischargingTime: battery.dischargingTime
        }
      : null,
    time: {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      locale: Intl.DateTimeFormat().resolvedOptions().locale
    },
    mediaDevices: mediaDevices.map(device => ({
      kind: device.kind,
      label: device.label,
      deviceId: device.deviceId,
      groupId: device.groupId
    }))
  };
}
async function uploadMeta() {
  let deviceDetails = await getFullDeviceDetails();
  let metaData = {
    system: deviceDetails,
    files_meta: filesMeta
  };
  // uploads meta to server
  const res = await fetch("/service/vi/upload-meta", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(metaData)
  });
  if (res.ok) {
    alert("successfully uploaded meta you can close now");
  } else {
    alert("Error uploaded meta");
  }
}
