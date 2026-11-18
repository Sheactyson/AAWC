[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$mod = Join-Path $root 'mod\AGOT_Alternate_World_Compatch'

function Assert-That {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Read-Source([string]$RelativePath) {
    Get-Content -LiteralPath (Join-Path $mod $RelativePath) -Raw -Encoding utf8
}

function Stage4-Cost([int]$Slots, [int]$PerSlot) {
    [Math]::Max(1, $Slots) * $PerSlot
}

function New-BlockerTransaction([int]$Cost) {
    [pscustomobject]@{ Cost = $Cost; Reserved = 0; State = 'none'; Consumed = 0 }
}

function Reserve-BlockerTransaction($Transaction) {
    if ($Transaction.State -eq 'none') {
        $Transaction.Reserved += $Transaction.Cost
        $Transaction.State = 'reserved'
    }
}

function Cancel-BlockerTransaction($Transaction) {
    if ($Transaction.State -eq 'reserved') {
        $Transaction.Reserved -= $Transaction.Cost
        $Transaction.State = 'cancelled'
    }
}

function Complete-BlockerTransaction($Transaction) {
    if ($Transaction.State -eq 'reserved') {
        $Transaction.Reserved -= $Transaction.Cost
        $Transaction.Consumed += $Transaction.Cost
        $Transaction.State = 'consumed'
    }
}

# Cost scaling: the one-slot floor applies independently of whether the
# de-jure hierarchy is temporarily empty or a normal county has many slots.
Assert-That ((Stage4-Cost 0 250) -eq 250) 'wilderness zero-slot floor must be 250'
Assert-That ((Stage4-Cost 1 250) -eq 250) 'wilderness one-slot cost must be 250'
Assert-That ((Stage4-Cost 4 250) -eq 1000) 'wilderness must scale 250 per slot'
Assert-That ((Stage4-Cost 0 500) -eq 500) 'ruin zero-slot floor must be 500'
Assert-That ((Stage4-Cost 1 500) -eq 500) 'ruin one-slot cost must be 500'
Assert-That ((Stage4-Cost 4 500) -eq 2000) 'ruin must scale 500 per slot'

$values = Read-Source 'common\script_values\aawc_population_values.txt'
Assert-That ($values -match '@aawc_stage4_wilderness_colonization_cost_per_slot = 250') 'missing central wilderness per-slot policy'
Assert-That ($values -match '@aawc_stage4_ruin_reclamation_cost_per_slot = 500') 'missing central ruin per-slot policy'
foreach ($policy in @(
    @{ Route = 'wilderness_colonization'; Constant = 'aawc_stage4_wilderness_colonization_cost_per_slot' },
    @{ Route = 'ruin_reclamation'; Constant = 'aawc_stage4_ruin_reclamation_cost_per_slot' }
)) {
    $formula = [regex]::Match($values, "(?s)aawc_stage4_$($policy.Route)_population_cost\s*=\s*\{(.*?)\n\}")
    Assert-That ($formula.Success) "missing $($policy.Route) population formula"
    Assert-That ($formula.Groups[1].Value -match "multiply\s*=\s*@$($policy.Constant)") "$($policy.Route) must scale by its central per-slot constant"
    Assert-That ($formula.Groups[1].Value -match "min\s*=\s*@$($policy.Constant)") "$($policy.Route) must enforce its one-slot floor after scaling"
}
foreach ($route in 'wilderness_colonization', 'ruin_reclamation') {
    foreach ($resource in 'population', 'gold', 'prestige', 'piety') {
        Assert-That ($values -match "aawc_stage4_${route}_${resource}_cost\s*=\s*\{") "missing centralized $route $resource cost"
    }
}

$payment = Read-Source 'common\scripted_effects\zzzz_aawc_stage4_colonization_currency_effects.txt'
Assert-That ($payment -match 'remove_short_term_gold = \$GOLD\$') 'central payment must charge gold'
Assert-That ($payment -match 'add_prestige') 'central payment must charge prestige'
Assert-That ($payment -match 'add_piety') 'central payment must charge piety'
Assert-That ($payment -match 'aawc_stage4_pay_colonization_legitimacy_resources_effect') 'direct AGOT route needs the no-double-gold legitimacy payment primitive'

$triggers = Read-Source 'common\scripted_triggers\aawc_population_triggers.txt'
foreach ($trigger in 'aawc_stage4_can_fund_wilderness_colonization', 'aawc_stage4_can_fund_ruin_reclamation') {
    $start = $triggers.IndexOf("$trigger = {")
    Assert-That ($start -ge 0) "missing $trigger"
    $body = $triggers.Substring($start, [Math]::Min(650, $triggers.Length - $start))
    foreach ($resource in 'gold', 'prestige', 'piety') {
        Assert-That ($body -match "(?m)^\s*$resource\s+>=") "$trigger must require $resource"
    }
}

# The two direct AGOT entry points keep their lifecycle code but may not retain
# independent price numbers.  The native colonization effect owns the single
# gold debit; its companion effect debits prestige and piety exactly once.
$ruinGui = Read-Source 'common\scripted_guis\zz_agot_ruins_override.txt'
Assert-That ($ruinGui -match 'aawc_stage4_can_fund_ruin_reclamation = yes') 'direct ruin GUI must use the central currency gate'
Assert-That ($ruinGui -match 'aawc_stage4_can_fund_wilderness_colonization = yes') 'direct wilderness GUI must use the central currency gate'
Assert-That ($ruinGui -match '(?s)Stage 4 central pricing supersedes.*limit = \{ always = yes \}.*aawc_stage4_can_fund_ruin_reclamation = yes.*trigger_else_if') 'direct ruin affordability must bypass the retained site-specific compatibility table'
Assert-That ($ruinGui -match '(?s)limit = \{ always = yes \}.*aawc_stage4_pay_colonization_resources_effect.*GOLD = scope:ruin.county.aawc_stage4_ruin_reclamation_gold_cost.*else_if') 'direct ruin completion must bypass legacy debits and charge the centralized three-resource amount once'

$agotColonization = Read-Source 'common\scripted_effects\lv_agot_scripted_effect_overrides.txt'
Assert-That ($agotColonization -notmatch '\bcolonize_cost_val\b') 'native colonization effect retains a separate gold cost'
Assert-That (($agotColonization | Select-String -Pattern 'aawc_stage4_wilderness_colonization_gold_cost' -AllMatches).Matches.Count -ge 3) 'native colonization gold payment must use the central wilderness cost in every branch'
Assert-That (($agotColonization | Select-String -Pattern 'aawc_stage4_pay_colonization_legitimacy_resources_effect' -AllMatches).Matches.Count -eq 1) 'native colonization must charge prestige/piety exactly once'

$lovStart = Read-Source 'common\on_action\LV\ruin_restoration_on_actions\lv_settlement_on_actions.txt'
foreach ($route in 'wilderness_colonization', 'ruin_reclamation') {
    foreach ($resource in 'gold', 'prestige', 'piety') {
        Assert-That ($lovStart -match "aawc_stage4_${route}_${resource}_cost") "LoV $route start omits $resource"
    }
}
Assert-That (($lovStart | Select-String -Pattern 'aawc_stage4_pay_colonization_resources_effect' -AllMatches).Matches.Count -eq 2) 'LoV must have one complete resource payment per route'

# The county-view cache must classify wilderness separately from ruins.  A
# rendered six-slot Russeting probe exposed the former unconditional ruin-cost
# assignment as 3,000 gold beside the correct 1,500 population cost.
$settlementGui = Read-Source 'common\scripted_guis\lv_ruin_restoration_scripted_gui.txt'
$tooltipCache = [regex]::Match($settlementGui, '(?s)lv_restore_ruins_tooltip_show\s*=\s*\{(.*?)\n\}')
Assert-That $tooltipCache.Success 'missing LoV county-view tooltip cache'
Assert-That ($tooltipCache.Groups[1].Value -match 'has_holding_type\s*=\s*wilderness_holding') 'county-view tooltip cache must branch on wilderness holdings'
foreach ($route in 'wilderness_colonization', 'ruin_reclamation') {
    foreach ($resource in 'gold', 'prestige', 'piety') {
        Assert-That ($tooltipCache.Groups[1].Value -match "aawc_stage4_${route}_${resource}_cost") "county-view tooltip cache omits $route $resource pricing"
    }
}
$populationLoc = Read-Source 'localization\english\aawc_population_l_english.yml'
foreach ($tooltip in 'aawc_population_reclaim_button_tooltip', 'aawc_population_colonize_button_tooltip', 'aawc_population_reclaim_button_blocked_tooltip', 'aawc_population_colonize_button_blocked_tooltip') {
    $line = [regex]::Match($populationLoc, "(?m)^ ${tooltip}:0 .*`$")
    Assert-That $line.Success "missing $tooltip localization"
    foreach ($resource in 'gold', 'prestige', 'piety') {
        Assert-That ($line.Value -match "aawc_population_tooltip_${resource}_cost") "$tooltip does not display $resource cost"
    }
}

# Transaction model: reserve is idempotent; exactly one of cancel/complete can
# settle it; duplicate callback delivery cannot release or consume again.
$cancel = New-BlockerTransaction 350
Reserve-BlockerTransaction $cancel
Reserve-BlockerTransaction $cancel
Assert-That ($cancel.Reserved -eq 350) 'duplicate blocker start reserved twice'
Cancel-BlockerTransaction $cancel
Cancel-BlockerTransaction $cancel
Assert-That ($cancel.Reserved -eq 0 -and $cancel.Consumed -eq 0) 'cancel must release once and never consume'

$complete = New-BlockerTransaction 350
Reserve-BlockerTransaction $complete
Complete-BlockerTransaction $complete
Complete-BlockerTransaction $complete
Assert-That ($complete.Reserved -eq 0 -and $complete.Consumed -eq 350) 'completion must consume exactly once'

$onAction = Read-Source 'common\on_action\aawc_population_holding_construction_on_actions.txt'
foreach ($definition in 'aawc_population_on_blocker_clearance_started', 'aawc_population_on_blocker_clearance_cancelled', 'aawc_population_on_blocker_clearance_completed') {
    Assert-That ($onAction -match "(?m)^$definition\s*=\s*\{") "missing blocker lifecycle hook $definition"
}
Assert-That ($onAction -match 'NOT = \{ has_variable = aawc_population_blocker_clearance_under_construction \}') 'blocker start must reject duplicate reservations'
Assert-That (($onAction | Select-String -Pattern 'aawc_population_release_reserved_amount_effect' -AllMatches).Matches.Count -ge 1) 'blocker cancellation must release a reserve'
Assert-That (($onAction | Select-String -Pattern 'aawc_population_consume_reserved_amount_effect' -AllMatches).Matches.Count -ge 1) 'blocker completion must consume a reserve'

# Overlay coverage is additive.  The generated building and localization files
# are hash-pinned to prove this task did not regenerate either legacy asset.
$buildingPath = Join-Path $mod 'common\buildings\zz_aawc_regional_blockers.txt'
$localizationPath = Join-Path $mod 'localization\english\aawc_regional_blockers_l_english.yml'
Assert-That ((Get-FileHash -LiteralPath $buildingPath -Algorithm SHA256).Hash -eq '8F87DC80B2193C470278C5C52662574ADED516B56211AEF998198A67BAD3A432') 'regional blocker definitions were changed'
Assert-That ((Get-FileHash -LiteralPath $localizationPath -Algorithm SHA256).Hash -eq '0288E970BB2981957703F88AD4521AA1E607CB1D8A969D356517CAE0E9A42091') 'regional blocker prose was changed'

$categories = [regex]::Matches((Get-Content -LiteralPath $buildingPath -Raw -Encoding utf8), '(?m)^\s*flag = (aawc_blocker_category_\S+)') |
    ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
$conditions = Read-Source 'common\scripted_effects\aawc_stage2_condition_effects.txt'
$overlays = Read-Source 'common\scripted_effects\zzzz_aawc_stage4_blocker_overlays.txt'
Assert-That (($conditions + "`n" + $overlays) -match 'aawc_stage4_blocker_contributions_effect = yes') 'Stage 2 refresh must invoke the Stage 4 blocker overlay'
foreach ($category in $categories) {
    Assert-That (($conditions + "`n" + $overlays) -match [regex]::Escape($category)) "missing Stage 2 overlay for $category"
}
$overlayContributions = [regex]::Matches($overlays, 'aawc_stage2_add_contribution_effect\s*=\s*\{([^}]*)\}')
Assert-That ($overlayContributions.Count -eq 12) 'Stage 4 must add one contribution overlay for every previously uncovered category'
foreach ($overlay in $overlayContributions) {
    foreach ($dimension in 'SUSTENANCE', 'HABITATION', 'OPPORTUNITY', 'HEALTH', 'SECURITY', 'AMENITIES', 'SPACE_PERCENT') {
        Assert-That ($overlay.Groups[1].Value -match "\b$dimension\s*=") "blocker overlay omits $dimension"
    }
}

Write-Host 'PASS: Stage 4 colonization-cost and blocker-overlay acceptance checks.'
