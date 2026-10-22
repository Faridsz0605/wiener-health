# AWS hosts services, Databricks Free Edition hosts the lakehouse

AWS (our account) hosts Open Wearables, the extraction functions, the S3 raw archive and the Analysis Store; Databricks Free Edition hosts lakehouse compute and Unity Catalog. We chose Free Edition for zero lakehouse cost on a portfolio project, accepting its limits; S3 stays the source of truth so the lakehouse can be rebuilt or moved to paid Databricks-on-AWS later.

## Consequences

- Free Edition outbound internet is restricted, so Databricks cannot pull from or push to our AWS services. Data is pushed into a Unity Catalog Volume, and gold data is pulled out by AWS-side code.
- Serverless streaming supports only `Trigger.AvailableNow`, so medallion processing is micro-batch.
- Daily compute quota can shut the workspace down until reset; S3 keeps landing data meanwhile, and the next run catches up.
- Free Edition is non-commercial use only.
