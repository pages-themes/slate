---
layout: default
title: Publications
description: Reviewed research publications from the AutoDIAL group.
---

<header class="publications-intro">
  <p class="eyebrow">Research outputs</p>
  <h1>Publications</h1>
  <p>Research publications selected and reviewed for the AutoDIAL website. Links to papers, software, and datasets are included when available.</p>
</header>

{% assign sorted_publications = site.data.publications | sort: 'year' | reverse %}
{% if sorted_publications.size > 0 %}
  {% assign publication_years = sorted_publications | group_by: 'year' %}
  <div class="publication-filters" hidden>
    <label for="publication-search">Search publications
      <input id="publication-search" type="search" autocomplete="off" placeholder="Title, author, or venue">
    </label>
    <label for="publication-type">Type
      <select id="publication-type">
        <option value="all">All types</option>
        <option value="journal">Journal articles</option>
        <option value="preprint">Preprints</option>
        <option value="other">Other</option>
      </select>
    </label>
    <label for="publication-year">Year
      <select id="publication-year">
        <option value="all">All years</option>
        {% for group in publication_years %}<option value="{{ group.name }}">{{ group.name }}</option>{% endfor %}
      </select>
    </label>
    <button id="publication-clear" type="button">Clear filters</button>
  </div>
  <p id="publication-count" class="publication-count" role="status" aria-live="polite"></p>
  <p id="publication-no-results" class="publication-no-results" hidden>No publications match these filters.</p>
  <div class="publication-years">
    {% for group in publication_years %}
    <section class="publication-year" data-year="{{ group.name }}" aria-labelledby="year-{{ group.name }}">
      <h2 id="year-{{ group.name }}">{{ group.name }}</h2>
      <div class="publication-year__list">
        {% for publication in group.items %}
          {% include publication-card.html publication=publication %}
        {% endfor %}
      </div>
    </section>
    {% endfor %}
  </div>
  <script src="{{ '/assets/js/publications.js' | relative_url }}" defer></script>
{% else %}
  <p class="publication-empty">Publication records are being prepared for review.</p>
{% endif %}
