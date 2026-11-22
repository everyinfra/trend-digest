# n8n workflows

Two small workflows that use only built-in n8n nodes (Schedule Trigger, Set, HTTP Request, Code).
They do not need this repository's Python code.

| File | What it does | Calls | Cost |
| --- | --- | --- | --- |
| `github-trending-to-discord.json` | Once a day, posts the top 5 GitHub trending repositories as one Discord embed. | 1 per day | about $0.02 a month |
| `subreddit-new-posts-to-discord.json` | Every 15 minutes, posts new posts from one subreddit. The first run only remembers what is there. | 96 per day | about $1.61 a month |

Prices are per 1,000 calls: $0.81 for `github/trending`, $0.56 for `reddit/subreddit_posts`.
Calls that return no data are not charged. Current prices: https://everyinfra.com/pricing

## Import

1. In n8n, open **Workflows > Add workflow**, then the **...** menu > **Import from File**, and pick one of the JSON files.
   You can also copy the file's content and paste it onto an empty canvas.
2. Get an EveryInfra API key: https://everyinfra.com/?utm_source=n8n-template
3. Open the HTTP Request node that calls EveryInfra. Under **Credential for Header Auth**, create a new credential:
   - Name: `Authorization`
   - Value: `Bearer YOUR_KEY`
4. In Discord, open the channel settings > **Integrations** > **Webhooks** > **New Webhook** > **Copy Webhook URL**.
5. Open the **Settings** node and paste the webhook URL into `discord_webhook_url`.
   For the subreddit workflow, also set `subreddit` (without `r/`).
6. Click **Execute workflow** once to check it, then switch the workflow to **Active**.

## Notes

- The subreddit workflow remembers post ids with workflow static data. n8n saves static data only
  when the workflow runs from its trigger while active, not during manual test runs. So the
  "first run only records" step happens on the first active run.
- Treat the Discord webhook URL like a password. Anyone who has it can post to your channel.
  If it leaks, delete the webhook in Discord and create a new one.
- Messages are sent with `allowed_mentions: { parse: [] }`, so nobody is pinged.
- To post somewhere other than Discord, change the Code node to build that service's message and
  point the last HTTP Request node at its webhook.
