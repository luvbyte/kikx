const kawaiGifsModule = {
  config: {
    gifs: [],
    width: "120px",
    height: "auto",
    extendGifs: function (list) {
      if (!Array.isArray(list)) return;
      this.gifs = [...new Set([...this.gifs, ...list])];
    }
  },

  outsideClickHandler: null,
  // open panel
  open: function () {
    const panelId = "gifs-picker-panel";
    const $main = $("#main");

    if ($("#" + panelId).length) return;

    const $panel = $(`
      <div id="${panelId}" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white/80 border border-black/60 shadow-lg rounded p-2 w-72 max-h-96 min-h-60 overflow-y-auto flex flex-col gap-2">
    
        <!-- Header: Label + Buttons -->
        <div class="flex items-center justify-between mb-1 gap-1">
        
          <div class="w-full flex items-center rounded-md gap-1">
            <div>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 20 20"><path fill="currentColor" d="M18 10a8 8 0 1 0-16 0a8 8 0 0 0 16 0M3 10a7 7 0 1 1 14 0a7 7 0 0 1-14 0m10.5-1.5a1 1 0 1 0-2 0a1 1 0 0 0 2 0m-5 0a1 1 0 1 0-2 0a1 1 0 0 0 2 0m-1.611 4.015a.5.5 0 1 0-.778.629A5 5 0 0 0 10 15c1.57 0 2.973-.725 3.889-1.856a.5.5 0 1 0-.778-.63A4 4 0 0 1 10 14a4 4 0 0 1-3.111-1.485"/></svg>
            </div>
            <div>GIFS</div>
          </div>

          <div class="flex items-center gap-1">
            <button onclick="kawaiGifsModule.removeAllGifs()" class="text-sm text-black px-2 py-1 rounded shadow-lg shadow-blue-300 bg-blue-400">
              <svg xmlns="http://www.w3.org/2000/svg" width="21" height="21" viewBox="0 0 21 21"><g fill="none" fill-rule="evenodd" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1"><path d="M3.578 6.487A8 8 0 1 1 2.5 10.5"/><path d="M7.5 6.5h-4v-4"/></g></svg>
            </button>
            <button onclick="kawaiGifsModule.close()" class="bg-red-400 text-black text-lg px-2 py-1 rounded shadow-lg shadow-red-300">
              <svg xmlns="http://www.w3.org/2000/svg" width="21" height="21" viewBox="0 0 24 24"><path fill="currentColor" d="m6.4 18.308l-.708-.708l5.6-5.6l-5.6-5.6l.708-.708l5.6 5.6l5.6-5.6l.708.708l-5.6 5.6l5.6 5.6l-.708.708l-5.6-5.6z"/></svg>
            </button>
          </div>
        </div>
    
        <!-- Gifs Grid -->
        <div class="grid grid-cols-3 gap-2 justify-items-center">
          ${this.config.gifs
            .map(
              (src, index) => `
                <img src="${src}" data-waifu-index="${index}" class="w-20 h-20 object-contain cursor-pointer hover:scale-105 transition-transform duration-200" />
              `
            )
            .join("")}
        </div>
      </div>
    `);

    $main.append($panel);

    $panel.find("img").on("click", e => {
      const index = $(e.currentTarget).data("waifu-index");
      this.addGif(this.config.gifs[index]);
    });

    this.outsideClickHandler = this.handleOutsideClick.bind(this);
    setTimeout(() => {
      $(document).on("mousedown touchstart", this.outsideClickHandler);
    }, 0);
  },
  handleOutsideClick: function (e) {
    const panelId = "gifs-picker-panel";
    if (!$(e.target).closest("#" + panelId).length) {
      this.close();
    }
  },

  close: function () {
    const panelId = "gifs-picker-panel";
    const $panel = $("#" + panelId);

    if ($panel.length) {
      $panel.fadeOut(200, () => {
        $panel.remove();
      });

      if (this.outsideClickHandler) {
        $(document).off("mousedown touchstart", this.outsideClickHandler);
        this.outsideClickHandler = null;
      }
    }
  },

  addGif: function (gifSrc) {
    const $main = $("#main");
    const overlayId = "waifu-" + Date.now();

    const $overlay = $(`
    <div id="${overlayId}" class="waifu-overlay absolute top-10 left-10 z-50 rounded-lg overflow-hidden touch-none border-2 border-transparent" style="touch-action: none;">
      <img src="${gifSrc}" class="w-full h-full block select-none pointer-events-none" draggable="false" />
    </div>
  `);

    // Initial dimensions
    const initialWidth = parseInt(this.config.width) || 120;
    let width = initialWidth;
    let height = initialWidth;

    $overlay.css({ width: width + "px", height: height + "px" });

    $main.append($overlay);

    let wasDragged = false;

    // ✅ Enable dragging
    $overlay.draggable({
      containment: "#main",
      start: () => {
        wasDragged = true;
      },
      stop: () => {
        setTimeout(() => {
          wasDragged = false;
        }, 150);
      }
    });

    // ✅ Double click / double tap to remove
    let lastTap = 0;
    $overlay.on("click", function () {
      const now = new Date().getTime();
      if (now - lastTap < 300) {
        $overlay.remove(); // double tap detected
      }
      lastTap = now;
    });

    // ✅ Pinch to resize naturally
    let currentScale = 1;

    interact($overlay[0]).gesturable({
      listeners: {
        move(event) {
          currentScale *= 1 + event.ds;
          currentScale = Math.max(0.3, Math.min(currentScale, 3));

          const newWidth = initialWidth * currentScale;
          const newHeight = initialWidth * currentScale;

          $overlay.css({
            width: newWidth + "px",
            height: newHeight + "px"
          });
        }
      }
    });
  },

  removeAllGifs: function () {
    $(".waifu-overlay").remove();
  }
};
