"""Turn a message into each channel's request body.

A "message" is the channel-neutral form of one digest post:

    {"lang", "title", "subtitle", "sections": [{"id", "label", "icon_url", "items"}],
     "footer", "site_url"}

Each module here has `render(message) -> dict` (one request body). When a body
would be over the channel's size limit, items are removed from the end of the
sections until it fits (see `common.shrink_until`).
"""

from . import dingtalk, discord, feishu, slack, telegram, wecom

RENDERERS = {
    "discord": discord.render,
    "slack": slack.render,
    "telegram": telegram.render,
    "feishu": feishu.render,
    "dingtalk": dingtalk.render,
    "wecom": wecom.render,
}
CHANNELS = tuple(RENDERERS)


def render_payloads(messages):
    """{channel: [body for each message]} for every channel."""
    return {channel: [render(message) for message in messages] for channel, render in RENDERERS.items()}
