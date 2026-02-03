# iRacing Session Exporter

This project exports iRacing session results into a CSV suitable for league administration workflows.

## Environment Variables

Set the following environment variables before running the exporter:

```bash
export IRACING_CLIENT_ID="your-client-id"
export IRACING_CLIENT_SECRET="your-client-secret"
export IRACING_USERNAME="your-iracing-username"
export IRACING_PASSWORD="your-iracing-password"
```

## Usage

```bash
python src/iracing_exporter.py --session-id 123456 --output results.csv
```

Additional options:

```bash
python src/iracing_exporter.py --session-id 123456 --output results.csv --format csv --verbose
```

To validate the CLI without contacting iRacing:

```bash
python src/iracing_exporter.py --session-id 123456 --output results.csv --dry-run
```

## Notes

* The OAuth password-limited client scope is restricted to `julian.m.colbert@gmail.com`.
