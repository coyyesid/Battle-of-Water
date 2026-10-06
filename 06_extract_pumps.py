#!/usr/bin/env python3
"""
Script 6: Extraer estaciones de bombeo activas en 2000
"""

import pandas as pd
import os

os.makedirs('output', exist_ok=True)


PUMPING_STATIONS = 'pumping_stations/pumping_stations-static_properties.xlsx'
year_2000 = pd.Timestamp('2000-01-01')


df = pd.read_excel(PUMPING_STATIONS)
print(f"Total estaciones: {len(df)}")

# ==============================================================================
# FUNCIÓN: Filtrar bombas activas en 2000
# ==============================================================================

def filter_pumps_for_year(option_ids_str, install_dates_str, end_dates_str, year_ref):
    """
    Filtra bombas que estaban activas en year_ref
    
    Retorna:
        option_ids_filtered: string con bombas activas separadas por ;
        install_dates_filtered: string con fechas de instalación correspondientes
        end_dates_filtered: string con fechas de fin correspondientes (o vacío)
    """
    # Si no hay fechas de instalación, retornar None (estación sin bombas)
    if pd.isna(install_dates_str):
        return None, None, None
    
    # Separar en listas
    option_ids = [x.strip() for x in str(option_ids_str).split(';')]
    install_dates = [x.strip() for x in str(install_dates_str).split(';')]
    
    # End dates puede ser NaN o tener menos elementos que install
    if pd.isna(end_dates_str):
        end_dates = [None] * len(install_dates)
    else:
        end_dates = [x.strip() for x in str(end_dates_str).split(';')]
        # Rellenar con None si faltan
        while len(end_dates) < len(install_dates):
            end_dates.append(None)
    
    # Filtrar bombas activas en year_ref
    active_options = []
    active_install = []
    active_end = []
    
    for i, (opt, inst, end) in enumerate(zip(option_ids, install_dates, end_dates)):
        # Parsear fecha de instalación
        try:
            install_date = pd.Timestamp(inst)
        except:
            continue  # Fecha inválida, saltar
        
        # Parsear fecha de fin (si existe)
        try:
            end_date = pd.Timestamp(end) if end and end != 'nan' else None
        except:
            end_date = None
        
        # Verificar si estaba activa en year_ref
        installed_before = install_date <= year_ref
        still_active = (end_date is None) or (end_date > year_ref)
        
        if installed_before and still_active:
            active_options.append(opt)
            active_install.append(inst)
            active_end.append(end if end and end != 'nan' else '')
    
    # Si no quedan bombas activas, retornar None
    if len(active_options) == 0:
        return None, None, None
    
    # Unir con ;
    return (
        ';'.join(active_options),
        ';'.join(active_install),
        ';'.join(active_end) if any(active_end) else ''
    )

# ==============================================================================
# PROCESAR ESTACIONES
# ==============================================================================

stations_filtered = []
skipped_no_install = 0
skipped_no_active = 0

for idx, row in df.iterrows():
    station_id = row['pumping_station_id']
    source_id = row['assigned_source']
    option_ids_str = row['pumps-option_ids']
    install_dates_str = row['pumps-installation_dates']
    end_dates_str = row['pumps-end_dates']
    
    # Sin fechas de instalación → omitir
    if pd.isna(install_dates_str):
        skipped_no_install += 1
        continue
    
    # Filtrar bombas activas
    active_opts, active_inst, active_end = filter_pumps_for_year(
        option_ids_str, install_dates_str, end_dates_str, year_2000
    )
    
    # Si no quedó ninguna bomba activa → omitir
    if active_opts is None:
        skipped_no_active += 1
        continue
    
    # Guardar estación con bombas filtradas
    stations_filtered.append({
        'pumping_station_id': station_id,
        'assigned_source': source_id,
        'pumps-option_ids': active_opts,
        'pumps-installation_dates': active_inst,
        'pumps-end_dates': active_end if active_end else ''
    })

df_output = pd.DataFrame(stations_filtered)

# Guardar
output_file = 'output/pumping_stations_2000.csv'
df_output.to_csv(output_file, index=False)

print(f"Total estaciones leídas: {len(df)}")
print(f"Omitidas - sin fecha de instalación: {skipped_no_install}")
print(f"Omitidas - sin bombas activas en 2000: {skipped_no_active}")
print(f"Estaciones con bombas activas en 2000:    {len(df_output)}")


# Estadísticas
if len(df_output) > 0:
    # Contar total de bombas
    total_pumps = sum(len(row['pumps-option_ids'].split(';')) for _, row in df_output.iterrows())
    print(f"Total de bombas activas en 2000: {total_pumps}")
    
    # Distribución por tipo
    pump_types = {}
    for _, row in df_output.iterrows():
        for pump in row['pumps-option_ids'].split(';'):
            pump_types[pump] = pump_types.get(pump, 0) + 1
    
    print(f"Distribución por tipo de bomba:")
    for pump_type, count in sorted(pump_types.items()):
        print(f"   {pump_type}: {count} bombas")
