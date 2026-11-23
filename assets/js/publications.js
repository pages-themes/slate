(function () {
  "use strict";

  const controls = document.querySelector(".publication-filters");
  if (!controls) return;
  const search = document.getElementById("publication-search");
  const type = document.getElementById("publication-type");
  const year = document.getElementById("publication-year");
  const clear = document.getElementById("publication-clear");
  const count = document.getElementById("publication-count");
  const noResults = document.getElementById("publication-no-results");
  const groups = Array.from(document.querySelectorAll(".publication-year"));
  const cards = Array.from(document.querySelectorAll(".publication-card"));

  controls.hidden = false;

  function update() {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    groups.forEach((group) => {
      let groupVisible = 0;
      group.querySelectorAll(".publication-card").forEach((card) => {
        const searchable = [
          card.querySelector("h3")?.textContent,
          card.querySelector(".publication-card__authors")?.textContent,
          card.querySelector(".publication-card__venue")?.textContent
        ].join(" ").toLocaleLowerCase();
        const matches = (!query || searchable.includes(query)) &&
          (type.value === "all" || card.dataset.publicationType === type.value) &&
          (year.value === "all" || group.dataset.year === year.value);
        card.hidden = !matches;
        if (matches) groupVisible += 1;
      });
      group.hidden = groupVisible === 0;
      visible += groupVisible;
    });
    count.textContent = `Showing ${visible} of ${cards.length} publication${cards.length === 1 ? "" : "s"}`;
    noResults.hidden = visible !== 0;
  }

  search.addEventListener("input", update);
  type.addEventListener("change", update);
  year.addEventListener("change", update);
  clear.addEventListener("click", () => {
    search.value = "";
    type.value = "all";
    year.value = "all";
    update();
    search.focus();
  });
  update();
}());
