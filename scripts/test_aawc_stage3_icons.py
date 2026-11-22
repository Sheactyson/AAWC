"""Focused asset and generated-reference checks for Stage 3 building icons."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
import struct
import unittest

import generate_aawc_stage3_buildings as buildings
from aawc_paths import MOD_SOURCE_ROOT


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / 'mod/AGOT_Alternate_World_Compatch/gfx/interface/icons/building_types'


class Stage3Icons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = json.loads((ROOT / 'catalogue/stage3/catalogue.json').read_text(encoding='utf-8'))
        cls.chains = {chain['id'] for chain in cls.catalogue['chains']}
        cls.artifacts = buildings.compile_buildings(cls.catalogue, buildings.load_source(buildings.CONSTRUCTION))
        cls.script = cls.artifacts[buildings.BUILDINGS].decode('utf-8-sig')
        cls.icons = dict(re.findall(r'(?m)^(aawc_[a-z0-9_]+_\d\d)\s*=\s*\{.*?^\s*type_icon\s*=\s*"([^"]+)"', cls.script, re.S | re.M))

    def test_every_chain_has_one_distinct_chain_icon(self):
        self.assertEqual(len(self.chains), 131)
        self.assertNotIn('icon_building_market_villages.dds', self.icons.values())
        for chain in self.chains:
            expected = buildings.stage3_icon(chain)
            levels = [level['id'] for item in self.catalogue['chains'] if item['id'] == chain for level in item['levels']]
            self.assertTrue(levels, chain)
            self.assertEqual({self.icons[level] for level in levels}, {expected}, chain)
        self.assertEqual(set(self.icons.values()), {buildings.stage3_icon(chain) for chain in self.chains})

    def test_referenced_dds_assets_exist_and_use_project_layout(self):
        digests = set()
        blocker = (ICON_DIR / 'aawc_blocker_blight_a.dds').read_bytes()
        for icon in set(self.icons.values()):
            with self.subTest(icon=icon):
                payload = (ICON_DIR / icon).read_bytes()
                self.assertEqual(len(payload), 262272)
                self.assertEqual(payload[:4], b'DDS ')
                self.assertEqual(payload[:128], blocker[:128])
                self.assertEqual(struct.unpack_from('<II', payload, 12), (256, 256))
                self.assertEqual(struct.unpack_from('<IIIIIIII', payload, 76),
                                 (32, 65, 0, 32, 0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000))
                pixels = payload[128:]
                self.assertEqual(set(pixels[0::4]), {0}, 'blue channel must be black')
                self.assertEqual(set(pixels[1::4]), {0}, 'green channel must be black')
                self.assertEqual(set(pixels[2::4]), {0}, 'red channel must be black')
                self.assertEqual(set(pixels[3::4]), {0, 255},
                                 'icon must combine fully transparent background with an opaque silhouette')
                digests.add(hashlib.sha256(payload).digest())
        self.assertEqual(len(digests), 131)

    def test_release_input_tree_includes_each_referenced_asset(self):
        # build_aawc_release.py packages every file under the mod folder. Pin
        # this path-level contract so a future packaging filter cannot silently
        # omit the icon assets.
        mod_folder = MOD_SOURCE_ROOT / 'AGOT_Alternate_World_Compatch'
        release_inputs = {path.relative_to(mod_folder).as_posix() for path in mod_folder.rglob('*') if path.is_file()}
        for icon in set(self.icons.values()):
            self.assertIn(f'gfx/interface/icons/building_types/{icon}', release_inputs)


if __name__ == '__main__':
    unittest.main()
