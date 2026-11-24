---
layout: default
title: News & Updates
description: News, research updates, publications, and group activities from AutoDIAL.
---


<div class="news-feed">
  <header class="news-feed__heading">
    <p class="eyebrow">From the lab</p>
    <h1>News & Updates</h1>
    <p>Research updates and publication announcements from AutoDIAL. Publication links lead to the paper and its full citation.</p>
  </header>

  {% assign all_news = site.news | sort: 'month' | reverse %}
  {% for item in all_news %}
    {% if item.kind == 'publication' %}
      {% assign paper = site.data.publications | where: 'doi', item.doi | first %}
      {% if paper and paper.type == 'journal' %}
        {% include publication-news-card.html item=item paper=paper %}
      {% endif %}
    {% else %}
      <article class="news-card news-card--post" id="news-{{ item.slug }}">
        <time datetime="{{ item.month }}">{{ item.month | append: '-01' | date: '%B %Y' }}</time>
        <h2 class="news-card__title"><a href="{{ item.url | relative_url }}">{{ item.title }}</a></h2>
        <p class="news-card__description">{{ item.excerpt | default: item.content | strip_html | truncatewords: 50 }}</p>
        <a class="text-link" href="{{ item.url | relative_url }}">Read post <span aria-hidden="true">→</span></a>
      </article>
    {% endif %}
  {% endfor %}
</div>

<script src="{{ '/assets/js/news.js' | relative_url }}" defer></script>
