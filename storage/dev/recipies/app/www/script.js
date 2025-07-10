async function main() {}

$(async () => {
  $("#loading-screen").fadeOut(400, function () {
    $(this).remove();
  });
  await main()
});

function refresh() {
  location.reload();
}
