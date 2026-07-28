#!/usr/bin/env python3
import os
import config
import loaders
import processors

def ensure_directories():
    if not os.path.exists(config.RAW_DIR):
        os.makedirs(config.RAW_DIR)

def main():
    print("=" * 60)
    print(" NHANES 2005-2006 Vision Data Processor (v4 - Refatorado)")
    print("=" * 60)
    
    ensure_directories()
    
    print("\n=== ETAPA 2: Processamento e Higienização dos Dados ===")
    
    df_demo = loaders.load_demographic_data()
    df_vix = loaders.load_vision_data()
    df_bmx = loaders.load_anthropometric_data()
    df_vid, has_vit_d = loaders.load_vitamin_d_data()
    
    print("\n--- Processando Refração e Calculando Equivalente Esférico ---")
    df_vix = processors.clean_refraction_values(df_vix)
    df_vix = processors.calculate_spherical_equivalent(df_vix)
    df_vix = processors.filter_valid_refraction(df_vix)
    df_vix = processors.classify_myopia(df_vix)
    
    df_consolidado = processors.merge_data_sources(df_vix, df_demo, df_bmx, df_vid, has_vit_d)
    df_consolidado = processors.rename_and_encode(df_consolidado)
    
    processors.print_distribution(df_consolidado)
    processors.save_dataframe(df_consolidado, config.OUTPUT_FILE)

if __name__ == "__main__":
    main()