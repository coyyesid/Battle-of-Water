#!/usr/bin/env python3
"""
Script 4: Extraer fuentes de agua activas en 2000
"""

import pandas as pd
from datetime import datetime
import os

os.makedirs('output', exist_ok=True)


# Rutas de entrada
SOURCES_STATIC = 'sources/sources-static_properties.xlsx'

year_2000 = pd.Timestamp('2000-01-01')


# Leer Excel con todas las hojas
xl = pd.ExcelFile(SOURCES_STATIC)
print(f"Hojas disponibles: {xl.sheet_names}")

sources_all = []

# Procesar cada tipo de fuente
for sheet in ['groundwater', 'surface_water', 'desalination']:
    if sheet not in xl.sheet_names:
        print(f"Hoja '{sheet}' no encontrada")
        continue
    
    df = pd.read_excel(SOURCES_STATIC, sheet_name=sheet)
    print(f"Total fuentes en hoja: {len(df)}")
    
    # Convertir fechas
    if 'activation_date' in df.columns:
        df['activation_date'] = pd.to_datetime(df['activation_date'], errors='coerce')
    if 'closure_date' in df.columns:
        df['closure_date'] = pd.to_datetime(df['closure_date'], errors='coerce')
    
    # Filtrar activas en 2000 (REGLAS ESTRICTAS):
    # 1. activation_date DEBE existir (no NaN) y ser <= 2000-01-01
    # 2. closure_date DEBE ser NaN (sin fecha de cierre) O > 2000-01-01
    df_active = df[
        (df['activation_date'].notna()) &  # DEBE tener fecha de activación
        (df['activation_date'] <= year_2000) &  # Activada antes o en 2000
        ((df['closure_date'].isna()) | (df['closure_date'] > year_2000))  # Sin cierre o cierre después de 2000
    ].copy()
    
    print(f"Fuentes activas en 2000: {len(df_active)}")
    
    # Agregar tipo de fuente
    df_active['source_type'] = sheet
    
    # Seleccionar columnas relevantes
    cols_to_keep = ['source_id', 'source_type', 'latitude', 'longitude', 'elevation', 'province']
    
    # Agregar capacity si existe
    if 'capacity-nominal' in df_active.columns:
        cols_to_keep.append('capacity-nominal')
    
    # Agregar permit para groundwater
    if sheet == 'groundwater' and 'permit' in df_active.columns:
        cols_to_keep.append('permit')
    
    # Filtrar columnas que existen
    cols_available = [col for col in cols_to_keep if col in df_active.columns]
    
    sources_all.append(df_active[cols_available])

# Combinar todas las fuentes
df_sources = pd.concat(sources_all, ignore_index=True)

# Rellenar valores faltantes de capacity con 0
if 'capacity-nominal' not in df_sources.columns:
    df_sources['capacity-nominal'] = 0.0
else:
    df_sources['capacity-nominal'] = df_sources['capacity-nominal'].fillna(0.0)

# Guardar resultado
output_file = 'output/sources_2000.csv'
df_sources.to_csv(output_file, index=False)

print(f"Total fuentes activas en 2000: {len(df_sources)}")

# Desglose por tipo
for source_type in df_sources['source_type'].unique():
    count = len(df_sources[df_sources['source_type'] == source_type])
    print(f"  - {source_type}: {count}")


# Estadísticas de capacidad
if 'capacity-nominal' in df_sources.columns:
    sources_with_capacity = df_sources[df_sources['capacity-nominal'] > 0]
    print("ESTADÍSTICAS DE CAPACIDAD:")
    print(f"Fuentes con capacidad definida: {len(sources_with_capacity)}/{len(df_sources)}")
    print(f"Capacidad está en m³/día (no m³/año)")
    if len(sources_with_capacity) > 0:
        print(f"Capacidad total: {sources_with_capacity['capacity-nominal'].sum():,.0f} m³/día")
        print(f"Capacidad promedio: {sources_with_capacity['capacity-nominal'].mean():,.0f} m³/día")
        print(f"Capacidad mínima: {sources_with_capacity['capacity-nominal'].min():,.0f} m³/día")
        print(f"Capacidad máxima: {sources_with_capacity['capacity-nominal'].max():,.0f} m³/día")
        
        # Conversión a m³/h para referencia
        capacity_hourly = sources_with_capacity['capacity-nominal'].sum() / 24
        print(f"Capacidad total en m³/h: {capacity_hourly:,.2f} m³/h")

# Verificar elevaciones
sources_with_elevation = df_sources[df_sources['elevation'].notna()]
print(f"Fuentes con elevación definida: {len(sources_with_elevation)}/{len(df_sources)}")
if len(sources_with_elevation) > 0:
    print(f"Elevación promedio: {sources_with_elevation['elevation'].mean():.2f} m")

