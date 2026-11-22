"""Apply narrow transaction locks to existing authoritative mutation surfaces.

CaFG overrides retain the dependency implementation. Only their mutating entry
points are guarded; no conversion or random-absorption algorithm is replaced.
"""
import re
from pathlib import Path

from aawc_paths import ROOT
from generate_aawc_stage3_buildings import matching_brace

MOD = ROOT / 'mod/AGOT_Alternate_World_Compatch'
EFFECTS = MOD / 'common/scripted_effects'
DEPS = ROOT / 'dependencies/AAWC_Dependencies_Modpack/common/scripted_effects'
CORE_NAMES = ('clear_ineligible_settlement', 'initialize_production_ledger', 'ensure_production_ledger',
              'apply_production_month', 'capture_transfer_packet', 'apply_transfer_packet',
              'debit_legacy_maa_population', 'debit_crisis_population', 'credit_population',
              'debit_population', 'death_population', 'set_population_target', 'apply_signed_transfer')


def guard(text, name, trigger='aawc_stage5_mutation_allowed_trigger = yes', blocked_receipts=()):
    match = re.search(r'(?m)^' + re.escape(name) + r'\s*=\s*\{',text)
    if not match:
        raise ValueError(name)
    start=match.end()-1; end=matching_brace(text,start)
    body=text[start+1:end]
    if body.lstrip().startswith('# Stage 5 endpoint mutation lock'):
        if blocked_receipts and '# Stage 5 blocked receipts' not in body:
            body += '\t# Stage 5 blocked receipts cannot reuse an earlier successful debit.\n\telse = {\n'+''.join(f'\t\tset_variable = {{ name = {key} value = 0 }}\n' for key in blocked_receipts)+'\t}\n'
            return text[:start+1]+body+text[end:]
        return text
    wrapped='\n\t# Stage 5 endpoint mutation lock; the exact committing packet may enter.\n\tif = {\n\t\tlimit = { '+trigger+' }\n'+''.join('\t'+line+'\n' for line in body.strip('\n').splitlines())+'\t}\n'
    return text[:start+1]+wrapped+text[end:]


def cafg_artifacts():
    result={}
    name='kei_cafg_province_struct_effects.txt'
    text=(DEPS/name).read_text(encoding='utf-8-sig')
    for key in ('create_struct','remove_struct','set_struct_factor','add_struct_factor','subtract_struct_factor'):
        text=guard(text,'E_kCAFG_'+key)
    text=guard(text,'E_kCAFG_check_struct_removal','prev = { aawc_stage5_mutation_allowed_trigger = yes }')
    result[EFFECTS/name]='# Generated Stage 5 guard overlay; underlying CaFG algorithms unchanged.\n'+text
    for axis in ('culture','faith'):
        name=f'kei_cafg_province_{axis}_effects.txt'
        text=(DEPS/name).read_text(encoding='utf-8-sig')
        for key in (f'convert_province_{axis}_factor',f'set_province_{axis}_factor',f'set_maximum_province_{axis}_factor',
                    f'set_province_{axis}_percentage',f'province_weighted_{axis}_conversion',f'province_weighted_{axis}_deconversion',
                    f'province_dynamic_weighted_{axis}_conversion',f'province_randomized_weighted_{axis}_conversion',f'clear_all_province_{axis}s'):
            text=guard(text,'E_kCAFG_'+key)
        result[EFFECTS/name]='# Generated Stage 5 guard overlay; underlying CaFG algorithms unchanged.\n'+text
    return result


if __name__=='__main__':
    path=EFFECTS/'aawc_reforging_cohort_production_effects.txt'
    text=path.read_text(encoding='utf-8-sig')
    for name in CORE_NAMES:
        text=guard(text,'aawc_reforging_cohort_'+name+'_effect')
    for name in CORE_NAMES:
        if name.startswith(('capture_', 'apply_transfer', 'debit_', 'credit_', 'death_', 'apply_signed')):
            text=guard(text,'aawc_reforging_cohort_'+name+'_effect',blocked_receipts=(
                'aawc_reforging_cohort_last_transfer_debit','aawc_reforging_cohort_last_transfer_credit',
                'aawc_reforging_cohort_last_external_deaths','aawc_reforging_round_last_applied'))
    text='\n'.join(line.rstrip() for line in text.splitlines())+'\n'
    path.write_text(text,encoding='utf-8-sig',newline='\n')
    for path,text in cafg_artifacts().items():path.write_text(text,encoding='utf-8-sig',newline='\n')
    print('Applied cohort and CaFG endpoint guards')
