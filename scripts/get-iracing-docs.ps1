param(
    [string]$AccessToken = $env:IRACING_ACCESS_TOKEN,
    [string]$BaseUrl = "https://members-ng.iracing.com",
    [string]$OutputDir = "iracing-docs"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AccessToken)) {
    throw "Access token missing. Provide -AccessToken or set IRACING_ACCESS_TOKEN."
}

function Normalize-DocPath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }
    return $Path.Trim("/")
}

function Get-DocUrl {
    param([string]$DocPath)
    $normalized = Normalize-DocPath $DocPath
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return "$BaseUrl/data/doc"
    }
    return "$BaseUrl/data/doc/$normalized"
}

function Invoke-DocRequest {
    param([string]$DocPath)
    $url = Get-DocUrl $DocPath
    Write-Host "Fetching $url"
    return Invoke-RestMethod -Method Get -Uri $url -Headers @{
        Authorization = "Bearer $AccessToken"
        Accept = "application/json"
    }
}

function Save-DocJson {
    param(
        [string]$DocPath,
        $Doc
    )
    $normalized = Normalize-DocPath $DocPath
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        $targetPath = Join-Path $OutputDir "root"
    } else {
        $targetPath = Join-Path $OutputDir ($normalized -replace "/", [IO.Path]::DirectorySeparatorChar)
    }
    $targetDir = Split-Path $targetPath -Parent
    if (-not [string]::IsNullOrWhiteSpace($targetDir) -and -not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    $targetFile = "$targetPath.json"
    $Doc | ConvertTo-Json -Depth 20 | Set-Content -Path $targetFile -Encoding utf8
}

function Get-StringValues {
    param($Value)
    $results = New-Object System.Collections.Generic.List[string]
    if ($null -eq $Value) {
        return $results
    }
    if ($Value -is [string]) {
        $results.Add($Value)
        return $results
    }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($entry in $Value.GetEnumerator()) {
            foreach ($item in Get-StringValues $entry.Value) {
                $results.Add($item)
            }
        }
        return $results
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        foreach ($item in $Value) {
            foreach ($nested in Get-StringValues $item) {
                $results.Add($nested)
            }
        }
    }
    return $results
}

function Convert-ToDocPath {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }
    $match = [regex]::Match($Value, '/data/doc(?:/([^\s"''<>?#]+))?', 'IgnoreCase')
    if ($match.Success) {
        $path = $match.Groups[1].Value
        return Normalize-DocPath $path
    }
    return $null
}

function Get-DocChildren {
    param(
        [string]$CurrentPath,
        $Doc
    )
    $children = New-Object System.Collections.Generic.List[string]
    if ($null -eq $Doc) {
        return $children
    }

    $serviceName = $null
    if ($Doc.PSObject.Properties.Match("service").Count -gt 0) {
        $serviceName = $Doc.service
    }

    if ($Doc.PSObject.Properties.Match("services").Count -gt 0 -and $Doc.services) {
        foreach ($service in $Doc.services) {
            $name = $service.name
            if ([string]::IsNullOrWhiteSpace($name)) {
                $name = $service.service
            }
            if (-not [string]::IsNullOrWhiteSpace($name)) {
                $children.Add((Normalize-DocPath $name))
            }
        }
    }

    if ($Doc.PSObject.Properties.Match("methods").Count -gt 0 -and $Doc.methods) {
        foreach ($method in $Doc.methods) {
            $methodName = $method.name
            if ([string]::IsNullOrWhiteSpace($methodName)) {
                continue
            }
            if (-not [string]::IsNullOrWhiteSpace($serviceName)) {
                $children.Add((Normalize-DocPath "$serviceName/$methodName"))
            } elseif (-not [string]::IsNullOrWhiteSpace($CurrentPath)) {
                $children.Add((Normalize-DocPath "$CurrentPath/$methodName"))
            }
        }
    }

    foreach ($stringValue in Get-StringValues $Doc) {
        $path = Convert-ToDocPath $stringValue
        if ($null -ne $path) {
            $children.Add($path)
        }
    }

    return $children
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$queue = New-Object System.Collections.Generic.Queue[string]
$visited = New-Object System.Collections.Generic.HashSet[string] ([StringComparer]::OrdinalIgnoreCase)
$queue.Enqueue("")

while ($queue.Count -gt 0) {
    $path = $queue.Dequeue()
    $normalized = Normalize-DocPath $path
    if (-not $visited.Add($normalized)) {
        continue
    }

    $doc = Invoke-DocRequest $normalized
    Save-DocJson $normalized $doc

    foreach ($child in Get-DocChildren $normalized $doc) {
        $childPath = Normalize-DocPath $child
        if (-not $visited.Contains($childPath)) {
            $queue.Enqueue($childPath)
        }
    }
}

Write-Host "Saved documentation to $OutputDir"
