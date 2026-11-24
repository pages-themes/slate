---
layout: default
title: Software
description: Explore open-source scientific software developed by the AutoDIAL research group.
---

<header class="software-intro">
  <p class="eyebrow">Open-source tools</p>
  <h1>Software</h1>
  <p>Scientific software developed by the AutoDIAL group. Explore each tool through its documentation, source code, and related publication where available.</p>
</header>

<div class="software-list">
  {% for software in site.data.software.packages %}
    {% include software-card.html software=software %}
  {% endfor %}
</div>
