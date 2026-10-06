#!/usr/bin/env python3
"""
Script 5: Extraer conexiones activas en el año 2000
"""

import pandas as pd
import os

os.makedirs('output', exist_ok=True)


CONNECTIONS_STATIC = 'connections/connections-static_properties.xlsx'
PIPE_OPTIONS = 'pipes/pipe_options-static_properties.xlsx'

year_2000 = pd.Timestamp('2000-01-01')

# ==============================================================================
# LEE OPCIONES DE TUBERIAS
# ==============================================================================

df_pipe_opt = pd.read_excel(PIPE_OPTIONS)

pipe_options = {}
for _, row in df_pipe_opt.iterrows():
    pipe_options[row['option_id']] = {
        'diameter_mm': float(row['diameter']),
        'diameter_m': float(row['diameter']) / 1000.0,  # mm → m
        'roughness': float(row['darcy_friction_factor-new_pipe']),
        'material': str(row['material'])
    }

# ==============================================================================
# LEER CONEXIONES
# ==============================================================================

xl = pd.ExcelFile(CONNECTIONS_STATIC)
dfs = []
for sheet in xl.sheet_names:
    df_sheet = pd.read_excel(CONNECTIONS_STATIC, sheet_name=sheet)
    dfs.append(df_sheet)

df_all = pd.concat(dfs, ignore_index=True)
print(f"Total conexiones: {len(df_all)}")

# ==============================================================================
# CARGAR NODOS VÁLIDOS
# ==============================================================================

df_munis_2000   = pd.read_csv('output/municipalities_2000.csv')
df_sources_2000 = pd.read_csv('output/sources_2000.csv')

valid_nodes = set(
    df_munis_2000['cbs_id'].tolist() +
    df_sources_2000['source_id'].tolist()
)
print(f"Nodos válidos: {len(valid_nodes)}")

# ==============================================================================
# Tuberais  activas en 2000
# ==============================================================================

def get_active_pipe_in_2000(dates_str, options_str):
    """Determina qué pipe estaba activo en 2000"""
    if pd.isna(dates_str) or pd.isna(options_str):
        return None
    
    dates_list = [d.strip() for d in str(dates_str).split(';')]
    options_list = [o.strip() for o in str(options_str).split(';')]
    
    # Parsear fechas
    parsed_dates = []
    for d in dates_list:
        try:
            parsed_dates.append(pd.Timestamp(d))
        except:
            parsed_dates.append(None)
    
    # Encontrar última fecha <= 2000
    best_idx = None
    best_date = None
    
    for i, date in enumerate(parsed_dates):
        if date is None:
            continue
        if date <= year_2000:
            if best_date is None or date > best_date:
                best_date = date
                best_idx = i
    
    if best_idx is None:
        return None
    
    # Tomar pipe correspondiente
    if best_idx < len(options_list):
        return options_list[best_idx]
    else:
        return options_list[-1]

# ==============================================================================
# FILTRAR 
# ==============================================================================

connections = []
skipped_no_date = 0
skipped_future = 0
skipped_node = 0
skipped_no_pipe = 0

for idx, row in df_all.iterrows():
    # Validar fechas de instalación
    dates_str = row.get('pipes-installation_dates', None)
    if pd.isna(dates_str):
        skipped_no_date += 1
        continue
    
    # Obtener pipe activo
    options_str = row.get('pipes-option_ids', None)
    active_pipe = get_active_pipe_in_2000(dates_str, options_str)
    
    if active_pipe is None:
        skipped_future += 1
        continue
    
    # Validar nodos
    from_node = row['from_node']
    to_node = row['to_node']
    
    if from_node not in valid_nodes or to_node not in valid_nodes:
        skipped_node += 1
        continue
    
    # Lookup de propiedades del pipe
    if active_pipe not in pipe_options:
        skipped_no_pipe += 1
        continue
    
    pipe_props = pipe_options[active_pipe]
    
    # Guardar conexión ENRIQUECIDA
    connections.append({
        'connection_id': row['connection_id'],
        'from_node': from_node,
        'to_node': to_node,
        'length': float(row['distance']),
        'minor_loss_coefficient': float(row['minor_loss_coefficient']),
        'pipe_option_id': active_pipe,
        'diameter_mm': pipe_props['diameter_mm'],
        'diameter_m': pipe_props['diameter_m'],
        'roughness': pipe_props['roughness'],
        'material': pipe_props['material'],
        'pipes-installation_dates': dates_str,
        'pipes-option_ids': options_str
    })
    
    if (len(connections)) % 100 == 0:
        print(f"   Procesadas {len(connections)} conexiones...")

df_output = pd.DataFrame(connections)

# ==============================================================================
# GUARDAR
# ==============================================================================

output_file = 'output/connections_2000.csv'
df_output.to_csv(output_file, index=False)


print(f"Total conexiones leídas: {len(df_all)}")
print(f"Omitidas - sin fecha instalación: {skipped_no_date}")
print(f"Omitidas - instaladas > 2000: {skipped_future}")
print(f"Omitidas - nodos inactivos: {skipped_node}")
print(f"Omitidas - pipe no encontrado:  {skipped_no_pipe}")
print(f"Conexiones VÁLIDAS en 2000:           {len(df_output)}")

# Estadísticas
if len(df_output) > 0:
    print(f"ESTADÍSTICAS:")
    print(f"Longitud total: {df_output['length'].sum()/1000:.2f} km")
    
    print(f"Distribución por tipo de tubería:")
    for pipe_id in sorted(df_output['pipe_option_id'].unique()):
        count = len(df_output[df_output['pipe_option_id'] == pipe_id])
        diam = pipe_options[pipe_id]['diameter_mm']
        mat = pipe_options[pipe_id]['material']
        print(f"   {pipe_id}: {count:>3} tuberías (D={diam:.0f}mm, {mat})")

