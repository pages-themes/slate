---
layout: default
title: News & Updates
description: News, research updates, publications, and group activities from AutoDIAL.
---

<style>
.blog-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.blog-post {
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
  border: 1px solid rgba(234, 88, 12, 0.1);
  transition: all 0.3s ease;
}

.blog-post:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(234, 88, 12, 0.15);
  border-color: rgba(234, 88, 12, 0.2);
}

.blog-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #ea580c;
}

.blog-date {
  color: #ea580c;
  font-weight: 600;
  font-size: 0.9em;
}

.blog-title {
  color: #1f2937;
  font-size: 1.5em;
  font-weight: bold;
  margin: 0 0 1rem 0;
  line-height: 1.3;
}

.blog-title a {
  color: inherit;
  text-decoration: none;
  transition: color 0.3s ease;
}

.blog-title a:hover {
  color: #ea580c;
}

.blog-excerpt {
  color: #4b5563;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.read-more {
  display: inline-block;
  color: #ea580c;
  text-decoration: none;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border: 2px solid #ea580c;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.read-more:hover {
  background: #ea580c;
  color: white;
  transform: translateY(-1px);
}

.no-posts {
  text-align: center;
  color: #6b7280;
  font-style: italic;
  padding: 3rem;
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  border-radius: 12px;
  border: 1px solid rgba(234, 88, 12, 0.1);
}

.page-title {
  text-align: center;
  color: #1f2937;
  margin-bottom: 3rem;
  font-size: 2.5em;
}
</style>

<div class="blog-container">
  <h1 class="page-title">News & Updates</h1>
  
  {% if site.news.size > 0 %}
    {% assign sorted_news = site.news | sort: 'date' | reverse %}
    {% for post in sorted_news %}
      <article class="blog-post">
        <div class="blog-meta">
          <div class="blog-date">{{ post.date | date: "%B %d, %Y" }}</div>
        </div>
        <h2 class="blog-title">
          <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
        </h2>
        <div class="blog-excerpt">
          {% if post.excerpt %}
            {{ post.excerpt | strip_html | truncatewords: 50 }}
          {% else %}
            {{ post.content | strip_html | truncatewords: 50 }}
          {% endif %}
        </div>
        <a href="{{ post.url | relative_url }}" class="read-more">Read More</a>
      </article>
    {% endfor %}
  {% else %}
    <div class="no-posts">
      <h2>No posts yet</h2>
      <p>Stay tuned for updates on our latest research, publications, and group activities!</p>
    </div>
  {% endif %}
</div>
