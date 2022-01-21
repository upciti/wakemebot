COMPONENT_PACKAGE_LIST = """\
# {{ component.name|capitalize }} - {{ component.package_count }} packages

{% for package in component.packages %}
## {% if package.homepage %}[{{ package.name }}]({{ package.homepage }}){% else %}{{ package.name }}{% endif %}

__{{ package.summary[0]|upper}}{{package.summary[1:] }}__

{{ package.description|replace("\n.\n", "\n\n") }}

{% for arch, versions in package.versions.items() %}
<div><span class="badge arch">{{ arch }}</span> {% for version in versions %}<span class="badge version">{{ version }}</span>{{ " " if not loop.last else "" }}{% endfor %}</div>
{% endfor %}
{% endfor %}
"""
