# Event-driven micro-batch pipeline; Lambda only where an S3 event exists

A box-side systemd timer extracts from Open Wearables every 6h into the S3 raw archive. An S3 `ObjectCreated` event triggers a Lambda (outside any VPC) that copies the file into a Unity Catalog Volume, and a Databricks file-arrival trigger runs the medallion job with `Trigger.AvailableNow`. Gold flows back the same way: Databricks writes Parquet snapshots to a Volume, and a box-side timer downloads them and reloads the Analysis Store. Open Wearables cannot run on Lambda, so the box exists anyway. A scheduled Lambda pulling Open Wearables would need Open Wearables exposed publicly or a NAT Gateway (~$32/mo), so extraction runs on the box instead.

## Considered Options

- Continuous streaming / webhooks to Lambda: rejected because it costs more and adds no value for data that reaches the cloud a few times per day.
- EventBridge Scheduler → Lambda → Open Wearables: rejected because of the public exposure or NAT cost described above.

## Consequences

- Each extraction re-pulls a rolling 3-day window and silver dedupes on natural key; no watermarks.
- Analysis Store reloads are truncate + reload per table (small data).
