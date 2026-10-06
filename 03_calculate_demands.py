#!/usr/bin/env python3
"""
Script 3: Calcular demanda horaria por municipio
"""

import pandas as pd
import numpy as np
import os

os.makedirs('output', exist_ok=True)

# ==============================================================================
# LEER FACTORES DE DEMANDA DEL EXCEL
# ==============================================================================

WATER_DEMAND_DYNAMIC = 'water_demand_model/water_demand_model-dynamic_properties.xlsx'
year_2000 = pd.Timestamp('2000-01-01')


# Leer hojas de factores
df_house_demand = pd.read_excel(WATER_DEMAND_DYNAMIC, sheet_name='per_house_demand')
df_business_demand = pd.read_excel(WATER_DEMAND_DYNAMIC, sheet_name='per_business_demand')

# Convertir timestamp y filtrar 2000
df_house_demand['timestamp'] = pd.to_datetime(df_house_demand['timestamp'])
df_business_demand['timestamp'] = pd.to_datetime(df_business_demand['timestamp'])

row_house = df_house_demand[df_house_demand['timestamp'] == year_2000].iloc[0]
row_business = df_business_demand[df_business_demand['timestamp'] == year_2000].iloc[0]

# Calcular PROMEDIO de las dos columnas (NL0000-min y NL0000-max)
house_min = row_house['NL0000-min']
house_max = row_house['NL0000-max']
PER_HOUSE_DEMAND = (house_min + house_max) / 2.0

business_min = row_business['NL0000-min']
business_max = row_business['NL0000-max']
PER_BUSINESS_DEMAND = (business_min + business_max) / 2.0

print(f"PARÁMETROS DE CÁLCULO (del Excel):")
print(f"Per house demand:")
print(f"      Min: {house_min:.5f} m³/h")
print(f"      Max: {house_max:.5f} m³/h")
print(f"      Promedio: {PER_HOUSE_DEMAND:.5f} m³/h  ← USADO")
print(f"Per business demand:")
print(f"      Min: {business_min:.5f} m³/h")
print(f"      Max: {business_max:.5f} m³/h")
print(f"      Promedio: {PER_BUSINESS_DEMAND:.5f} m³/h  ← USADO")

# ==============================================================================
# LEER ARCHIVOS PREVIOS
# ==============================================================================


df_munis = pd.read_csv('output/municipalities_2000.csv')
print(f"{len(df_munis)} municipios")

df_patterns = pd.read_csv('output/demand_patterns.csv')
print(f"{len(df_patterns)} patrones")

# Leer asociaciones de patrones
MUNICIPALITIES_DYNAMIC = 'jurisdictions/municipalities-dynamic_properties.xlsx'

df_assoc_res1 = pd.read_excel(MUNICIPALITIES_DYNAMIC, sheet_name='assoc_dem_pat-residential-1')
df_assoc_res2 = pd.read_excel(MUNICIPALITIES_DYNAMIC, sheet_name='assoc_dem_pat-residential-2')
df_assoc_bus = pd.read_excel(MUNICIPALITIES_DYNAMIC, sheet_name='assoc_dem_pat-business')

# Convertir timestamp y filtrar 2000
df_assoc_res1['timestamp'] = pd.to_datetime(df_assoc_res1['timestamp'])
df_assoc_res2['timestamp'] = pd.to_datetime(df_assoc_res2['timestamp'])
df_assoc_bus['timestamp'] = pd.to_datetime(df_assoc_bus['timestamp'])

row_assoc_res1 = df_assoc_res1[df_assoc_res1['timestamp'] == year_2000].iloc[0]
row_assoc_res2 = df_assoc_res2[df_assoc_res2['timestamp'] == year_2000].iloc[0]
row_assoc_bus = df_assoc_bus[df_assoc_bus['timestamp'] == year_2000].iloc[0]

# ==============================================================================
# CALCULAR DEMANDA
# ==============================================================================


hour_cols = [f'year_hour-{i}' for i in range(8760)]
demands = []
successful = 0
failed = 0

for idx, muni in df_munis.iterrows():
    cbs_id = muni['cbs_id']
    n_houses = muni['n_houses']
    n_businesses = muni['n_businesses']
    
    try:
        # Obtener IDs de patrones
        pattern_res1_id = row_assoc_res1[cbs_id] if cbs_id in row_assoc_res1.index else None
        pattern_res2_id = row_assoc_res2[cbs_id] if cbs_id in row_assoc_res2.index else None
        pattern_bus_id = row_assoc_bus[cbs_id] if cbs_id in row_assoc_bus.index else None
        
        if pd.isna(pattern_res1_id) or pd.isna(pattern_res2_id) or pd.isna(pattern_bus_id):
            print(f"{cbs_id}: Patrones no asignados")
            demand_total = np.full(8760, n_houses * PER_HOUSE_DEMAND + n_businesses * PER_BUSINESS_DEMAND)
        else:
            # Obtener patrones
            pattern_res1 = df_patterns[df_patterns['demand_pattern_id'] == pattern_res1_id]
            pattern_res2 = df_patterns[df_patterns['demand_pattern_id'] == pattern_res2_id]
            pattern_bus = df_patterns[df_patterns['demand_pattern_id'] == pattern_bus_id]
            
            if len(pattern_res1) == 0 or len(pattern_res2) == 0 or len(pattern_bus) == 0:
                print(f"{cbs_id}: Patrones no encontrados en base de datos")
                demand_total = np.full(8760, n_houses * PER_HOUSE_DEMAND + n_businesses * PER_BUSINESS_DEMAND)
            else:
                pattern_res1 = pattern_res1.iloc[0]
                pattern_res2 = pattern_res2.iloc[0]
                pattern_bus = pattern_bus.iloc[0]
                
                # Calcular demanda horaria (patrones son multiplicadores 0-1)
                demand_res = (
                    0.5 * pattern_res1[hour_cols].values.astype(float) * n_houses * PER_HOUSE_DEMAND +
                    0.5 * pattern_res2[hour_cols].values.astype(float) * n_houses * PER_HOUSE_DEMAND
                )
                
                demand_bus = pattern_bus[hour_cols].values.astype(float) * n_businesses * PER_BUSINESS_DEMAND
                
                demand_total = demand_res + demand_bus
        
        # Guardar
        demand_row = {'cbs_id': cbs_id}
        for i, val in enumerate(demand_total):
            demand_row[f'hour_{i}'] = float(val)
        
        demands.append(demand_row)
        successful += 1
        
        if (idx + 1) % 50 == 0:
            print(f"   Procesados {idx + 1}/{len(df_munis)} municipios...")
    
    except Exception as e:
        print(f"Error en {cbs_id}: {str(e)}")
        failed += 1

df_demands = pd.DataFrame(demands)

# Guardar resultado
output_file = 'output/demands_2000.csv'
df_demands.to_csv(output_file, index=False)


print(f"Municipios procesados exitosamente: {successful}")
print(f"Municipios con errores: {failed}")

# Estadísticas
total_demands = []
for i in range(8760):
    total_demands.append(df_demands[f'hour_{i}'].sum())

print("ESTADÍSTICAS DE DEMANDA:")
print(f"Demanda total promedio: {np.mean(total_demands):,.2f} m³/h")
print(f"Demanda total mínima: {np.min(total_demands):,.2f} m³/h")
print(f"Demanda total máxima: {np.max(total_demands):,.2f} m³/h")
print(f"Demanda anual total: {np.sum(total_demands):,.2f} m³")

