const bgSettingsModule = {
  selectedImage: null,
  imagePaths: [
    {
      name: "SHARE",
      virtual: "share://images/bg",
      url: "/share/images/bg",
      canUpdate: false
    },
    {
      name: "LOCAL",
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
        bgSettingsModule.selectedImage = src;
        $("#apps").css("background-image", `url('${src}')`);
      });

    return $wrapper.append($skeleton, $img);
  },
  // Render images from filesystem
  async renderImages() {
    const { virtual, url } = this.currentPath;

    await client.fs.createDirectory(virtual);
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
    if (!bgSettingsModule.currentPath.canUpdate) return;
    const selected = bgSettingsModule.selectedImage;

    if (!selected) {
      $("#bg-upload-error").text("No image selected.");
      return;
    }

    const fileName = selected.replace(this.basePath, "");
    const fullPath = `${this.currentPath.virtual}/${fileName}`;

    try {
      const res = await bgSettingsModule.deleteImage(fullPath);

      if (res.error) {
        $("#bg-upload-error").text("Delete failed. " + (res.message || ""));
        return;
      }

      // Remove image from list and reset state
      $(`#image-list img[src="${selected}"]`).remove();

      if (kuiConfig.config.bg === bgSettingsModule.selectedImage) {
        // if deleted selected image
        bgSettingsModule.selectedImage = defaultBackground;
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
    if (!bgSettingsModule.currentPath.canUpdate) return;

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
      const imageUrl = bgSettingsModule.basePath + newFileName;
      const $imageList = $("#image-list");
      const $img = bgSettingsModule.createImageElement(imageUrl);
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
      const $img = bgSettingsModule.createImageElement(imageUrl);
      $imageList.prepend($img);
      $img.click(); // auto-select
    };
    testImage.onerror = function () {
      $error.text("Failed to load image. Please check the URL.");
    };

    testImage.src = imageUrl;
  },

  // Open settings UI
  async open() {
    this.selectedImage = null;

    $("#main").append(`
      <div id="kui-settings"
        onclick="bgSettingsModule.frameClick(event)"
        class="absolute w-full h-full flex flex-col justify-between insert-0 text-white z-[499]">
        
        <div class="flex flex-col animate__animated animate__slideInDown animate__faster">
          <div class="flex gap-1 items-center bg-gradient-to-br from-blue-400 to-pink-400 shadow-2xl h-16 px-2">
          
            <select id="virtual-path-selector" class="p-1 focus:outline-none border round-style bg-transparent text-white">
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
              class="w-full focus:outline-none border round-style p-1 bg-transparent placeholder:text-white"
              placeholder="Image url"
            />
            <div class="border rounded rounded-br-none bg-purple-400/60 p-1 px-4" onclick="bgSettingsModule.setBackgroundCustomUrl()">
               SET
            </div>
          </div>
          
         <!-- Upload & Delete buttons -->
          <div style="display: none" id="upload-delete" class="flex gap-2 p-2 bg-black/20">
            <label for="bg-upload" class="flex-1 border bg-purple-500/80 px-4 py-1 round-style flex justify-center cursor-pointer">
              UPLOAD
            </label>
          
            <div
              id="bg-delete"
              class="flex-1 border bg-red-500/80 px-4 py-1 round-style flex justify-center cursor-pointer"
              onclick="bgSettingsModule.handleDeleteSelectedImage()"
            >
              DELETE
            </div>
          </div>
          
          <input
            id="bg-upload"
            type="file"
            accept="image/*"
            class="hidden"
            onchange="bgSettingsModule.handleImageUpload(event)"
          />
          
          <!-- Error message -->
          <div id="bg-upload-error" class="text-red-400 text-sm px-2"></div>
          <div id="bg-url-error" class="text-red-400 text-sm px-2"></div>
        </div>
          
        <!-- images panel-->
        <div class="flex flex-col gap-0.5 bg-black/20 animate__animated animate__slideInUp animate__faster">
          <div id="bg-images" class="h-64 w-full p-2 overflow-x-auto">
            <div id="image-list" class="flex gap-1 h-full flex-nowrap">
              <!-- Images injected here -->
            </div>
          </div>
        </div>
      </div>
    `);

    $("#virtual-path-selector").on("change", function () {
      const selectedVurtual = $(this).val();
      const selectedPath = bgSettingsModule.imagePaths.find(
        p => p.virtual === selectedVurtual
      );

      if (selectedPath) {
        bgSettingsModule.currentPath = selectedPath;
        bgSettingsModule.renderImages().then(() => {
          bgSettingsModule.toggleUploadDelete(); // call only after render is done
        });
      }
    });

    // Wait until images are rendered before toggling upload/delete buttons
    await bgSettingsModule.renderImages();
    bgSettingsModule.toggleUploadDelete(); // ✅ now the element exists
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
      bgSettingsModule.close();
    }
  }
};
