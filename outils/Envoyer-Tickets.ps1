<#
.SYNOPSIS
    Script d'automatisation d'envoi de tickets d'incidents vers l'API Vigie (Jour 4).
.DESCRIPTION
    1. Récupère le jeton d'authentification (Variable d'environnement ou fichier .env).
    2. Interroge la route GET /tickets pour garantir l'idempotence (pas de doublons).
    3. Lit le fichier de non-conformités JSON fourni en argument.
    4. Envoie un ticket POST /tickets par poste non conforme (titre + poste obligatoires).
    5. Gère la limitation de débit HTTP 429 (Retry-After / Backoff) et HTTP 401 (exit 3).
#>

# ==============================================================================
# DECLARATION DES PARAMETRES
# ==============================================================================
# La clause [Parameter(Mandatory=$true)] rend l'argument -Fichier obligatoire.
# Si l'utilisateur lance le script sans -Fichier, PowerShell lui demandera de le saisir.
param(
    [Parameter(Mandatory=$true)]
    [string]$Fichier
)

# ==============================================================================
# 1. GESTION DU JETON ET DE L'URL DE L'API VIGIE (Exigence 1)
# ==============================================================================
# On tente d'abord de lire le jeton et l'URL depuis les variables d'environnement de la session.
$token = $env:VIGIE_TOKEN
$url = $env:VIGIE_URL

# Fallback : Si $VIGIE_TOKEN n'est pas défini dans l'environnement,
# on parse le fichier de configuration local /etc/mistral/vigie.env.
if (-not $token -and (Test-Path "/etc/mistral/vigie.env")) {
    $envLines = Get-Content "/etc/mistral/vigie.env"
    foreach ($line in $envLines) {
        # Extraction par expression régulière (Regex) en nettoyant les guillemets et espaces
        if ($line -match '^VIGIE_TOKEN=(.*)$') {
            $token = $matches[1].Trim("'", '"', "`r", " ")
        }
        if (-not $url -and $line -match '^VIGIE_URL=(.*)$') {
            $url = $matches[1].Trim("'", '"', "`r", " ")
        }
    }
}

# Si le jeton est toujours introuvable, on écrit une erreur sur STDERR et on quitte immédiatement avec le code 3.
if (-not $token) {
    [Console]::Error.WriteLine("erreur: VIGIE_TOKEN introuvable")
    exit 3
}

# URL par défaut si elle n'a pas été fournie dans le fichier .env
if (-not $url) {
    $url = "http://vigie.mistral.test:8080/api/v1"
}
# Suppression de tout slash final pour éviter des URLs malformées (ex: http://.../api/v1//tickets)
$url = $url.TrimEnd("/")


# ==============================================================================
# FONCTION AUXILIAIRE : APPEL HTTP ROBUSTE A L'API VIGIE (Exigences 1, 4)
# ==============================================================================
function Invoke-VigieApi {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [object]$Body = $null
    )

    # Entêtes HTTP requis pour s'authentifier auprès du reverse proxy / API Vigie
    $headers = @{
        "Authorization" = "Bearer $token"
        "X-Vigie-Token"  = $token
    }

    # Conversion de l'objet hashtable en chaîne JSON compacte si un corps est transmis
    $jsonBody = $null
    if ($Body) {
        $jsonBody = $Body | ConvertTo-Json -Depth 5 -Compress
        $headers["Content-Type"] = "application/json"
    }

    $attempt = 1
    $maxAttempts = 10

    # Boucle de réessai (Backoff) pour résister aux pannes réseau et limitations de débit (429)
    while ($true) {
        try {
            # SkipHttpErrorCheck=$true empêche Invoke-WebRequest de lever une exception
            # bloquante lors d'un code retour HTTP 4xx ou 5xx.
            $params = @{
                Uri                = $Uri
                Method             = $Method
                Headers            = $headers
                SkipHttpErrorCheck = $true
            }
            if ($jsonBody) {
                # Conversion du JSON en octets UTF-8 pour préserver les caractères accentués
                $params["Body"] = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
            }

            $response = Invoke-WebRequest @params
            $statusCode = [int]$response.StatusCode

            # --- CAS DE SUCCES (200 OK ou 201 Created) ---
            if ($statusCode -eq 200 -or $statusCode -eq 201) {
                if ($response.Content) {
                    return ($response.Content | ConvertFrom-Json)
                }
                return $null
            }
            # --- CAS JETON REFUSE (401 Unauthorized) ---
            elseif ($statusCode -eq 401) {
                [Console]::Error.WriteLine("jeton refusé")
                exit 3
            }
            # --- CAS LIMITATION DE DEBIT (429 Too Many Requests) ---
            elseif ($statusCode -eq 429) {
                # On recherche la présence de l'entête standard Retry-After envoyé par Vigie
                $retryAfter = $response.Headers["Retry-After"]
                $delay = 1
                if ($retryAfter -and [int]::TryParse($retryAfter, [ref]$delay)) {
                    # Si Retry-After indique un nombre de secondes, on respecte cette valeur
                } else {
                    # Sinon, calcul de délai exponentiel (1s, 2s, 4s, 8s, 16s...)
                    $delay = [math]::Pow(2, $attempt - 1)
                }
                Start-Sleep -Seconds $delay
                $attempt++
            }
            # --- AUTRES ERREURS SERVER / RESEAU (500, 503...) ---
            else {
                if ($attempt -ge $maxAttempts) {
                    [Console]::Error.WriteLine("Erreur HTTP $statusCode")
                    exit 1
                }
                $delay = [math]::Pow(2, $attempt - 1)
                Start-Sleep -Seconds $delay
                $attempt++
            }
        }
        catch {
            # Gestion des pannes de connexion au niveau socket/DNS
            if ($attempt -ge $maxAttempts) {
                [Console]::Error.WriteLine("Erreur connexion API: $_")
                exit 1
            }
            $delay = [math]::Pow(2, $attempt - 1)
            Start-Sleep -Seconds $delay
            $attempt++
        }
    }
}


# ==============================================================================
# 2. CHARGEMENT ET PARSING DU FICHIER JSON D'ENTREE
# ==============================================================================
if (-not (Test-Path $Fichier)) {
    [Console]::Error.WriteLine("Erreur: Fichier $Fichier introuvable")
    exit 1
}

# -Raw permet de lire l'intégralité du fichier comme un seul bloc de texte pour ConvertFrom-Json
$postesNonConformes = Get-Content $Fichier -Raw | ConvertFrom-Json

# Sécurité : Forcer le résultat sous forme de tableau @() même si le JSON n'a qu'un seul élément
if ($postesNonConformes -isnot [System.Array]) {
    $postesNonConformes = @($postesNonConformes)
}


# ==============================================================================
# 3. VERIFICATION DE L'IDEMPOTENCE (Exigence 3)
# ==============================================================================
# On interroge d'abord la route GET /tickets de Vigie pour connaître la liste
# des tickets déjà enregistrés sur le serveur avant d'effectuer le moindre envoi.
$responseTickets = Invoke-VigieApi -Uri "$url/tickets" -Method "GET"
$postesAvecTicket = @()

if ($responseTickets) {
    $listeTickets = $responseTickets
    if ($responseTickets.tickets) { $listeTickets = $responseTickets.tickets }

    # Extraction des noms de postes déjà couverts par un ticket
    foreach ($t in $listeTickets) {
        if ($t.poste) { $postesAvecTicket += $t.poste }
        elseif ($t.nom) { $postesAvecTicket += $t.nom }
    }
}


# ==============================================================================
# 4. CREATION ET ENVOI SANS DOUBLONS DES TICKETS (Exigences 2 & 3)
# ==============================================================================
$nouveauxTickets = 0

foreach ($item in $postesNonConformes) {
    # Normalisation du nom de machine (champ 'nom' ou 'poste')
    $nomPoste = $item.nom
    if (-not $nomPoste -and $item.poste) { $nomPoste = $item.poste }
    if (-not $nomPoste) { continue }

    # TEST D'IDEMPOTENCE : Si le poste est déjà présent dans la liste des tickets
    # ouverts sur Vigie, on saute cet élément pour éviter la création de doublons.
    if ($postesAvecTicket -contains $nomPoste) {
        Write-Host "Poste $nomPoste : ticket déjà présent (ignoré)."
        continue
    }

    # Récupération des raisons de non-conformité selon le schéma du JSON
    $raisons = $item.raisons
    if (-not $raisons -and $item.non_conformites) { $raisons = $item.non_conformites }
    if (-not $raisons -and $item.motifs) { $raisons = $item.motifs }

    # CONSTRUCTION DU PAYLOAD MANDATAIRE :
    # Vigie exige impérativement les champs 'poste' et 'titre'.
    $payload = @{
        poste   = $nomPoste
        titre   = "Non-conformité détectée sur $nomPoste"
        raisons = $raisons
    }

    # Envoi du ticket via POST
    $null = Invoke-VigieApi -Uri "$url/tickets" -Method "POST" -Body $payload
    Write-Host "Ticket créé avec succès pour le poste : $nomPoste"
    
    $nouveauxTickets++
    # Ajout dynamique au tableau local pour éviter de renvoyer si le JSON contient des doublons d'un même poste
    $postesAvecTicket += $nomPoste
}

# Message bilan final
Write-Host "Bilan : $nouveauxTickets nouveau(x) ticket(s) créé(s)."
