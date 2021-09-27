import re
from typing import Literal

from pydantic import BaseModel, Field

GIT_MESSAGE_RE = re.compile(
    r"^\* (?P<verb>\w+) (?P<name>\w+) (?:to )?v(?P<version>[\w\.]+)$"
)


class Entry(BaseModel):
    verb: Literal["Update", "Add", "Remove"]
    name: str = Field(regex=r"[a-z0-9]+")
    version: str = Field(regex=r"[a-z0-9]+")


def parse_line(line: str) -> Entry:
    if (m := GIT_MESSAGE_RE.match(line)) is None:
        raise ValueError(f'Unable to parse line "{line}"')
    return Entry.parse_obj(m.groupdict())


def parse_commit_message(message):
    for line in message.split("\n")[2:]:
        if line:
            yield parse_line(line)
