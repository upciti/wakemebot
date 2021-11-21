# {{ component.name|capitalize }} - {{ component.package_count }} packages

{% for package in component.packages %}
## {{ package.name }}

{{ package.description }}

<span class="badge arch">amd64</span> {% for version in package.versions|map(attribute="upstream_version") %}<span class="badge version">{{ version }}</span> {% endfor %}
{% endfor %}