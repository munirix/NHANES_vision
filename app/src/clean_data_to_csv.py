# -*- coding: utf-8 -*-
"""
Higienização de um ciclo do NHANES e exportação para CSV.

Encadeia a carga dos componentes brutos (DEMO/VIX/BMX/VID) com as regras de
tratamento: remoção dos códigos de anomalia, cálculo do Equivalente Esférico (SE),
rotulagem das classes de miopia, harmonização do top-coding de idade e merge das
fontes por SEQN. A orquestração dos ciclos fica em main.py.
"""
import config
import loaders
import processors

def process_cycle(cycle):
    """Executa o pipeline completo de um único ciclo: carga, higienização, cálculo
    do equivalente esférico, rotulagem e merge das fontes. Retorna None quando o
    ciclo não pode ser processado."""
    
    print("\n" + "-" * 60)
    print(f" CICLO {cycle['name']} (sufixo '{cycle['suffix']}')")
    print("-" * 60)
    
    if not loaders.check_cycle_files(cycle):
        return None
        
    df_demo = loaders.load_demographic_data(cycle)
    df_vix = loaders.load_vision_data(cycle)
    if df_vix is None:
        return None
    df_bmx = loaders.load_anthropometric_data(cycle)
    df_vid, has_vit_d = loaders.load_vitamin_d_data(cycle)
    
    print("\n--- Processando Refração e Calculando Equivalente Esférico ---")
    df_vix = processors.clean_refraction_values(df_vix)
    df_vix = processors.calculate_spherical_equivalent(df_vix)
    df_vix = processors.filter_valid_refraction(df_vix)
    df_vix = processors.classify_myopia(df_vix)
    
    df_demo = processors.harmonize_age(df_demo)
    
    df_cycle = processors.merge_data_sources(df_vix, df_demo, df_bmx, df_vid, has_vit_d)
    df_cycle = processors.rename_and_encode(df_cycle)
    df_cycle = processors.tag_cycle(df_cycle, cycle["name"])
    
    processors.print_distribution(df_cycle, f"Ciclo {cycle['name']} consolidado!")
    processors.save_dataframe(df_cycle, config.cycle_output_file(cycle["name"]))
    
    return df_cycle