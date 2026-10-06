#!/usr/bin/env python3
"""
Script 2: Extraer patrones de demanda (8760 valores horarios)
"""

import pandas as pd
import os

os.makedirs('output', exist_ok=True)

# Rutas de entrada
DEMAND_PATTERNS = 'water_demand_model/water_demand_model-static_properties.xlsx'

# Leer patrones residenciales
df_res = pd.read_excel(DEMAND_PATTERNS, sheet_name='residential')
print(f"{len(df_res)} patrones residenciales")

# Leer patrones comerciales
df_bus = pd.read_excel(DEMAND_PATTERNS, sheet_name='business')
print(f"{len(df_bus)} patrones comerciales")

# Verificar columnas de horas
hour_cols = [f'year_hour-{i}' for i in range(8760)]
missing_cols_res = [col for col in hour_cols if col not in df_res.columns]
missing_cols_bus = [col for col in hour_cols if col not in df_bus.columns]

if missing_cols_res or missing_cols_bus:
    print(f"Advertencia: Faltan algunas columnas de horas")
    print(f"Residencial: {len(missing_cols_res)} columnas faltantes")
    print(f"Comercial: {len(missing_cols_bus)} columnas faltantes")

patterns_res = df_res[['demand_pattern_id'] + hour_cols].copy()
patterns_res['category'] = 'residential'

patterns_bus = df_bus[['demand_pattern_id'] + hour_cols].copy()
patterns_bus['category'] = 'business'

# Combinar todos los patrones
patterns_all = pd.concat([patterns_res, patterns_bus], ignore_index=True)

# Guardar resultado
output_file = 'output/demand_patterns.csv'
patterns_all.to_csv(output_file, index=False)

print(f"Total patrones extraídos: {len(patterns_all)}")
print(f"Residenciales: {len(patterns_res)}")
print(f"Comerciales: {len(patterns_bus)}")

# Verificar algunos valores
sample_pattern = patterns_all.iloc[0]
values = [sample_pattern[f'year_hour-{i}'] for i in range(8760)]
print(f"Patrón ejemplo: {sample_pattern['demand_pattern_id']}")
print(f"  Valor mínimo: {min(values):.4f}")
print(f"  Valor máximo: {max(values):.4f}")
print(f"  Valor promedio: {sum(values)/len(values):.4f}")

