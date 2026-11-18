import json,unittest,tempfile,shutil
from pathlib import Path
import pyarrow.parquet as pq
from materials.physical import load_inventory
ROOT=Path(__file__).resolve().parents[1]

class InputMaterials(unittest.TestCase):
    def test_json_parquet_values_and_inventory(self):
        self.assertTrue(load_inventory(ROOT/'inputs'))
        seed=json.loads((ROOT/'inputs/seed.json').read_text(encoding='utf-8'))
        for name,rows in seed.items():
            self.assertEqual(pq.read_table(ROOT/'inputs'/(name+'.parquet')).to_pylist(),rows,name)

    def test_modified_raw_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'inputs';shutil.copytree(ROOT/'inputs',target)
            inv=json.loads((target/'inventory.json').read_text(encoding='utf-8'))
            p=target/inv['files'][0]['path'];p.write_bytes(p.read_bytes()+b'x')
            with self.assertRaisesRegex(ValueError,'摘要'):load_inventory(target)

    def test_domain_material_references_and_edge_states(self):
        seed=json.loads((ROOT/'inputs/seed.json').read_text(encoding='utf-8'))
        actions=json.loads((ROOT/'inputs/actions.json').read_text(encoding='utf-8'))
        episodes={x['episode'] for x in seed['visits']};by={}
        for x in seed['events']:
            self.assertIn(x['episode'],episodes)
            if x['event_id'] in by:self.assertEqual(x,by[x['event_id']])
            by[x['event_id']]=x
        self.assertLess(len(by),len(seed['events']))
        self.assertTrue(any(x['kind']=='abandon' for x in by.values()))
        spans={}
        for x in by.values():spans.setdefault(x['episode'],{})[x['kind']]=x
        self.assertTrue(any('join' in x and 'start' not in x and 'abandon' not in x for x in spans.values()))
        for server in ('A1','B1'):
            jobs=sorted([(x['start']['at'],x['finish']['at']) for x in spans.values() if 'finish' in x and x['start']['server']==server])
            self.assertTrue(all(a[1]<=b[0] for a,b in zip(jobs,jobs[1:])))
