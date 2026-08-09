/**
 * Gallery client: loads manifest.json and renders cards + lightbox.
 */

(function () {
  const galleryEl = document.getElementById("gallery");
  const searchEl = document.getElementById("search");
  const statEl = document.getElementById("stat-count");
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightbox-img");
  const lightboxCaption = document.getElementById("lightbox-caption");
  const closeBtn = lightbox.querySelector(".lightbox-close");

  let paintings = [];
  let filter = "all";
  let query = "";

  function isAvailable(p) {
    return p.local_file && p.status !== "missing" && p.status !== "error";
  }

  function matches(p) {
    if (filter === "available" && !isAvailable(p)) return false;
    if (filter === "missing" && isAvailable(p)) return false;
    if (!query) return true;
    const hay = [p.artist, p.title, p.year, p.location, p.notes]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return hay.includes(query);
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function cardHtml(p) {
    const available = isAvailable(p);
    const media = available
      ? `<div class="card-media">
           <button type="button" data-open="${escapeHtml(p.id)}" aria-label="View ${escapeHtml(p.title)} larger">
             <img src="${escapeHtml(p.local_file)}" alt="${escapeHtml(p.title)} by ${escapeHtml(p.artist)}" loading="lazy" />
           </button>
         </div>`
      : `<div class="card-media missing"><span class="missing-badge">Image not found</span></div>`;

    const links = [];
    if (p.page_url) {
      links.push(`<a href="${escapeHtml(p.page_url)}" target="_blank" rel="noopener">Wikimedia</a>`);
    }
    if (p.museum_url) {
      links.push(`<a href="${escapeHtml(p.museum_url)}" target="_blank" rel="noopener">Source</a>`);
    }
    if (available) {
      links.push(`<a href="${escapeHtml(p.local_file)}" download>Download</a>`);
    }

    return `
      <article class="card" data-id="${escapeHtml(p.id)}">
        ${media}
        <div class="card-body">
          <p class="card-year">${escapeHtml(p.year || "—")}</p>
          <h2 class="card-title">${escapeHtml(p.title)}</h2>
          <p class="card-artist">${escapeHtml(p.artist)}</p>
          ${p.location ? `<p class="card-location">${escapeHtml(p.location)}</p>` : ""}
          ${p.notes ? `<p class="card-notes">${escapeHtml(p.notes)}</p>` : ""}
          ${links.length ? `<div class="card-links">${links.join("")}</div>` : ""}
        </div>
      </article>`;
  }

  function render() {
    const list = paintings.filter(matches);
    if (!list.length) {
      galleryEl.innerHTML = `<p class="empty">No paintings match your filters.</p>`;
      return;
    }
    galleryEl.innerHTML = list.map(cardHtml).join("");
  }

  function updateStats() {
    const total = paintings.length;
    const available = paintings.filter(isAvailable).length;
    statEl.textContent = `${available} of ${total} images available`;
  }

  function openLightbox(id) {
    const p = paintings.find((x) => x.id === id);
    if (!p || !isAvailable(p)) return;
    lightboxImg.src = p.local_file;
    lightboxImg.alt = `${p.title} by ${p.artist}`;
    lightboxCaption.innerHTML = `<strong>${escapeHtml(p.title)}</strong>${escapeHtml(p.artist)}${p.year ? ` · ${escapeHtml(p.year)}` : ""}`;
    if (typeof lightbox.showModal === "function") {
      lightbox.showModal();
    } else {
      lightbox.setAttribute("open", "");
    }
  }

  function closeLightbox() {
    if (typeof lightbox.close === "function") {
      lightbox.close();
    } else {
      lightbox.removeAttribute("open");
    }
    lightboxImg.removeAttribute("src");
  }

  galleryEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-open]");
    if (btn) openLightbox(btn.getAttribute("data-open"));
  });

  closeBtn.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) closeLightbox();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && lightbox.open) closeLightbox();
  });

  searchEl.addEventListener("input", () => {
    query = searchEl.value.trim().toLowerCase();
    render();
  });

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      filter = chip.dataset.filter;
      render();
    });
  });

  fetch("manifest.json")
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then((data) => {
      paintings = Array.isArray(data) ? data : [];
      updateStats();
      render();
    })
    .catch((err) => {
      galleryEl.innerHTML = `
        <p class="empty">
          Could not load <code>manifest.json</code>. Run
          <code>python3 download_images.py</code> first, then open this site via a local server
          (e.g. <code>python3 -m http.server</code>) or GitHub Pages.
          <br /><small>${escapeHtml(err.message)}</small>
        </p>`;
      statEl.textContent = "Manifest missing";
    });
})();
