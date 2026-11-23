(function () {
  "use strict";

  document.documentElement.classList.add("news-has-js");

  document.querySelectorAll(".news-card__toggle").forEach(function (button) {
    button.addEventListener("click", function () {
      const card = button.closest(".news-card");
      const expanded = button.getAttribute("aria-expanded") === "true";
      const citation = card.querySelector(".news-card__expanded");

      button.setAttribute("aria-expanded", String(!expanded));
      button.textContent = expanded ? "+ More" : "− Less";
      card.classList.toggle("news-card--expanded", !expanded);
      citation.hidden = expanded;
    });
  });
}());
