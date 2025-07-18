const kuiSettingsApp = {
  settings: JSON.parse(JSON.stringify(kuiConfig)),
  selectedImage: null,
  basePath: "/share/images/bg/",
  imageExtensions: [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"],

  // Create image element with click handler
  createImageElement(src) {
    return $("<img>")
      .attr("src", src)
      .addClass(
        "h-full cursor-pointer border-2 border-transparent hover:border-blue-500 p-1"
      )
      .on("click", function () {
        kuiSettingsApp.settings.bg = src;
        kuiSettingsApp.selectedImage = src; // Save currently selected image
        $("#apps").css("background-image", `url("${src}")`);
        $("#image-list img").removeClass("border-blue-500");
        $(this).addClass("border-blue-500");
      });
  },

  // Render images from filesystem
  async renderImages() {
    const res = await client.fs.listFiles("share://images/bg");
    if (res.error) return;

    const $imageList = $("#image-list");
    $imageList.empty();

    res.data
      .filter(
        file =>
          !file.directory &&
          kuiSettingsApp.imageExtensions.includes(file.suffix.toLowerCase())
      )
      .forEach(file => {
        const imgSrc = kuiSettingsApp.basePath + file.name;
        $imageList.append(kuiSettingsApp.createImageElement(imgSrc));
      });
  },

  async deleteImage(path) {
    return await client.fs.deleteFile(path);
  },
  handleDeleteSelectedImage: async function () {
    const selected = kuiSettingsApp.selectedImage;

    if (!selected) {
      $("#bg-upload-error").text("No image selected.");
      return;
    }

    const fileName = selected.replace(kuiSettingsApp.basePath, "");
    const fullPath = `share://images/bg/${fileName}`;

    try {
      const res = await kuiSettingsApp.deleteImage(fullPath);

      if (res.error) {
        $("#bg-upload-error").text("Delete failed. " + (res.message || ""));
        return;
      }

      // Remove image from list and reset state
      $(`#image-list img[src="${selected}"]`).remove();

      if (kuiConfig.bg === kuiSettingsApp.selectedImage) {
        // if deleted selected image
        kuiSettingsApp.selectedImage = null;
        kuiSettingsApp.settings.bg = "bg.png";
        $("#apps").css("background-image", `url("bg.png")`);
      } else {
        // if non selected image
        kuiSettingsApp.selectedImage = null;
        kuiSettingsApp.settings.bg = kuiConfig.bg;

        setValidBackground(kuiConfig.bg);
        //$("#apps").css("background-image", `url("${}")`);
        //$("#apps").css("background-image", kuiConfig.bg);
      }

      //kuiSettingsApp.selectedImage = null;
      //kuiSettingsApp.settings.bg = "";
      //$("#apps").css("background-image", "none");
    } catch (err) {
      $("#bg-upload-error").text("Unexpected error while deleting.");
      console.error(err);
    }
  },
  // uploads image to share://image/bg/random-id
  handleImageUpload: async function (event) {
    const file = event.target.files[0];
    const $error = $("#bg-upload-error");
    $error.text("");

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      $error.text("Only image files are allowed.");
      return;
    }

    // Generate random ID and extension
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    const randomId = Math.random().toString(36).substring(2, 10); // e.g. "a9gkz1qw"
    const newFileName = `${randomId}${ext}`;
    const fullVirtualPath = `share://images/bg/${newFileName}`;

    // Rename the file
    const renamedFile = new File([file], fullVirtualPath, { type: file.type });

    try {
      // Upload with custom virtual path
      const res = await client.fs.uploadFile(renamedFile);

      if (res.error) {
        $error.text("Upload failed. " + (res.message || ""));
        return;
      }

      // Show preview using the new path
      const imageUrl = kuiSettingsApp.basePath + newFileName;
      const $imageList = $("#image-list");
      const $img = kuiSettingsApp.createImageElement(imageUrl);
      $imageList.prepend($img);
      $img.click();
    } catch (err) {
      $error.text("Unexpected error during upload.");
      console.error(err);
    }
  },

  // Add custom background from URL
  setBackgroundCustomUrl() {
    const imageUrl = $("#bg-url").val().trim();
    const $error = $("#bg-url-error");
    $error.text(""); // Clear previous error

    if (!imageUrl) return;

    const testImage = new Image();
    testImage.onload = function () {
      const $imageList = $("#image-list");
      const $img = kuiSettingsApp.createImageElement(imageUrl);
      $imageList.prepend($img);
      $img.click(); // auto-select
    };
    testImage.onerror = function () {
      $error.text("Failed to load image. Please check the URL.");
    };

    testImage.src = imageUrl;
  },

  // Open settings UI
  async openSettings() {
    $controlCenter.hide();

    $("#main").append(`
      <div id="kui-settings"
        class="absolute w-full h-full flex flex-col insert-0 bg-slate-800/80 text-white z-[499]">
          <div class="text-center p-2 bg-gradient-to-b from-purple-400 to-blue-400/80 font-bold">KUI SETTINGS</div>
    
          <div class="p-1 border round-style m-2 bg-blue-400/60 flex justify-center items-center gap-1">
            <div class="w-6 h-6">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M5 19h14V5H5zm4-5.86l2.14 2.58l3-3.87L18 17H6z" opacity="0.3"/><path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2m0 16H5V5h14zm-4.86-7.14l-3 3.86L9 13.14L6 17h12z"/></svg>
            </div>
            <div>Wallpaper</div>
          </div>
          
        <div class="absolute bottom-6 right-4 flex gap-2 items-center px-2">
          <div class="border bg-red-400/60 p-1 w-20 flex justify-center round-style" onclick="kuiSettingsApp.kuiSettingsUpdate(false)">CANCEL</div>
          <div class="border bg-green-400/60 p-1 w-20 flex justify-center round-style" onclick="kuiSettingsApp.kuiSettingsUpdate(true)">SAVE</div>
        </div>
        
        <div class="flex flex-col gap-0.5 px-2">
          <div class="flex gap-1 items-center">
            <input
              id="bg-url"
              class="w-full focus:outline-none border round-style p-1 bg-transparent"
              placeholder="Image url"
            />
            <div class="border rounded rounded-br-none bg-purple-400/60 p-1 px-4" onclick="kuiSettingsApp.setBackgroundCustomUrl()">
               SET
            </div>
          </div>
          <div id="bg-url-error" class="text-red-400 text-sm mt-1"></div>
          <div id="bg-images" class="h-64 w-full border p-2 round-style overflow-x-auto">
            <div id="image-list" class="flex h-full">
              <!-- Images injected here -->
            </div>
          </div>

          <!-- Upload & Delete buttons -->
          <div class="flex gap-2 mt-2">
            <label for="bg-upload" class="flex-1 border bg-purple-500/60 px-4 py-1 round-style flex justify-center cursor-pointer">
              UPLOAD
            </label>
          
            <div
              id="bg-delete"
              class="flex-1 border bg-red-500/60 px-4 py-1 round-style flex justify-center cursor-pointer"
              onclick="kuiSettingsApp.handleDeleteSelectedImage()"
            >
              DELETE
            </div>
          </div>
          
          <input
            id="bg-upload"
            type="file"
            accept="image/*"
            class="hidden"
            onchange="kuiSettingsApp.handleImageUpload(event)"
          />
          
          <!-- Error message -->
          <div id="bg-upload-error" class="text-red-400 text-sm mt-1"></div>

        </div>
      </div>
    `);

    await kuiSettingsApp.renderImages();
  },

  getSettings() {
    //if (Object.keys(kuiSettingsApp.settings).length === 0) {
    //return null;
    //}
    return JSON.stringify(kuiSettingsApp.settings);
  },

  // Save settings to disk
  async saveSettings() {
    $("#kui-settings").remove();
    const updatedSettings = kuiSettingsApp.getSettings();

    //if (updatedSettings) {
    await client.fs.createDirectory("home://.config/kui");
    await client.fs.writeFile(
      "home://.config/kui/config.json",
      updatedSettings
    );
    // }
  },

  // Cancel without saving
  cancelSettings() {
    $("#kui-settings").remove();
  },

  // Handle save or cancel
  async kuiSettingsUpdate(save = true) {
    if (save) {
      await kuiSettingsApp.saveSettings();
      kuiSettingsApp.settings = {}; // Reset temp settings
      await updateKuiConfig(); // Apply new config
    } else {
      kuiSettingsApp.cancelSettings(); // Just close UI, no apply
      await updateKuiConfig(false); // Apply new config
    }
  }
};
