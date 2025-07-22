const imageSettingsModule = {
  selectedImage: null,
  imagePaths: [
    {
      name: "Share",
      virtual: "share://images/bg",
      url: "/share/images/bg",
      canUpdate: false
    },
    {
      name: "Files",
      virtual: "home://share/images/bg",
      url: "/files/images/bg",
      canUpdate: true
    }
  ],

  currentPath: {
    virtual: "share://images/bg",
    url: "/share/images/bg",
    canUpdate: false
  },

  imageExtensions: [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"],

  // Create image element with click handler
  createImageElement(src) {
    const $wrapper = $("<div>").addClass(
      "relative h-full flex-none w-30 flex items-center justify-center"
    );

    const $skeleton = $("<div>").addClass(
      "absolute inset-0 bg-slate-700 animate-pulse rounded"
    );

    const $img = $("<img>")
      .attr("src", src)
      .addClass(
        "h-full w-auto max-w-full opacity-0 transition-opacity duration-500 cursor-pointer border-2 border-transparent hover:border-blue-500 p-1 rounded"
      )
      .on("load", function () {
        $(this).removeClass("opacity-0");
        $skeleton.remove();
      })
      .on("click", function () {
        $("#image-list img").removeClass("border-blue-500");
        $(this).addClass("border-blue-500");
        imageSettingsModule.selectedImage = src;
        $("#apps").css("background-image", `url('${src}')`);
      });

    return $wrapper.append($skeleton, $img);
  },
  createImageElement__(src) {
    return $("<img>")
      .attr("src", src)
      .addClass(
        "h-full cursor-pointer border-2 border-transparent hover:border-blue-500 p-1"
      )
      .on("click", function () {
        imageSettingsModule.selectedImage = src; // Save currently selected image
        $("#apps").css("background-image", `url("${src}")`);
        $("#image-list img").removeClass("border-blue-500");
        $(this).addClass("border-blue-500");
      });
  },

  // Render images from filesystem
  async renderImages() {
    const { virtual, url } = this.currentPath;
    
    await client.fs.createDirectory(virtual)
    const res = await client.fs.listFiles(virtual);
    if (res.error) return;

    this.basePath = url.endsWith("/") ? url : url + "/";

    const $imageList = $("#image-list");
    $imageList.empty();

    res.data
      .filter(
        file =>
          !file.directory &&
          this.imageExtensions.includes(file.suffix.toLowerCase())
      )
      .forEach(file => {
        const imgSrc = this.basePath + file.name;
        $imageList.append(this.createImageElement(imgSrc));
      });
  },

  async deleteImage(path) {
    return await client.fs.deleteFile(path);
  },
  handleDeleteSelectedImage: async function () {
    if (!imageSettingsModule.currentPath.canUpdate) return;
    const selected = imageSettingsModule.selectedImage;

    if (!selected) {
      $("#bg-upload-error").text("No image selected.");
      return;
    }

    const fileName = selected.replace(this.basePath, "");
    const fullPath = `${this.currentPath.virtual}/${fileName}`;

    try {
      const res = await imageSettingsModule.deleteImage(fullPath);

      if (res.error) {
        $("#bg-upload-error").text("Delete failed. " + (res.message || ""));
        return;
      }

      // Remove image from list and reset state
      $(`#image-list img[src="${selected}"]`).remove();

      if (kuiConfig.config.bg === imageSettingsModule.selectedImage) {
        // if deleted selected image
        imageSettingsModule.selectedImage = defaultBackground;
        kuiConfig.config.bg = defaultBackground;
        $("#apps").css("background-image", `url("${defaultBackground}")`);
      } else {
        // if non selected image
        kuiConfig.parse();
      }
    } catch (err) {
      $("#bg-upload-error").text("Unexpected error while deleting.");
      console.error(err);
    }
  },
  // uploads image to share://image/bg/random-id
  handleImageUpload: async function (event) {
    if (!imageSettingsModule.currentPath.canUpdate) return;

    const file = event.target.files[0];
    const $error = $("#bg-upload-error");
    $error.text("");

    if (!file) return;

    if (!file.type.startsWith("image/")) {
      $error.text("Only image files are allowed.");
      return;
    }

    // Generate random ID and extension

    const { virtual, url } = this.currentPath;
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    const randomId = Math.random().toString(36).substring(2, 10);
    const newFileName = `${randomId}${ext}`;
    const fullVirtualPath = `${virtual}/${newFileName}`;

    const renamedFile = new File([file], fullVirtualPath, { type: file.type });

    // Rename the file
    //const renamedFile = new File([file], fullVirtualPath, { type: file.type });

    try {
      // Upload with custom virtual path
      const res = await client.fs.uploadFile(renamedFile);

      if (res.error) {
        $error.text("Upload failed. " + (res.message || ""));
        return;
      }

      // Show preview using the new path
      const imageUrl = imageSettingsModule.basePath + newFileName;
      const $imageList = $("#image-list");
      const $img = imageSettingsModule.createImageElement(imageUrl);
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
      const $img = imageSettingsModule.createImageElement(imageUrl);
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
    this.selectedImage = null;

    $("#main").append(`
      <div id="kui-settings"
        onclick="imageSettingsModule.frameClick(event)"
        class="absolute w-full h-full flex flex-col insert-0 bg-slate-800/80 text-white z-[499]">
          <div class="p-1 border round-style m-2 bg-blue-400 flex justify-center items-center gap-1">
            <div class="w-6 h-6">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M5 19h14V5H5zm4-5.86l2.14 2.58l3-3.87L18 17H6z" opacity="0.3"/><path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2m0 16H5V5h14zm-4.86-7.14l-3 3.86L9 13.14L6 17h12z"/></svg>
            </div>
            <div>Wallpaper</div>
          </div>
        <!-- 
        <div class="absolute bottom-6 right-4 flex gap-2 items-center px-2">
          <div class="border bg-green-400/60 p-1 w-20 flex justify-center round-style" onclick="imageSettingsModule.close()">DONE</div>
        </div>
        -->

        <div class="flex flex-col gap-0.5 px-2">
          <div class="flex gap-1 items-center">
          
            <select id="virtual-path-selector" class="p-1 focus:outline-none border bg-transparent round-style text-white">
              ${this.imagePaths
                .map(
                  path =>
                    `<option value="${path.virtual}" ${
                      path.virtual === this.currentPath.virtual
                        ? "selected"
                        : ""
                    }>${path.name}</option>`
                )
                .join("")}
            </select>

            <input
              id="bg-url"
              class="w-full focus:outline-none border round-style p-1 bg-transparent"
              placeholder="Image url"
            />
            <div class="border rounded rounded-br-none bg-purple-400/60 p-1 px-4" onclick="imageSettingsModule.setBackgroundCustomUrl()">
               SET
            </div>
          </div>

          <div id="bg-url-error" class="text-red-400 text-sm mt-1"></div>
          <div id="bg-images" class="h-64 w-full border p-2 round-style overflow-x-auto">
            <div id="image-list" class="flex gap-1 h-full flex-nowrap">
              <!-- Images injected here -->
            </div>
          </div>

          <!-- Upload & Delete buttons -->
          <div style="display: none" id="upload-delete" class="flex gap-2 mt-2">
            <label for="bg-upload" class="flex-1 border bg-purple-500/60 px-4 py-1 round-style flex justify-center cursor-pointer">
              UPLOAD
            </label>
          
            <div
              id="bg-delete"
              class="flex-1 border bg-red-500/60 px-4 py-1 round-style flex justify-center cursor-pointer"
              onclick="imageSettingsModule.handleDeleteSelectedImage()"
            >
              DELETE
            </div>
          </div>
          
          <input
            id="bg-upload"
            type="file"
            accept="image/*"
            class="hidden"
            onchange="imageSettingsModule.handleImageUpload(event)"
          />
          
          <!-- Error message -->
          <div id="bg-upload-error" class="text-red-400 text-sm mt-1"></div>

        </div>
      </div>
    `);

    $("#virtual-path-selector").on("change", function () {
      const selectedVurtual = $(this).val();
      const selectedPath = imageSettingsModule.imagePaths.find(
        p => p.virtual === selectedVurtual
      );

      if (selectedPath) {
        imageSettingsModule.currentPath = selectedPath;
        imageSettingsModule.renderImages().then(() => {
          imageSettingsModule.toggleUploadDelete(); // call only after render is done
        });
      }
    });

    // Wait until images are rendered before toggling upload/delete buttons
    await imageSettingsModule.renderImages();
    imageSettingsModule.toggleUploadDelete(); // ✅ now the element exists
  },

  toggleUploadDelete() {
    const $block = $("#kui-settings #upload-delete");
    if ($block.length === 0) return; // exit if not found
    $block.toggle(this.currentPath.canUpdate);
  },

  // Handle save or cancel
  async close() {
    $("#kui-settings").remove();
    if (!this.selectedImage) return;

    kuiConfig.config.bg = this.selectedImage;

    await kuiConfig.save();
    // kuiConfig.parse();
  },

  frameClick(event) {
    // Check if the clicked element is the parent (not a child element)
    if (event.target === event.currentTarget) {
      // Call something if the click is on the parent
      imageSettingsModule.close();
    }
  }
};
