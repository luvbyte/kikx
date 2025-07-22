const soundModule = {
  silent: false,
  sounds: "assets/sound",
  notifySound: "drop_002",

  play(file) {
    const audio = new Audio(file);
    audio.play();
  },
  playSound(name, ext = "ogg") {
    if (this.silent) return;
    this.play(`${this.sounds}/${name}.${ext}`);
  },
  notify() {
    this.playSound(this.notifySound);
  },
  // create tommorow
  openSettings() {}
};
