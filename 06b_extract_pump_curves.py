#!/usr/bin/env python3
"""
Script 6b: Extraer curvas Q-H de bombas
"""

import pandas as pd
import os

os.makedirs('output', exist_ok=True)

PUMP_OPTIONS = 'pumps/pump_options-static_properties.xlsx'


# Leer hoja principal con lista de bombas
df_options = pd.read_excel(PUMP_OPTIONS, sheet_name='options')
print(f"{len(df_options)} tipos de bomba disponibles")

# Leer qué bombas están activas en 2000
df_stations = pd.read_csv('output/pumping_stations_2000.csv')

# Obtener tipos únicos de bombas activas
pump_types_active = set()
for _, row in df_stations.iterrows():
    pumps = str(row['pumps-option_ids']).split(';')
    pump_types_active.update(pumps)

print(f"Tipos de bomba activos en 2000: {sorted(pump_types_active)}")

# ==============================================================================
# EXTRAER CURVAS Q-H
# ==============================================================================

xl = pd.ExcelFile(PUMP_OPTIONS)
curves = []

for pump_type in sorted(pump_types_active):
    # Verificar que la hoja exista
    if pump_type not in xl.sheet_names:
        print(f"{pump_type}: Hoja no encontrada en Excel, omitiendo...")
        continue
    
    # Leer curva
    df_curve = pd.read_excel(PUMP_OPTIONS, sheet_name=pump_type)
    
    # Verificar columnas necesarias
    if 'flow_rate' not in df_curve.columns or 'head' not in df_curve.columns:
        print(f"{pump_type}: Columnas 'flow_rate' o 'head' no encontradas")
        continue
    
    # Limpiar y ordenar por flow_rate
    df_curve = df_curve[['flow_rate', 'head']].dropna()
    df_curve = df_curve.sort_values('flow_rate').reset_index(drop=True)
    
    # Guardar cada punto de la curva
    for idx, row in df_curve.iterrows():
        curves.append({
            'pump_type': pump_type,
            'point_number': idx + 1,
            'flow_rate': float(row['flow_rate']),
            'head': float(row['head'])
        })
    
    print(f"{pump_type}: {len(df_curve)} puntos en la curva")

df_curves = pd.DataFrame(curves)

# Guardar
output_file = 'output/pump_curves_2000.csv'
df_curves.to_csv(output_file, index=False)

print(f"Tipos de bomba procesados: {len(pump_types_active)}")
print(f"Total puntos de curva: {len(df_curves)}")

print(f"Archivo guardado: {output_file}")

# Mostrar ejemplo de cada curva
print("CURVAS EXTRAÍDAS:")
for pump_type in sorted(pump_types_active):
    curve_data = df_curves[df_curves['pump_type'] == pump_type]
    if len(curve_data) > 0:
        print(f"{pump_type}:")
        print(f"Puntos: {len(curve_data)}")
        print(f"Q range: {curve_data['flow_rate'].min():.1f} - {curve_data['flow_rate'].max():.1f}")
        print(f"H range: {curve_data['head'].min():.1f} - {curve_data['head'].max():.1f}")
        print(f"Primeros 3 puntos:")
        for _, row in curve_data.head(3).iterrows():
            print(f"    Q={row['flow_rate']:>6.1f} m³/h  →  H={row['head']:>6.2f} m")

