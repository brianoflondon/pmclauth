if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("./sw.js?v=86c6e616289b").catch(function () {
      /* offline / private mode — ignore */
    });
  });
}
