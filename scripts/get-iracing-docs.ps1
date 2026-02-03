param(
    [string]$AccessToken = $env:IRACING_ACCESS_TOKEN,
    [string]$BaseUrl = "https://members-ng.iracing.com",
    [string]$OutputDir = "iracing-docs"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TokenUrl = "https://oauth.iracing.com/oauth2/token"
$LegacyAuthUrl = "$BaseUrl/auth"
$WebSession = $null

function Get-RequiredEnvValue {
    param([string]$Name)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Missing required environment variable: $Name"
    }
    return $value
}

function Convert-ToMaskedSecret {
    param(
        [string]$Secret,
        [string]$Identifier
    )
    $normalizedId = $Identifier.Trim().ToLowerInvariant()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes("$Secret$normalizedId")
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha256.ComputeHash($bytes)
    } finally {
        $sha256.Dispose()
    }
    return [Convert]::ToBase64String($digest)
}

function Request-OAuthToken {
    param(
        [string]$ClientId,
        [string]$ClientSecret,
        [string]$Username,
        [string]$Password,
        [string]$RefreshToken
    )
    if (-not [string]::IsNullOrWhiteSpace($RefreshToken)) {
        $payload = @{
            grant_type = "refresh_token"
            client_id = $ClientId
            client_secret = (Convert-ToMaskedSecret $ClientSecret $ClientId)
            refresh_token = $RefreshToken
        }
    } elseif (-not [string]::IsNullOrWhiteSpace($Password)) {
        $payload = @{
            grant_type = "password_limited"
            username = $Username
            password = (Convert-ToMaskedSecret $Password $Username)
            client_id = $ClientId
            client_secret = (Convert-ToMaskedSecret $ClientSecret $ClientId)
            scope = "iracing.auth"
        }
    } else {
        throw "Missing IRACING_PASSWORD or IRACING_REFRESH_TOKEN for OAuth authentication."
    }

    return Invoke-RestMethod -Method Post -Uri $TokenUrl -Body $payload -ContentType "application/x-www-form-urlencoded"
}

function Request-LegacySession {
    param(
        [string]$Username,
        [string]$Password
    )
    if ([string]::IsNullOrWhiteSpace($Password)) {
        throw "Missing IRACING_PASSWORD for legacy authentication."
    }
    $payload = @{
        email = $Username
        password = $Password
    } | ConvertTo-Json
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    Invoke-RestMethod -Method Post -Uri $LegacyAuthUrl -Body $payload -ContentType "application/json" -WebSession $session | Out-Null
    return $session
}

if ([string]::IsNullOrWhiteSpace($AccessToken)) {
    $clientId = Get-RequiredEnvValue "IRACING_CLIENT_ID"
    $clientSecret = Get-RequiredEnvValue "IRACING_CLIENT_SECRET"
    $username = Get-RequiredEnvValue "IRACING_USERNAME"
    $password = [Environment]::GetEnvironmentVariable("IRACING_PASSWORD")
    $refreshToken = [Environment]::GetEnvironmentVariable("IRACING_REFRESH_TOKEN")

    try {
        $tokenResponse = Request-OAuthToken -ClientId $clientId -ClientSecret $clientSecret -Username $username -Password $password -RefreshToken $refreshToken
        $AccessToken = $tokenResponse.access_token
        if ([string]::IsNullOrWhiteSpace($AccessToken)) {
            throw "OAuth token response did not include an access_token."
        }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($statusCode -ne 405) {
            throw
        }
        Write-Warning "OAuth token request returned HTTP 405. Falling back to legacy auth endpoint."
        $WebSession = Request-LegacySession -Username $username -Password $password
    }
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
    if (-not [string]::IsNullOrWhiteSpace($AccessToken)) {
        return Invoke-RestMethod -Method Get -Uri $url -Headers @{
            Authorization = "Bearer $AccessToken"
            Accept = "application/json"
        }
    }
    if ($null -ne $WebSession) {
        return Invoke-RestMethod -Method Get -Uri $url -WebSession $WebSession -Headers @{
            Accept = "application/json"
        }
    }
    throw "No authentication available. Provide -AccessToken or set OAuth environment variables."
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
