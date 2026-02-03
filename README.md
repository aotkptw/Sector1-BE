# iRacing Session Exporter

This project exports iRacing session results into a CSV suitable for league administration workflows.

## Environment Variables

Set the following environment variables before running the exporter:

```bash
export IRACING_CLIENT_ID="your-client-id"
export IRACING_CLIENT_SECRET="your-client-secret"
export IRACING_USERNAME="your-iracing-username"
export IRACING_PASSWORD="your-iracing-password"
export IRACING_REFRESH_TOKEN="your-refresh-token"
```

## Usage

```bash
python src/iracing_exporter.py --session-id 123456 --output results.csv
```

To export league data, provide a league id, season id, and dataset:

```bash
python src/iracing_exporter.py --league-id 98765 --season-id 2024 --league-data team-standings --output league_team_standings.csv
```

Available league datasets:

* `team-standings`
* `driver-standings` (overall)
* `pro-standings`
* `am-standings`
* `nation-standings`
* `points`
* `calendar` (race calendar with top-three positions)
* `all` (all league datasets in one CSV)

To export all league datasets into one CSV:

```bash
python src/iracing_exporter.py --league-id 98765 --season-id 2024 --league-data all --output league_all.csv
```

Additional options:

```bash
python src/iracing_exporter.py --session-id 123456 --output results.csv --format csv --verbose
```

To validate the CLI without contacting iRacing:

```bash
python src/iracing_exporter.py --session-id 123456 --output results.csv --dry-run
```

## Windows PowerShell

On Windows, you can run the same command via Windows PowerShell:

```powershell
powershell -Command "python src/iracing_exporter.py --session-id 123456 --output results.csv --dry-run"
```

## Troubleshooting

If you see a `SyntaxError` that references a line starting with `index` (for example,
`index 31bd26...`), the Python file likely contains a pasted git diff header. Re-download
the project archive or open the file and remove the stray diff header lines before
running the exporter.

## Notes

* The OAuth password-limited client scope is restricted to `julian.m.colbert@gmail.com`.
* If `IRACING_REFRESH_TOKEN` is set, the exporter will use the refresh grant before falling back to the password-limited grant.
* The iRacing OAuth service requires masking of the client secret and user password before submission; the exporter handles this automatically.
