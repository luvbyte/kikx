"use strict";

let pathProtocol = "home://";
let currentPath = "";
let currentFilePath = "";

/* -------------------------- Utilities -------------------------- */

const sanitizeText = text => {
  if (typeof text !== "string") return "";
  return text.replace(/[<>]/g, "");
};

const isValidPath = path => {
  return typeof path === "string" && !path.includes("..");
};

const safeExt = ext => {
  if (!ext) return "";
  return ext.toLowerCase();
};

/* -------------------------- Viewers -------------------------- */

const viewText = async (res, file) => {
  $("#text-editor").removeClass("hidden");

  $("#text-filename").text(sanitizeText(file.name));
  $("#text-panel").val(await blobToText(res.data));
};

const viewImage = async (res, file) => {
  $("#image-viewer").removeClass("hidden");

  const blobUrl = URL.createObjectURL(res.data);

  $("#image-filename").text(sanitizeText(file.name));
  $("#image-frame").attr("src", blobUrl);
};

const playVideo = async (res, file) => {
  $("#video-viewer").removeClass("hidden");

  const blobUrl = URL.createObjectURL(res.data);

  $("#video-filename").text(sanitizeText(file.name));
  $("#video-frame").attr("src", blobUrl);
};

/* -------------------------- File Actions -------------------------- */

const openFile = async file => {
  if (!file || !file.name) return;

  const path = file.path + file.name;

  if (!isValidPath(path)) return;

  const res = await kikxApp.fs.readFile(path);
  if (!res || res.err) return;

  currentFilePath = path;
  $(".panel").addClass("hidden");

  const ext = safeExt(file.suffix);

  const imageExtensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"];
  const videoExtensions = [".mp4"];

  if (imageExtensions.includes(ext)) {
    await viewImage(res, file);
  } else if (videoExtensions.includes(ext)) {
    await playVideo(res, file);
  } else {
    await viewText(res, file);
  }
};

const closeFile = () => {
  $(".panel").addClass("hidden");
  $("#file-browser").removeClass("hidden");
};

const saveTextFile = async () => {
  if (!currentFilePath) return;

  const content = $("#text-panel").val();

  const res = await kikxApp.fs.writeFile(currentFilePath, content);

  if (res && !res.err) {
    alert("File saved");
  }
};

/* -------------------------- Rendering -------------------------- */

const getFileIconPath = ext => {
  const iconsPath = "icons/";
  const imageExtensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"];

  if (imageExtensions.includes(safeExt(ext))) {
    return iconsPath + "picture.png";
  }

  return iconsPath + "file.png";
};

const renderFiles = files => {
  const container = $("#files-panel");
  container.empty();

  files.forEach(file => {
    const wrapper = $("<div>")
      .addClass("w-14 h-14 flex flex-col items-center");

    const img = $("<img>")
      .addClass("w-8 h-8")
      .attr("alt", "file icon")
      .attr("src", file.icon);

    const nameDiv = $("<div>")
      .addClass("text-sm mt-1 truncate w-full text-center")
      .text(sanitizeText(file.name));

    wrapper.append(img);
    wrapper.append(nameDiv);

    wrapper.on("click", () => {
      if (file.directory) {
        currentPath += file.name + "/";
        loadFiles();
      } else {
        openFile(file);
      }
    });

    container.append(wrapper);
  });
};

/* -------------------------- Path Handling -------------------------- */

function transformList(items) {
  return items.map(item => ({
    name: sanitizeText(item.name),
    suffix: item.suffix,
    directory: item.directory,
    path: pathProtocol + currentPath,
    icon: item.directory
      ? "icons/folder.png"
      : getFileIconPath(item.suffix)
  }));
}

function goBackOnePath() {
  const parts = currentPath.replace(/\/+$/, "").split("/");
  parts.pop();
  currentPath = parts.length ? parts.join("/") + "/" : "";
  loadFiles();
}

function goHomePath() {
  if (!currentPath) return;
  currentPath = "";
  loadFiles();
}

/* -------------------------- Loader -------------------------- */

const loadFiles = async () => {
  const path = pathProtocol + currentPath;

  if (!isValidPath(path)) return;

  const res = await kikxApp.fs.listFiles(path);

  if (res && res.data) {
    $("#file-path").val(path);
    renderFiles(transformList(res.data));

    $("#loading-screen").fadeOut(400, function () {
      $(this).remove();
    });
  }
};

/* -------------------------- Init -------------------------- */

$(async () => {
  await loadFiles();
});