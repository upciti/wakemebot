from pathlib import Path

from jinja2 import Environment

environment = Environment()

IMAGE = """\
data:image/png;base64,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
"""

TEMPLATE_SVG = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    width="{{badge_width}}"
    height="20"
>
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <mask id="0">
        <rect width="{{badge_width}}" height="20" rx="3" fill="#fff"/>
    </mask>
    <g mask="url(#0)">
        <path fill="{{label_color}}" d="M0 0h{{split_x}}v20H0z"/>
        <path fill="{{value_color}}" d="M{{split_x}} 0h{{value_width}}v20H{{split_x}}z"/>
        <path fill="url(#b)" d="M0 0h{{badge_width}}v20H0z"/>
    </g>
    <image
        x="{{image_padding}}"
        y="4"
        width="{{image_width}}"
        height="15"
        xlink:href="{{image}}"
    />
    <g fill="{{text_color}}" text-anchor="middle" font-family="{{font}}" font-size="11">
        <text x="{{value_x+1}}" y="15" fill="#010101" fill-opacity=".3">{{value}}</text>
        <text x="{{value_x}}" y="14">{{value}}</text>
    </g>
</svg>"""


class Badge:
    def __init__(self, version: str) -> None:
        self.label_width = 80
        self.image_padding = 8
        self.image_width = self.label_width - 2 * self.image_padding
        self.value = f"v{version}"
        self.value_width = int(len(self.value) * 7)
        self.badge_width = self.label_width + self.value_width
        self.value_x = self.badge_width - self.value_width / 2
        self.split_x = self.badge_width - self.value_width

    def generate(self) -> str:
        template = environment.from_string(TEMPLATE_SVG)
        return template.render(
            image=IMAGE,
            label_color="#414288",
            value_color="#a63df9",
            text_color="white",
            font="DejaVu Sans,Verdana,Geneva,sans-serif",
            **self.__dict__,
        )

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(exist_ok=True, parents=True)
        output_path.write_text(self.generate())


if __name__ == "__main__":
    Badge("10.9.123").save(Path("ops2deb.svg"))
