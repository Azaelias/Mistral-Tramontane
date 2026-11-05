<#
.SYNOPSIS
    Exécute un audit de conformité du parc informatique.
.DESCRIPTION
    Analyse un fichier JSON de postes, évalue leur conformité selon plusieurs critères (Build, Defender, Disque, Mise à jour) et exporte les résultats sous forme de CSV et JSON.
.AUTHOR
    HAMMOUD Mouhamed
.PARAMETER Fichier
    Chemin vers le fichier source JSON contenant les données du parc (obligatoire).
.PARAMETER Sortie
    Dossier de destination pour enregistrer les rapports d'audit (obligatoire).
.PARAMETER Seuil
    Pourcentage maximal d'utilisation du disque toléré (défaut : 90).
.PARAMETER JoursMaj
    Nombre maximal de jours toléré depuis la dernière mise à jour (défaut : 30).
.PARAMETER BuildMin
    Numéro de build minimal requis pour le système d'exploitation (défaut : 19045).
.PARAMETER Date
    Date de référence pour calculer l'ancienneté des mises à jour (défaut : aujourd'hui).
.EXAMPLE
pwsh -NoProfile -File outils/Audit-Parc.ps1 -Fichier /srv/mistral/parc/postes.json -Sortie /tmp/audit80 - Date 2026-11-05 -Seuil 80

#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Fichier,

    [Parameter(Mandatory = $true)]
    [string]$Sortie,

    [int]$Seuil = 90,
    [int]$JoursMaj = 30,
    [int]$BuildMin = 19045,
    [datetime]$Date = (Get-Date)
)

# 1. Vérification et création du dossier de sortie si absent
if (-not (Test-Path $Sortie)) {
    New-Item -ItemType Directory -Path $Sortie | Out-Null
}

# 2. Chargement et parsing du fichier JSON du parc
$postes = Get-Content -Raw $Fichier | ConvertFrom-Json

$resultatsNonConformes = foreach ($p in $postes) {
    $raisons = @()

    # Règle 1 : Build inférieur à BuildMin
    if ($p.build -lt $BuildMin) {
        $raisons += "build"
    }

    # Règle 2 : Antivirus Defender désactivé (false ou absent)
    if (-not $p.defender) {
        $raisons += "defender"
    }

    # Règle 3 : Disque strictement au-dessus du Seuil
    if ($p.disque_pct -gt $Seuil) {
        $raisons += "disque"
    }

    # Règle 4 : Dernière mise à jour il y a plus de JoursMaj jours à la Date de référence
    if ($p.derniere_maj) {
        $ageJours = ($Date - [datetime]$p.derniere_maj).Days
        if ($ageJours -gt $JoursMaj) {
            $raisons += "maj"
        }
    } else {
        $raisons += "maj"
    }

    # Si le poste présente au moins une non-conformité
    if ($raisons.Count -gt 0) {
        [PSCustomObject]@{
            nom     = $p.nom
            site    = $p.site
            raisons = $raisons # Tableau pour le JSON, joint en chaîne pour le CSV
        }
    }
}

# Tri des postes non conformes par ordre alphabétique du nom
$resultatsTries = $resultatsNonConformes | Sort-Object nom

# 3. Exportation au format JSON (liste d'objets avec "raisons" en liste)
$cheminJson = Join-Path $Sortie "non-conformes.json"
ConvertTo-Json -InputObject @($resultatsTries) -Depth 5 | Set-Content -Path $cheminJson -Encoding utf8
#$resultatsTries | ConvertTo-Json -Depth 5 | Set-Content -Path $cheminJson -Encoding utf8

# 4. Exportation au format CSV (séparateur ;, colonnes nom;site;raisons jointes par |)
$cheminCsv = Join-Path $Sortie "non-conformes.csv"

# Construction manuelle ou formatée des lignes CSV pour garantir le séparateur '|' pour les raisons
$lignesCsv = @("nom;site;raisons")
foreach ($poste in $resultatsTries) {
    $raisonsString = $poste.raisons -join "|"
    $lignesCsv += "$($poste.nom);$($poste.site);$raisonsString"
}
$lignesCsv | Set-Content -Path $cheminCsv -Encoding utf8

Write-Host "Audit terminé avec succès. Rapports générés dans : $Sortie" -ForegroundColor Green
