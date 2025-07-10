let pathProtocol = "home://";
let currentPath = "";

let currentFilePath = "";

const viewText = async (res, file) => {
  $("#text-editor").removeClass("hidden");

  $("#text-filename").text(file.name);
  $("#text-panel").val(await blobToText(res.data));
};
const viewImage = async (res, file) => {
  $("#image-viewer").removeClass("hidden");
  const blobUrl = URL.createObjectURL(res.data);

  $("#image-frame").attr("src", blobUrl);
};
const playVideo = async (res, file) => {};

const openFile = async file => {
  const path = file.path + file.name;
  const res = await kikxApp.fs.readFile(path);

  console.log(res);

  // return on error
  if (res.err) return;

  currentFilePath = path;
  $(".panel").addClass("hidden");

  const ext = file.suffix.toLowerCase();

  const imageExtensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"];
  const videoExternsion = [".mp4"];
  if (imageExtensions.includes(ext)) {
    await viewImage(res, file);
  } else if (videoExternsion.includes(ext)) await playVideo(res, file);
  else {
    await viewText(res, file);
  }
};

const closeFile = async () => {
  $(".panel").addClass("hidden");
  $("#file-browser").removeClass("hidden");
};

const saveTextFile = async () => {
  if (currentFilePath.length <= 0) return;

  const res = await kikxApp.fs.writeFile(
    currentFilePath,
    $("#text-panel").val()
  );
  if (res.dataa) {
    alert("file saved");
  }
};

const renderFiles = files => {
  const container = $("#files-panel");
  container.empty(); // Clear existing content

  files.forEach(file => {
    const fileElement = $(`
        <div class="w-14 h-14 flex flex-col items-center">
          <img src="${file.icon}" alt="${file.name} icon" class="w-8 h-8" />
          <div class="text-sm mt-1 truncate w-full text-center">${file.name}</div>
        </div>
      `);
    fileElement.on("click", function () {
      if (file.directory) {
        currentPath += file.name + "/";
        loadFiles();
      } else {
        openFile(file);
      }
    });
    container.append(fileElement);
  });
};

const getFileIconPath = ext => {
  const iconsPath = "icons/";

  const imageExtensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"];
  if (imageExtensions.includes(ext)) {
    return iconsPath + "picture.png";
  } else {
    return iconsPath + "file.png";
  }
};

function transformList(items) {
  return items.map(item => ({
    name: item.name,
    suffix: item.suffix,
    directory: item.directory,
    path: pathProtocol + currentPath,
    icon: item.directory ? "icons/folder.png" : getFileIconPath(item.suffix)
  }));
}

function goBackOnePath() {
  const parts = currentPath.replace(/\/+$/, "").split("/");
  parts.pop();
  currentPath = parts.length ? parts.join("/") + "/" : "";
  loadFiles();
}

function goHomePath() {
  if (currentPath.length === 0) return;
  currentPath = "";
  loadFiles();
}

const loadFiles = async () => {
  path = pathProtocol + currentPath;

  const res = await kikxApp.fs.listFiles(path);
  if (res.data) {
    $("#file-path").val(path);
    renderFiles(transformList(res.data));
    $("#loading-screen").fadeOut(400, function () {
      $(this).remove();
    });
  }
};

$(async () => {
  kikxApp.system.getUserSettings().then(res => {
    if (res.data) {
      $("html").toggleClass("dark", res.data.dark_mode);
    }
  });
  loadFiles();
});
