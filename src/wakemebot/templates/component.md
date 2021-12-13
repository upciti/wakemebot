# {{ component.name|capitalize }} - {{ component.package_count }} packages

{% for package in component.packages %}
## {% if package.homepage %}[{{ package.name }}]({{ package.homepage }}){% else %}{{ package.name }}{% endif %}

__{{ package.summary }}__

{{ package.description }}

<span class="badge arch">amd64</span> {% for version in package.versions %}<span class="badge version">{{ version }}</span>{{ " " if not loop.last else "" }}{% endfor %}
{% endfor %}
