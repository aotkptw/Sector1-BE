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

## iRacing API Documentation

The iRacing API exposes documentation via `/data/doc`. Provide your OAuth access token
as a Bearer token to retrieve the root documentation or a specific service/method.

```bash
curl --fail \
  -H "Authorization: Bearer ${IRACING_ACCESS_TOKEN}" \
  "https://members-ng.iracing.com/data/doc"
```

To fetch a service page (for example, `car`) or a specific method (for example,
`car/assets`), append the path:

```bash
curl --fail \
  -H "Authorization: Bearer ${IRACING_ACCESS_TOKEN}" \
  "https://members-ng.iracing.com/data/doc/car"
```

```bash
curl --fail \
  -H "Authorization: Bearer ${IRACING_ACCESS_TOKEN}" \
  "https://members-ng.iracing.com/data/doc/car/assets"
```

If you want to use the Python client helpers, build an API instance with your access
token and call `get_documentation`:

```python
from iracing_api import build_api

api = build_api("your-access-token")
doc = api.get_documentation("car/assets")
print(doc)
```

To download all documentation pages with PowerShell, run (PowerShell 7+):

```powershell
pwsh ./scripts/get-iracing-docs.ps1 -AccessToken $env:IRACING_ACCESS_TOKEN -OutputDir ./iracing-docs
```

If `pwsh` is not available, use Windows PowerShell 5.1 instead (note the path format):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\get-iracing-docs.ps1 -AccessToken $env:IRACING_ACCESS_TOKEN -OutputDir .\iracing-docs
```

If you are using an absolute path on Windows, do not prefix it with `.\`:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\julia\Sector1-BE\Sector1-BE-main\scripts\get-iracing-docs.ps1 -AccessToken $env:IRACING_ACCESS_TOKEN -OutputDir C:\Users\julia\Sector1-BE\Sector1-BE-main\iracing-docs
```

## Notes

* The OAuth password-limited client scope is restricted to `julian.m.colbert@gmail.com`.
* If `IRACING_REFRESH_TOKEN` is set, the exporter will use the refresh grant before falling back to the password-limited grant.
* The iRacing OAuth service requires masking of the client secret and user password before submission; the exporter handles this automatically.
