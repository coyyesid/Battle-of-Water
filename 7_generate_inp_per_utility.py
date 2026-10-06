#!/usr/bin/env python3
"""
Script 12: Generar archivo .inp por empresa de agua
Cada empresa obtiene su red independiente con sus provincias
Las fuentes se renombran con provincia para identificar origen
"""

import pandas as pd
import numpy as np
import os

os.makedirs('output', exist_ok=True)


# ==============================================================================
# CARGAR DATOS BASE
# ==============================================================================

df_munis_all = pd.read_csv('output/municipalities_2000.csv')
df_sources_all = pd.read_csv('output/sources_2000.csv')
df_conns_all = pd.read_csv('output/connections_2000.csv')
df_demands_all = pd.read_csv('output/demands_2000.csv')
df_stations_all = pd.read_csv('output/pumping_stations_2000.csv')
df_curves = pd.read_csv('output/pump_curves_2000.csv')

print(f"Municipios: {len(df_munis_all)}")
print(f"✓Fuentes: {len(df_sources_all)}")
print(f"Conexiones: {len(df_conns_all)}")
print(f"Estaciones: {len(df_stations_all)}")

# ==============================================================================
# CARGAR EMPRESAS Y PROVINCIAS
# ==============================================================================

WATER_UTILITIES = 'water_utilities/water_utilities-static_properties.xlsx'
JURISDICTIONS = 'jurisdictions/jurisdictions-static_properties.xlsx'

df_utilities = pd.read_excel(WATER_UTILITIES)
df_provinces = pd.read_excel(JURISDICTIONS, sheet_name='provinces')
df_munis_full = pd.read_excel(JURISDICTIONS, sheet_name='municipalities')

print(f"Empresas: {len(df_utilities)}")
print(f"Provincias: {len(df_provinces)}")

# cbs_id a nombre de provincia
province_names = {}
for _, row in df_provinces.iterrows():
    province_names[row['cbs_id']] = row['name']

#municipio a provincia
muni_to_province = {}
for _, row in df_munis_full.iterrows():
    muni_to_province[row['cbs_id']] = row['province']

print(f"Mapeo municipio → provincia creado")

# ==============================================================================
#  GENERAR .INP PARA UNA EMPRESA
# ==============================================================================

def generate_inp_for_utility(utility_id, provinces_str):
    """
    Genera un archivo .inp para una empresa específica
    """
    # Parsear provincias
    provinces = [p.strip() for p in str(provinces_str).split(';')]
    province_names_list = [province_names.get(p, p) for p in provinces]
    utility_name = '-'.join(province_names_list)
    
    print(f"\n{'='*80}")
    print(f"PROCESANDO: {utility_id} ({utility_name})")
    print(f"Provincias: {provinces}")
    print(f"{'='*80}")
    
    # -------------------------------------------------------------------------
    # FILTRAR MUNICIPIOS DE ESTAS PROVINCIAS
    # -------------------------------------------------------------------------
    
    munis_of_utility = []
    for _, muni in df_munis_all.iterrows():
        cbs_id = muni['cbs_id']
        if cbs_id in muni_to_province:
            if muni_to_province[cbs_id] in provinces:
                munis_of_utility.append(cbs_id)
    
    df_munis = df_munis_all[df_munis_all['cbs_id'].isin(munis_of_utility)].copy()
    df_demands = df_demands_all[df_demands_all['cbs_id'].isin(munis_of_utility)].copy()
    
    print(f"Municipios: {len(df_munis)}")
    
    if len(df_munis) == 0:
        print("Sin municipios, omitiendo empresa")
        return None
    
    # -------------------------------------------------------------------------
    # FILTRAR CONEXIONES Y FUENTES
    # -------------------------------------------------------------------------
    
    # Conexiones donde AMBOS nodos pertenecen a la empresa
    df_conns = df_conns_all[
        df_conns_all['from_node'].isin(munis_of_utility) | 
        df_conns_all['to_node'].isin(munis_of_utility)
    ].copy()
    
    # Identificar fuentes que alimentan municipios de esta empresa
    sources_used = set()
    source_to_province = {}  # Para renombrar fuentes con provincia
    
    for _, conn in df_conns.iterrows():
        from_node = conn['from_node']
        to_node = conn['to_node']
        
        # Si from_node es fuente y to_node es municipio de la empresa
        if from_node.startswith('SG') and to_node in munis_of_utility:
            sources_used.add(from_node)
            # Determinar provincia del municipio destino
            dest_province = muni_to_province.get(to_node, 'UNKNOWN')
            source_to_province[from_node] = dest_province
        
        # Si to_node es fuente y from_node es municipio de la empresa
        if to_node.startswith('SG') and from_node in munis_of_utility:
            sources_used.add(to_node)
            src_province = muni_to_province.get(from_node, 'UNKNOWN')
            source_to_province[to_node] = src_province
    
    df_sources = df_sources_all[df_sources_all['source_id'].isin(sources_used)].copy()
    
    # RENOMBRAR FUENTES CON PROVINCIA
    source_rename_map = {}
    for source_id in sources_used:
        prov_id = source_to_province.get(source_id, 'UNKNOWN')
        prov_name = province_names.get(prov_id, prov_id)
        new_name = f"{source_id}_{prov_name}"
        source_rename_map[source_id] = new_name
    
    print(f"✓ Fuentes: {len(df_sources)} (renombradas con provincia)")
    print(f"✓ Conexiones: {len(df_conns)}")
    
    # Aplicar renombrado en dataframes
    df_sources['source_id_original'] = df_sources['source_id']
    df_sources['source_id'] = df_sources['source_id'].map(source_rename_map)
    
    df_conns['from_node'] = df_conns['from_node'].apply(
        lambda x: source_rename_map.get(x, x)
    )
    df_conns['to_node'] = df_conns['to_node'].apply(
        lambda x: source_rename_map.get(x, x)
    )
    
    # Filtrar estaciones de bombeo de estas fuentes
    df_stations = df_stations_all[
        df_stations_all['assigned_source'].isin(df_sources['source_id_original'].tolist())
    ].copy()
    
    # Renombrar fuentes en estaciones
    df_stations['assigned_source'] = df_stations['assigned_source'].map(
        lambda x: source_rename_map.get(x, x)
    )
    
    print(f"✓ Estaciones: {len(df_stations)}")
    
    # -------------------------------------------------------------------------
    # FILTRAR NODOS CONECTADOS
    # -------------------------------------------------------------------------
    
    connected_nodes = set(
        df_conns['from_node'].tolist() +
        df_conns['to_node'].tolist()
    )
    
    df_munis = df_munis[df_munis['cbs_id'].isin(connected_nodes)].copy()
    df_sources = df_sources[df_sources['source_id'].isin(connected_nodes)].copy()
    df_demands = df_demands[df_demands['cbs_id'].isin(connected_nodes)].copy()
    
    print(f"✓ Nodos conectados - Municipios: {len(df_munis)}, Fuentes: {len(df_sources)}")
    
    # -------------------------------------------------------------------------
    # PREPARAR PATRONES
    # -------------------------------------------------------------------------
    
    patterns_per_muni = {}
    pattern_ids_muni = {}
    
    for _, row in df_demands.iterrows():
        cbs_id = row['cbs_id']
        demand_real = np.array([row[f'hour_{i}'] for i in range(8760)])
        patterns_per_muni[cbs_id] = demand_real
        pattern_ids_muni[cbs_id] = f"P_{cbs_id}"
    
    # -------------------------------------------------------------------------
    # IDENTIFICAR FUENTES CON BOMBAS
    # -------------------------------------------------------------------------
    
    sources_with_pumps = {}
    for _, station in df_stations.iterrows():
        source_id = station['assigned_source']
        if source_id not in sources_with_pumps:
            sources_with_pumps[source_id] = []
        sources_with_pumps[source_id].append(station)
    
    source_destinations = {}
    for source_id in sources_with_pumps.keys():
        conn = df_conns[df_conns['from_node'] == source_id]
        if len(conn) > 0:
            source_destinations[source_id] = conn.iloc[0]['to_node']
    
    # -------------------------------------------------------------------------
    # GENERAR ARCHIVO .INP
    # -------------------------------------------------------------------------
    
    output_file = f'output/{utility_id}_{utility_name}_2000.inp'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        def w(line=''):
            f.write(line + '\n')
        
        def write_section(name):
            w()
            w(f"[{name}]")
        
        # HEADER
        w("[TITLE]")
        w(f"{utility_name} Water Distribution Network - Year 2000")
        w(f"Utility: {utility_id}")
        w(f"Provinces: {', '.join(province_names_list)}")
        
        # JUNCTIONS
        write_section("JUNCTIONS")
        w(";ID               Elev      Demand    Pattern")
        
        for _, row in df_munis.iterrows():
            cbs_id = row['cbs_id']
            elev = row['elevation']
            pat_id = pattern_ids_muni.get(cbs_id, '')
            w(f" {cbs_id:<16} {elev:>8.2f}  {1.0:>10.6f}  {pat_id}")
        
        # Nodos intermedios
        intermediate_nodes = {}
        for source_id, dest_node in source_destinations.items():
            int_node_id = f"INT_{source_id}"
            source_row = df_sources[df_sources['source_id'] == source_id].iloc[0]
            int_elev = source_row['elevation']
            int_pattern = pattern_ids_muni.get(dest_node, '')
            
            intermediate_nodes[source_id] = {
                'node_id': int_node_id,
                'elevation': int_elev,
                'longitude': source_row['longitude'] + 0.001,
                'latitude': source_row['latitude'],
                'pattern': int_pattern
            }
            
            w(f" {int_node_id:<16} {int_elev:>8.2f}  {0.0:>10.6f}  {int_pattern}")
        
        # RESERVOIRS
        write_section("RESERVOIRS")
        w(";ID               Head      Pattern")
        
        for _, row in df_sources.iterrows():
            src_id = row['source_id']
            head = row['elevation'] + 20.0
            w(f" {src_id:<16} {head:>8.2f}")
        
        # TANKS
        write_section("TANKS")
        w(";ID  Elev  InitLvl  MinLvl  MaxLvl  Diam  MinVol  VolCurve")
        
        # PIPES
        write_section("PIPES")
        w(";ID               Node1            Node2            Length    Diameter  Roughness  MinorLoss  Status")
        
        for _, row in df_conns.iterrows():
            from_node = row['from_node']
            to_node = row['to_node']
            
            if from_node in sources_with_pumps:
                int_node = intermediate_nodes[from_node]['node_id']
                w(f" {row['connection_id']:<16} {int_node:<16} {to_node:<16} "
                  f"{row['length']:>9.2f} {row['diameter_m']*1000:>9.2f} "
                  f"{row['roughness']:>10.6f} {row['minor_loss_coefficient']:>10.4f}  Open")
            else:
                w(f" {row['connection_id']:<16} {from_node:<16} {to_node:<16} "
                  f"{row['length']:>9.2f} {row['diameter_m']*1000:>9.2f} "
                  f"{row['roughness']:>10.6f} {row['minor_loss_coefficient']:>10.4f}  Open")
        
        # PUMPS
        write_section("PUMPS")
        w(";ID               Node1            Node2            Parameters")
        
        pump_count = 0
        for source_id, stations in sources_with_pumps.items():
            int_node = intermediate_nodes[source_id]['node_id']
            
            for station_row in stations:
                station_id = station_row['pumping_station_id']
                pumps_str = station_row['pumps-option_ids']
                pump_types = [p.strip() for p in str(pumps_str).split(';')]
                
                for i, pump_type in enumerate(pump_types, 1):
                    pump_id = f"{station_id}_P{i:02d}"
                    curve_name = f"CURVE_{pump_type}"
                    w(f" {pump_id:<16} {source_id:<16} {int_node:<16} HEAD {curve_name}")
                    pump_count += 1
        
        # VALVES
        write_section("VALVES")
        w(";ID  Node1  Node2  Diameter  Type  Setting  MinorLoss")
        
        # CURVES
        write_section("CURVES")
        w(";ID               X-Value      Y-Value")
        
        for pump_type in sorted(df_curves['pump_type'].unique()):
            curve_data = df_curves[df_curves['pump_type'] == pump_type].sort_values('flow_rate')
            curve_name = f"CURVE_{pump_type}"
            w(f";PUMP: {curve_name}")
            for _, point in curve_data.iterrows():
                w(f" {curve_name:<16} {point['flow_rate']:>12.4f}  {point['head']:>12.4f}")
            w()
        
        # PATTERNS
        write_section("PATTERNS")
        w(";ID               Multipliers")
        
        VALS_PER_LINE = 6
        for cbs_id, values in patterns_per_muni.items():
            pat_id = pattern_ids_muni[cbs_id]
            w(f";Pattern {cbs_id}")
            for i in range(0, 8760, VALS_PER_LINE):
                chunk = values[i:i+VALS_PER_LINE]
                vals_str = '  '.join(f"{v:>10.6f}" for v in chunk)
                w(f" {pat_id:<16} {vals_str}")
        
        # Secciones restantes (simplificadas)
        for section in ["DEMANDS", "STATUS", "CONTROLS", "RULES", "EMITTERS", 
                        "QUALITY", "SOURCES", "MIXING"]:
            write_section(section)
        
        write_section("ENERGY")
        w("Global Efficiency  75")
        w("Global Price       0")
        w("Demand Charge      0")
        
        write_section("REACTIONS")
        w("Order Bulk            1")
        w("Order Tank            1")
        w("Order Wall            1")
        w("Global Bulk           0")
        w("Global Wall           0")
        
        write_section("TIMES")
        w("Duration           8760:00")
        w("Hydraulic Timestep 1:00")
        w("Quality Timestep   0:05")
        w("Pattern Timestep   1:00")
        w("Report Timestep    1:00")
        w("Start ClockTime    12:00 AM")
        
        write_section("REPORT")
        w("Status             No")
        w("Summary            No")
        
        write_section("OPTIONS")
        w("Units              CMH")
        w("Headloss           D-W")
        w("Trials             40")
        w("Accuracy           0.001")
        w("Unbalanced         Continue 10")
        w("Demand Multiplier  1.0")
        
        write_section("COORDINATES")
        w(";Node             X-Coord          Y-Coord")
        
        for _, row in df_munis.iterrows():
            w(f" {row['cbs_id']:<16} {row['longitude']:>16.6f}  {row['latitude']:>16.6f}")
        
        for _, row in df_sources.iterrows():
            w(f" {row['source_id']:<16} {row['longitude']:>16.6f}  {row['latitude']:>16.6f}")
        
        for source_id, int_data in intermediate_nodes.items():
            w(f" {int_data['node_id']:<16} {int_data['longitude']:>16.6f}  {int_data['latitude']:>16.6f}")
        
        write_section("VERTICES")
        write_section("LABELS")
        write_section("BACKDROP")
        write_section("END")
    
    print(f"Generado: {output_file}")
    print(f"Municipios: {len(df_munis)}, Fuentes: {len(df_sources)}, Bombas: {pump_count}")
    
    return output_file

# ==============================================================================
# GENERAR .INP PARA CADA EMPRESA
# ==============================================================================

print("GENERANDO ARCHIVOS .INP POR EMPRESA")


generated_files = []

for _, row in df_utilities.iterrows():
    utility_id = row['water_utility_id']
    provinces = row['assigned_provinces']
    
    if pd.isna(provinces):
        print(f"{utility_id}: Sin provincias asignadas, omitiendo")
        continue
    
    result = generate_inp_for_utility(utility_id, provinces)
    if result:
        generated_files.append(result)


print(f"Archivos generados: {len(generated_files)}")
for f in generated_files:
    print(f"   {f}")
