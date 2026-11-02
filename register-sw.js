if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("./sw.js?v=4f0695bd50b1").catch(function () {
      /* offline / private mode — ignore */
    });
  });
}
