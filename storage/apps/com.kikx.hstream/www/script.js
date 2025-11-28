document.addEventListener("DOMContentLoaded", () => {
  const option1 = document.getElementById("option1");
  const option2 = document.getElementById("option2");
  const option3 = document.getElementById("option3");

  const dropdown1 = document.getElementById("dropdown1");
  const dropdown2 = document.getElementById("dropdown2");
  const qrScanner = document.getElementById("qr-scanner");

  function updateView() {
    dropdown1.classList.add("hidden");
    dropdown2.classList.add("hidden");
    qrScanner.classList.add("hidden");

    if (option1.checked) {
      dropdown1.classList.remove("hidden");
    } else if (option2.checked) {
      dropdown2.classList.remove("hidden");
    } else if (option3.checked) {
      qrScanner.classList.remove("hidden");

      // Initialize QR scanner only once
      if (!window.qrStarted) {
        const qr = new Html5Qrcode("qr-scanner-box");
        Html5Qrcode.getCameras().then(cameras => {
          if (cameras && cameras.length) {
            qr.start(
              cameras[0].id,
              {
                fps: 10,
                qrbox: 200
              },
              decodedText => {
                alert("Scanned: " + decodedText);
                qr.stop(); // Optional: stop after first scan
              },
              error => {}
            );
            window.qrStarted = true;
          }
        }).catch(err => {
          console.error("Camera error:", err);
        });
      }
    }
  }

  [option1, option2, option3].forEach(opt => {
    opt.addEventListener("change", updateView);
  });

  updateView(); // Initial view
});