#!/usr/bin/env python3
"""
Script 1: Extraer municipios activos en el año 2000
"""

import pandas as pd
from datetime import datetime
import os

# Crear carpeta de salida si no existe
os.makedirs('output', exist_ok=True)

# Rutas de entrada (ajustar según tu estructura)
JURISDICTIONS_STATIC = 'jurisdictions/jurisdictions-static_properties.xlsx'
MUNICIPALITIES_DYNAMIC = 'jurisdictions/municipalities-dynamic_properties.xlsx'

# Leer datos estáticos
df_static = pd.read_excel(JURISDICTIONS_STATIC, sheet_name='municipalities')
print(f"✓ Leídos {len(df_static)} municipios totales")

# Filtrar activos en 2000
year_2000 = pd.Timestamp('2000-01-01')

df_static['begin_date'] = pd.to_datetime(df_static['begin_date'])
df_static['end_date'] = pd.to_datetime(df_static['end_date'])

active_2000 = df_static[
    (df_static['begin_date'] <= year_2000) &
    ((df_static['end_date'].isna()) | (df_static['end_date'] > year_2000))
].copy()

print(f"Filtrados {len(active_2000)} municipios activos en 2000")


df_pop = pd.read_excel(MUNICIPALITIES_DYNAMIC, sheet_name='population')
df_houses = pd.read_excel(MUNICIPALITIES_DYNAMIC, sheet_name='n_houses')
df_business = pd.read_excel(MUNICIPALITIES_DYNAMIC, sheet_name='n_businesses')

# Convertir timestamp
df_pop['timestamp'] = pd.to_datetime(df_pop['timestamp'])
df_houses['timestamp'] = pd.to_datetime(df_houses['timestamp'])
df_business['timestamp'] = pd.to_datetime(df_business['timestamp'])

# Filtrar fila 2000-01-01
row_pop = df_pop[df_pop['timestamp'] == year_2000].iloc[0]
row_houses = df_houses[df_houses['timestamp'] == year_2000].iloc[0]
row_business = df_business[df_business['timestamp'] == year_2000].iloc[0]


result = []
municipalities_with_data = 0
municipalities_without_data = 0

for _, muni in active_2000.iterrows():
    cbs_id = muni['cbs_id']
    
    # Verificar que el municipio tenga datos dinámicos
    if cbs_id in row_pop.index:
        pop_value = row_pop[cbs_id]
        houses_value = row_houses[cbs_id]
        business_value = row_business[cbs_id]
        
        # Solo incluir si tiene datos válidos (no NaN y > 0)
        if pd.notna(pop_value) and pop_value > 0:
            result.append({
                'cbs_id': cbs_id,
                'name': muni['name'],
                'province': muni['province'],
                'latitude': muni['latitude'],
                'longitude': muni['longitude'],
                'elevation': muni['elevation'],
                'population': float(pop_value),
                'n_houses': float(houses_value) if pd.notna(houses_value) else 0.0,
                'n_businesses': float(business_value) if pd.notna(business_value) else 0.0
            })
            municipalities_with_data += 1
        else:
            municipalities_without_data += 1
    else:
        municipalities_without_data += 1

df_result = pd.DataFrame(result)

# Guardar resultado
output_file = 'output/municipalities_2000.csv'
df_result.to_csv(output_file, index=False)

print(f"Total municipios activos en 2000: {len(active_2000)}")
print(f"Municipios CON datos válidos: {municipalities_with_data}")
print(f"Municipios SIN datos válidos: {municipalities_without_data}")


print("ESTADÍSTICAS:")
print(f"Población total: {df_result['population'].sum():,.0f}")
print(f"Total casas: {df_result['n_houses'].sum():,.0f}")
print(f"Total negocios: {df_result['n_businesses'].sum():,.0f}")
print(f"Población promedio por municipio: {df_result['population'].mean():,.0f}")

