class VIService extends Service {
  constructor() {
    super("vi");
  }
  authKey = () => this.request("app-access");
}

$(async () => {
  const vi = new VIService();
  const req = await vi.authKey()

  if (req.ok) {
    // create iframe with jQuery
    const $iframe = $("<iframe>", {
      class: "w-full h-full",
      src: req.data.url,
      allowfullscreen: "true",
      allow: "accelerometer; gyroscope; fullscreen"
    });

    // when iframe finishes loading
    $iframe.on("load", function () {
      $("#loading-screen").hide();
    });
    $("#main").append($iframe);
  } else {
    // show error
  }
});
