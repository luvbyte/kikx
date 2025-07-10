const tabs = {
  display: {},
  sensors: {}
};

function onTabSelect(element) {}

async function main() {
  $(".tab-button").click(function () {
    const index = $(this).index();

    // Remove active classes from all buttons
    $(".tab-button").removeClass("active text-blue-500 border-blue-500");
    // Hide all tab contents
    $(".tab-content").addClass("hidden");

    // Add active class to the clicked button
    $(this).addClass("active text-blue-500 border-blue-500");
    // Show corresponding content
    $(".tab-content").eq(index).removeClass("hidden");
  });
  // Initialize first tab as active
  $(".tab-button").first().addClass("active text-blue-500 border-blue-500");
}

$(async () => {
  $("#loading-screen").fadeOut(400, function () {
    $(this).remove();
  });
  await main();
});

function refresh() {
  location.reload();
}
