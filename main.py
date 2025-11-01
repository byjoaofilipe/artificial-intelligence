"""
Script principal para executar e comparar os 4 métodos de otimização.
Inclui visualizações e geração de relatório.
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from data_parser import PatientAllocationData
from milp_model import PatientAllocationMILP
from metaheuristics import SimulatedAnnealing, TabuSearch
from hybrid_solver import HybridSolver, compare_all_methods
import time


def run_complete_comparison(data_file, lambda1=0.5, lambda2=0.5, 
                            time_limit=300, output_dir='/mnt/user-data/outputs'):
    """
    Executa comparação completa dos 4 métodos e gera relatório com gráficos.
    
    Args:
        data_file: Caminho para o ficheiro .dat
        lambda1: Peso do objetivo 1 (custo)
        lambda2: Peso do objetivo 2 (equilíbrio)
        time_limit: Tempo limite em segundos
        output_dir: Diretório para guardar os resultados
    """
    print("="*80)
    print("ANÁLISE COMPLETA: COMPARAÇÃO DOS 4 MÉTODOS")
    print("="*80)
    print(f"\nParâmetros:")
    print(f"  - Ficheiro de dados: {data_file}")
    print(f"  - λ1 (custo): {lambda1}")
    print(f"  - λ2 (equilíbrio): {lambda2}")
    print(f"  - Tempo limite: {time_limit}s")
    print()
    
    # Carregar dados
    print("📂 Carregando dados...")
    data = PatientAllocationData(data_file)
    data.print_summary()
    
    # Executar comparação
    print("\n\n🚀 Executando os 4 métodos...")
    print("="*80)
    
    results = {}
    
    # MÉTODO 1: Branch & Bound
    print("\n🔹 MÉTODO 1: BRANCH & BOUND PURO")
    print("-" * 80)
    start = time.time()
    milp = PatientAllocationMILP(data, lambda1, lambda2)
    milp.build_model()
    m1_result = milp.solve(time_limit=time_limit, threads=4, verbose=True)
    
    if m1_result:
        results['Branch & Bound\n(Exato)'] = {
            'tempo': m1_result['solve_time'],
            'objetivo': m1_result['objective_value'],
            'gap': m1_result['gap'] * 100 if m1_result['gap'] else 0,
            'tipo': 'Exato',
            'cor': '#2ecc71'
        }
    
    # MÉTODO 2: Simulated Annealing
    print("\n🔹 MÉTODO 2: SIMULATED ANNEALING")
    print("-" * 80)
    sa = SimulatedAnnealing(data, lambda1, lambda2)
    m2_result = sa.solve(max_iterations=10000, verbose=True)
    
    results['Simulated\nAnnealing'] = {
        'tempo': m2_result['solve_time'],
        'objetivo': m2_result['objective_value'],
        'gap': None,
        'tipo': 'Metaheurística',
        'cor': '#e74c3c'
    }
    
    # MÉTODO 3: Tabu Search
    print("\n🔹 MÉTODO 3: TABU SEARCH")
    print("-" * 80)
    ts = TabuSearch(data, lambda1, lambda2)
    m3_result = ts.solve(max_iterations=5000, verbose=True)
    
    results['Tabu\nSearch'] = {
        'tempo': m3_result['solve_time'],
        'objetivo': m3_result['objective_value'],
        'gap': None,
        'tipo': 'Metaheurística',
        'cor': '#f39c12'
    }
    
    # MÉTODO 4: Híbrido
    print("\n🔹 MÉTODO 4: HÍBRIDO (SA + B&B)")
    print("-" * 80)
    hybrid = HybridSolver(data, lambda1, lambda2)
    m4_result = hybrid.solve(
        metaheuristic='SA',
        mh_max_iter=5000,
        milp_time_limit=time_limit,
        verbose=True
    )
    
    if m4_result['final_obj']:
        results['Híbrido\n(SA + B&B)'] = {
            'tempo': m4_result['total_time'],
            'objetivo': m4_result['final_obj'],
            'gap': None,
            'tipo': 'Híbrido',
            'cor': '#9b59b6'
        }
    
    # Criar visualizações
    print("\n\n📊 Gerando visualizações...")
    _create_visualizations(results, output_dir, data.num_days, len(data.patients))
    
    # Criar relatório
    print("\n📄 Gerando relatório...")
    _create_report(results, data, lambda1, lambda2, output_dir)
    
    print("\n" + "="*80)
    print("✓ ANÁLISE COMPLETA CONCLUÍDA!")
    print("="*80)
    print(f"\nFicheiros gerados em: {output_dir}/")
    print("  - comparison_chart.png")
    print("  - time_vs_quality.png")
    print("  - report.txt")
    print()


def _create_visualizations(results, output_dir, num_days, num_patients):
    """Cria gráficos de comparação."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Gráfico 1: Tempo de execução
    methods = list(results.keys())
    times = [results[m]['tempo'] for m in methods]
    colors = [results[m]['cor'] for m in methods]
    
    ax1 = axes[0]
    bars1 = ax1.bar(methods, times, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Tempo (segundos)', fontsize=12, fontweight='bold')
    ax1.set_title('Tempo de Execução por Método', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Adicionar valores nas barras
    for bar, time_val in zip(bars1, times):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{time_val:.2f}s',
                ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 2: Qualidade da solução
    objectives = [results[m]['objetivo'] for m in methods]
    
    ax2 = axes[1]
    bars2 = ax2.bar(methods, objectives, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Valor Objetivo', fontsize=12, fontweight='bold')
    ax2.set_title('Qualidade da Solução por Método', fontsize=14, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Adicionar valores nas barras
    for bar, obj_val in zip(bars2, objectives):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{obj_val:.0f}',
                ha='center', va='bottom', fontweight='bold')
    
    # Marcar o melhor
    best_idx = np.argmin(objectives)
    bars2[best_idx].set_edgecolor('gold')
    bars2[best_idx].set_linewidth(3)
    ax2.text(bars2[best_idx].get_x() + bars2[best_idx].get_width()/2., 
             bars2[best_idx].get_height() * 1.02,
             '⭐ MELHOR', ha='center', va='bottom', 
             fontweight='bold', color='darkgreen', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/comparison_chart.png', dpi=150, bbox_inches='tight')
    print(f"  ✓ Gráfico salvo: comparison_chart.png")
    
    # Gráfico 2: Tempo vs Qualidade (scatter plot)
    fig, ax = plt.subplots(figsize=(10, 7))
    
    for method in methods:
        x = results[method]['tempo']
        y = results[method]['objetivo']
        color = results[method]['cor']
        
        ax.scatter(x, y, s=300, color=color, alpha=0.7, edgecolor='black', linewidth=2)
        ax.annotate(method, (x, y), xytext=(10, 10), textcoords='offset points',
                   fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.3))
    
    ax.set_xlabel('Tempo de Execução (segundos)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Valor Objetivo (menor é melhor)', fontsize=12, fontweight='bold')
    ax.set_title('Compromisso Tempo vs Qualidade', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Adicionar linha de referência da solução ótima
    if 'Branch & Bound\n(Exato)' in results:
        optimal = results['Branch & Bound\n(Exato)']['objetivo']
        ax.axhline(y=optimal, color='green', linestyle='--', linewidth=2, 
                  label=f'Solução Ótima: {optimal:.0f}', alpha=0.7)
        ax.legend(fontsize=11)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/time_vs_quality.png', dpi=150, bbox_inches='tight')
    print(f"  ✓ Gráfico salvo: time_vs_quality.png")
    
    plt.close('all')


def _create_report(results, data, lambda1, lambda2, output_dir):
    """Cria relatório textual detalhado."""
    
    with open(f'{output_dir}/report.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("RELATÓRIO: COMPARAÇÃO DE MÉTODOS DE OTIMIZAÇÃO\n")
        f.write("Problema: Alocação de Pacientes em Hospitais\n")
        f.write("="*80 + "\n\n")
        
        f.write("1. INFORMAÇÃO DO PROBLEMA\n")
        f.write("-" * 80 + "\n")
        f.write(f"  • Número de pacientes: {len(data.patients)}\n")
        f.write(f"  • Número de enfermarias: {len(data.wards)}\n")
        f.write(f"  • Número de especializações: {len(data.specialisms)}\n")
        f.write(f"  • Período de planeamento: {data.num_days} dias\n")
        f.write(f"  • Pesos: λ1={lambda1} (custo), λ2={lambda2} (equilíbrio)\n\n")
        
        f.write("2. RESULTADOS POR MÉTODO\n")
        f.write("-" * 80 + "\n\n")
        
        for i, (method, res) in enumerate(results.items(), 1):
            f.write(f"  {i}. {method.replace(chr(10), ' ')}\n")
            f.write(f"     Tipo: {res['tipo']}\n")
            f.write(f"     Tempo de execução: {res['tempo']:.4f} segundos\n")
            f.write(f"     Valor objetivo: {res['objetivo']:.2f}\n")
            if res['gap'] is not None:
                f.write(f"     Gap de otimalidade: {res['gap']:.6f}%\n")
            f.write("\n")
        
        f.write("3. ANÁLISE COMPARATIVA\n")
        f.write("-" * 80 + "\n\n")
        
        # Encontrar melhor
        best_method = min(results.items(), key=lambda x: x[1]['objetivo'])
        fastest_method = min(results.items(), key=lambda x: x[1]['tempo'])
        
        f.write(f"  ⭐ MELHOR SOLUÇÃO: {best_method[0].replace(chr(10), ' ')}\n")
        f.write(f"     Objetivo: {best_method[1]['objetivo']:.2f}\n\n")
        
        f.write(f"  ⚡ MÉTODO MAIS RÁPIDO: {fastest_method[0].replace(chr(10), ' ')}\n")
        f.write(f"     Tempo: {fastest_method[1]['tempo']:.4f}s\n\n")
        
        # Comparar qualidade vs tempo
        if 'Branch & Bound\n(Exato)' in results:
            optimal = results['Branch & Bound\n(Exato)']['objetivo']
            
            f.write("  📊 DESVIO EM RELAÇÃO AO ÓTIMO:\n")
            for method, res in results.items():
                if method != 'Branch & Bound\n(Exato)':
                    deviation = ((res['objetivo'] - optimal) / optimal) * 100
                    f.write(f"     {method.replace(chr(10), ' ')}: +{deviation:.2f}%\n")
            f.write("\n")
        
        f.write("4. CONCLUSÕES\n")
        f.write("-" * 80 + "\n\n")
        
        if 'Híbrido\n(SA + B&B)' in results:
            hybrid_res = results['Híbrido\n(SA + B&B)']
            exact_res = results.get('Branch & Bound\n(Exato)', None)
            
            if exact_res and abs(hybrid_res['objetivo'] - exact_res['objetivo']) < 1.0:
                f.write("  ✓ O método híbrido conseguiu atingir a solução ótima!\n")
                f.write(f"    Tempo total: {hybrid_res['tempo']:.2f}s\n\n")
            else:
                f.write("  ✓ O método híbrido oferece um bom compromisso tempo/qualidade.\n\n")
        
        f.write("  • Branch & Bound: Garante otimalidade mas pode ser lento.\n")
        f.write("  • Metaheurísticas: Rápidas mas não garantem otimalidade.\n")
        f.write("  • Híbrido: Combina velocidade inicial com refinamento exato.\n\n")
        
        f.write("="*80 + "\n")
        f.write("FIM DO RELATÓRIO\n")
        f.write("="*80 + "\n")
    
    print(f"  ✓ Relatório salvo: report.txt")


# Executar análise completa
if __name__ == "__main__":
    run_complete_comparison(
        data_file='/mnt/user-data/uploads/s0m0.dat',
        lambda1=0.5,
        lambda2=0.5,
        time_limit=180
    )
