param(
    [Parameter(Mandatory = $true)]
    [string]$Fichier,

    [Parameter(Mandatory = $true)]
    [string]$Sortie,

    [int]$Jours = 90,

    [datetime]$Date = (Get-Date)
)

$ErrorActionPreference = 'Stop'

try {
    # Vérifier que le fichier existe
    if (-not (Test-Path -LiteralPath $Fichier -PathType Leaf)) {
        throw "Fichier introuvable : $Fichier"
    }

    if ($Jours -lt 0) {
        throw "Le nombre de jours doit être positif ou nul."
    }

    # Lire les comptes et garder les humains actifs
    $comptes = Import-Csv -Path $Fichier -Delimiter ';' |
        Where-Object {
            $_.Type -eq 'Humain' -and $_.Actif -eq 'Oui'
        }

    # Calculer le nombre de jours depuis la dernière connexion
    $resultat = @(
        $comptes | ForEach-Object {
            $dernierLogon = [datetime]$_.DernierLogon

            [pscustomobject]@{
                Login        = $_.Login
                Service      = $_.Service
                JoursInactif = ($Date.Date - $dernierLogon.Date).Days
            }
        } |
        Where-Object {
            $_.JoursInactif -ge $Jours
        } |
        Sort-Object `
            @{ Expression = 'JoursInactif'; Descending = $true },
            @{ Expression = 'Login'; Descending = $false }
    )

    # Créer le dossier de destination si nécessaire
    $dossier = Split-Path -Parent $Sortie
    if ($dossier -and -not (Test-Path -LiteralPath $dossier)) {
        New-Item -ItemType Directory -Path $dossier -Force | Out-Null
    }

    # Exporter avec exactement les trois colonnes demandées
    if ($resultat.Count -gt 0) {
        $resultat |
            Select-Object Login, Service, JoursInactif |
            Export-Csv -Path $Sortie -Delimiter ';' -NoTypeInformation -Encoding utf8
    }
    else {
        Set-Content -Path $Sortie -Value '"Login";"Service";"JoursInactif"' -Encoding utf8
    }

    Write-Host "$($resultat.Count) compte(s) dormant(s) trouvé(s)."
}
catch {
    [Console]::Error.WriteLine("Erreur : $($_.Exception.Message)")
    exit 1
}
