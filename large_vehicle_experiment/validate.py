import sys, os
sys.path.insert(0, r'D:\arxml-secdiff-main\graph_based_security_validation-main')
os.chdir(r'D:\arxml-secdiff-main\graph_based_security_validation-main')

from arxml_secdiff import parser

m = parser.parse(['large_vehicle_experiment/full_vehicle_24node.arxml'])
print('Component types:', len(m.component_types))
print('Prototypes (nodes):', len(m.prototypes))
print('Assembly connectors:', len(m.assembly_connectors))
print('ECUs:', len(m.ecus))
print('Interfaces:', len(m.interfaces))
print('PDUs:', len(m.pdus))
print('Data mappings:', len(m.data_mappings))
print('Unresolved refs:', len(m.unresolved_refs))
if m.unresolved_refs:
    for path, ref in m.unresolved_refs:
        print(f'  UNRESOLVED: {path} -> {ref}')
print('\nPrototype nodes:')
for p in sorted(m.prototypes):
    print(f'  {p}')
print('\nECU mappings:')
for proto, ecu in sorted(m.swc_to_ecu.items()):
    print(f'  {proto} -> {ecu}')
