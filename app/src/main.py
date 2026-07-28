#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ponto de entrada do pipeline de Harmonização e Consolidação dos Ciclos
Históricos do NHANES (1999-2008).
Desenvolvido para o projeto TCC: Inteligência Artificial para Diagnóstico de Miopia.

Orquestra a execução: percorre os ciclos declarados em config.CYCLES, delega a
higienização de cada um para clean_data_to_csv.process_cycle e concatena os
resultados em uma base unificada de alta volumetria para o treinamento dos modelos.
"""
import os
import config
import processors
import clean_data_to_csv

def ensure_directories():
    for directory in (config.NHANES_DIR, config.CLEANED_DIR, config.CYCLE_DIR):
        os.makedirs(directory, exist_ok=True)

def main():
    print("=" * 60)
    print(" NHANES 1999-2008 Vision Data Processor (v5 - Multiciclo)")
    print("=" * 60)
    
    ensure_directories()
    
    processed_dfs = []
    for cycle in config.CYCLES:
        df_cycle = clean_data_to_csv.process_cycle(cycle)
        if df_cycle is not None:
            processed_dfs.append(df_cycle)
            
    if not processed_dfs:
        print(f"\n[!] Nenhum ciclo foi carregado. Verifique os arquivos .XPT em '{config.NHANES_DIR}'.")
        return
        
    print("\n" + "=" * 60)
    print(" CONSOLIDAÇÃO HISTÓRICA (1999-2008)")
    print("=" * 60)
    
    df_combined = processors.combine_cycles(processed_dfs)
    processors.print_distribution(df_combined, "Consolidação histórica concluída!")
    processors.print_cycle_volumetry(df_combined)
    processors.save_dataframe(df_combined, config.OUTPUT_FILE)
    print("\nTudo pronto para iniciar a análise exploratória de dados (EDA) e treinamento dos modelos!")

if __name__ == "__main__":
    main()