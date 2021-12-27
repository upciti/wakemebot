# {{ component.name|capitalize }} - {{ component.package_count }} packages

{% for package in component.packages %}
## {% if package.homepage %}[{{ package.name }}]({{ package.homepage }}){% else %}{{ package.name }}{% endif %}

__{{ package.summary }}__

{{ package.description }}

{% for arch, versions in package.versions.items() %}
<span class="badge arch">{{ arch }}</span> {% for version in versions %}<span class="badge version">{{ version }}</span>{{ " " if not loop.last else "" }}{% endfor %}
{% endfor %}
{% endfor %}
