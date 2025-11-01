"""
Análise em Batch: Processa múltiplos ficheiros .dat automaticamente.
Permite testar os 4 métodos em centenas/milhares de instâncias e agregar resultados.
"""

import os
import glob
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from data_parser import PatientAllocationData
from milp_model import PatientAllocationMILP
from metaheuristics import SimulatedAnnealing, TabuSearch
from hybrid_solver import HybridSolver


class BatchAnalyzer:
    """Processa múltiplos ficheiros .dat e agrega resultados."""
    
    def __init__(self, data_directory, output_directory='/mnt/user-data/outputs'):
        """
        Inicializa o analisador em batch.
        
        Args:
            data_directory: Diretório com os ficheiros .dat
            output_directory: Diretório para guardar resultados
        """
        self.data_dir = data_directory
        self.output_dir = output_directory
        self.results = []
        
        # Criar diretório de outputs se não existir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def find_dat_files(self, pattern='*.dat', max_files=None):
        """
        Encontra todos os ficheiros .dat no diretório.
        
        Args:
            pattern: Padrão para filtrar ficheiros (ex: 's0m*.dat')
            max_files: Limite máximo de ficheiros (None = todos)
        
        Returns:
            Lista de caminhos dos ficheiros
        """
        search_pattern = os.path.join(self.data_dir, pattern)
        files = sorted(glob.glob(search_pattern))
        
        if max_files:
            files = files[:max_files]
        
        print(f"📂 Encontrados {len(files)} ficheiros .dat")
        return files
    
    def process_single_file(self, filepath, methods=['bb', 'sa', 'tabu', 'hybrid'],
                           lambda1=0.5, lambda2=0.5, time_limit=300):
        """
        Processa um único ficheiro com os métodos selecionados.
        
        Args:
            filepath: Caminho para o ficheiro .dat
            methods: Lista de métodos a executar
            lambda1: Peso objetivo 1
            lambda2: Peso objetivo 2
            time_limit: Tempo limite por método
        
        Returns:
            Dict com resultados de todos os métodos
        """
        filename = os.path.basename(filepath)
        print(f"\n{'='*80}")
        print(f"Processando: {filename}")
        print(f"{'='*80}")
        
        # Carregar dados
        try:
            data = PatientAllocationData(filepath)
        except Exception as e:
            print(f"❌ Erro ao carregar {filename}: {e}")
            return None
        
        result = {
            'filename': filename,
            'num_patients': len(data.patients),
            'num_wards': len(data.wards),
            'num_days': data.num_days,
            'M': data.M  # Número de especializações menores
        }
        
        # Método 1: Branch & Bound
        if 'bb' in methods:
            print(f"\n🔹 Branch & Bound...")
            try:
                milp = PatientAllocationMILP(data, lambda1, lambda2)
                milp.build_model()
                bb_result = milp.solve(time_limit=time_limit, threads=4, verbose=False)
                
                if bb_result:
                    result['bb_time'] = bb_result['solve_time']
                    result['bb_objective'] = bb_result['objective_value']
                    result['bb_gap'] = bb_result['gap'] if bb_result['gap'] else 0
                    result['bb_status'] = 'optimal'
                    print(f"  ✓ Tempo: {bb_result['solve_time']:.2f}s | Obj: {bb_result['objective_value']:.2f}")
                else:
                    result['bb_time'] = time_limit
                    result['bb_objective'] = None
                    result['bb_status'] = 'timeout'
                    print(f"  ⚠️ Timeout")
            except Exception as e:
                print(f"  ❌ Erro: {e}")
                result['bb_time'] = None
                result['bb_objective'] = None
                result['bb_status'] = 'error'
        
        # Método 2: Simulated Annealing
        if 'sa' in methods:
            print(f"\n🔹 Simulated Annealing...")
            try:
                sa = SimulatedAnnealing(data, lambda1, lambda2)
                sa_result = sa.solve(max_iterations=10000, verbose=False)
                
                result['sa_time'] = sa_result['solve_time']
                result['sa_objective'] = sa_result['objective_value']
                result['sa_feasible'] = sa_result['feasible']
                print(f"  ✓ Tempo: {sa_result['solve_time']:.2f}s | Obj: {sa_result['objective_value']:.2f}")
            except Exception as e:
                print(f"  ❌ Erro: {e}")
                result['sa_time'] = None
                result['sa_objective'] = None
                result['sa_feasible'] = False
        
        # Método 3: Tabu Search
        if 'tabu' in methods:
            print(f"\n🔹 Tabu Search...")
            try:
                ts = TabuSearch(data, lambda1, lambda2)
                ts_result = ts.solve(max_iterations=5000, verbose=False)
                
                result['tabu_time'] = ts_result['solve_time']
                result['tabu_objective'] = ts_result['objective_value']
                result['tabu_feasible'] = ts_result['feasible']
                print(f"  ✓ Tempo: {ts_result['solve_time']:.2f}s | Obj: {ts_result['objective_value']:.2f}")
            except Exception as e:
                print(f"  ❌ Erro: {e}")
                result['tabu_time'] = None
                result['tabu_objective'] = None
                result['tabu_feasible'] = False
        
        # Método 4: Híbrido
        if 'hybrid' in methods:
            print(f"\n🔹 Híbrido (SA + B&B)...")
            try:
                hybrid = HybridSolver(data, lambda1, lambda2)
                hybrid_result = hybrid.solve(
                    metaheuristic='SA',
                    mh_max_iter=5000,
                    milp_time_limit=time_limit,
                    verbose=False
                )
                
                result['hybrid_time'] = hybrid_result['total_time']
                result['hybrid_objective'] = hybrid_result['final_obj']
                result['hybrid_mh_obj'] = hybrid_result['metaheuristic_obj']
                result['hybrid_improvement'] = hybrid_result['improvement_pct']
                print(f"  ✓ Tempo: {hybrid_result['total_time']:.2f}s | Obj: {hybrid_result['final_obj']:.2f}")
            except Exception as e:
                print(f"  ❌ Erro: {e}")
                result['hybrid_time'] = None
                result['hybrid_objective'] = None
        
        # Calcular desvios em relação ao ótimo (se disponível)
        if 'bb_objective' in result and result['bb_objective']:
            optimal = result['bb_objective']
            
            if 'sa_objective' in result and result['sa_objective']:
                result['sa_deviation'] = ((result['sa_objective'] - optimal) / optimal) * 100
            
            if 'tabu_objective' in result and result['tabu_objective']:
                result['tabu_deviation'] = ((result['tabu_objective'] - optimal) / optimal) * 100
            
            if 'hybrid_objective' in result and result['hybrid_objective']:
                result['hybrid_deviation'] = ((result['hybrid_objective'] - optimal) / optimal) * 100
        
        return result
    
    def run_batch_analysis(self, pattern='*.dat', max_files=None, 
                          methods=['bb', 'sa', 'hybrid'],
                          lambda1=0.5, lambda2=0.5, time_limit=300):
        """
        Executa análise em batch em múltiplos ficheiros.
        
        Args:
            pattern: Padrão de ficheiros a processar
            max_files: Número máximo de ficheiros (None = todos)
            methods: Métodos a executar
            lambda1, lambda2: Pesos dos objetivos
            time_limit: Tempo limite por método
        """
        print("="*80)
        print("ANÁLISE EM BATCH - MÚLTIPLOS FICHEIROS")
        print("="*80)
        
        # Encontrar ficheiros
        files = self.find_dat_files(pattern, max_files)
        
        if not files:
            print("❌ Nenhum ficheiro encontrado!")
            return
        
        print(f"\n📊 Métodos selecionados: {methods}")
        print(f"⏱️  Tempo limite por método: {time_limit}s")
        print(f"📈 Pesos: λ1={lambda1}, λ2={lambda2}")
        
        # Processar cada ficheiro
        start_time = time.time()
        
        for i, filepath in enumerate(files, 1):
            print(f"\n{'#'*80}")
            print(f"# Ficheiro {i}/{len(files)}")
            print(f"{'#'*80}")
            
            result = self.process_single_file(
                filepath, 
                methods=methods,
                lambda1=lambda1,
                lambda2=lambda2,
                time_limit=time_limit
            )
            
            if result:
                self.results.append(result)
        
        total_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("✓ ANÁLISE EM BATCH CONCLUÍDA!")
        print("="*80)
        print(f"Ficheiros processados: {len(self.results)}/{len(files)}")
        print(f"Tempo total: {total_time:.2f}s ({total_time/60:.1f} minutos)")
        print(f"Tempo médio por ficheiro: {total_time/len(files):.2f}s")
        
        # Gerar relatórios
        self.generate_reports()
    
    def generate_reports(self):
        """Gera relatórios e visualizações dos resultados agregados."""
        if not self.results:
            print("❌ Sem resultados para gerar relatórios!")
            return
        
        print("\n📊 Gerando relatórios...")
        
        # Converter para DataFrame
        df = pd.DataFrame(self.results)
        
        # Salvar CSV
        csv_path = os.path.join(self.output_dir, 'batch_results.csv')
        df.to_csv(csv_path, index=False)
        print(f"  ✓ CSV salvo: batch_results.csv")
        
        # Gerar estatísticas
        self._generate_statistics(df)
        
        # Gerar visualizações
        self._generate_visualizations(df)
        
        # Gerar relatório textual
        self._generate_text_report(df)
    
    def _generate_statistics(self, df):
        """Calcula e exibe estatísticas agregadas."""
        print("\n" + "="*80)
        print("ESTATÍSTICAS AGREGADAS")
        print("="*80)
        
        # Estatísticas por método
        methods = []
        if 'bb_time' in df.columns:
            methods.append(('Branch & Bound', 'bb'))
        if 'sa_time' in df.columns:
            methods.append(('Simulated Annealing', 'sa'))
        if 'tabu_time' in df.columns:
            methods.append(('Tabu Search', 'tabu'))
        if 'hybrid_time' in df.columns:
            methods.append(('Híbrido', 'hybrid'))
        
        for method_name, prefix in methods:
            print(f"\n{method_name}:")
            print("-" * 60)
            
            time_col = f'{prefix}_time'
            obj_col = f'{prefix}_objective'
            
            if time_col in df.columns:
                times = df[time_col].dropna()
                if len(times) > 0:
                    print(f"  Tempo médio: {times.mean():.2f}s (±{times.std():.2f}s)")
                    print(f"  Tempo min/max: {times.min():.2f}s / {times.max():.2f}s")
            
            if obj_col in df.columns:
                objs = df[obj_col].dropna()
                if len(objs) > 0:
                    print(f"  Objetivo médio: {objs.mean():.2f} (±{objs.std():.2f})")
            
            # Desvio do ótimo (se aplicável)
            dev_col = f'{prefix}_deviation'
            if dev_col in df.columns:
                devs = df[dev_col].dropna()
                if len(devs) > 0:
                    print(f"  Desvio médio do ótimo: {devs.mean():.2f}% (±{devs.std():.2f}%)")
                    print(f"  Desvio min/max: {devs.min():.2f}% / {devs.max():.2f}%")
    
    def _generate_visualizations(self, df):
        """Gera gráficos comparativos."""
        print("\n📊 Gerando visualizações...")
        
        # Gráfico 1: Boxplot de tempos
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Tempos
        time_data = []
        time_labels = []
        
        if 'bb_time' in df.columns:
            time_data.append(df['bb_time'].dropna())
            time_labels.append('B&B')
        if 'sa_time' in df.columns:
            time_data.append(df['sa_time'].dropna())
            time_labels.append('SA')
        if 'tabu_time' in df.columns:
            time_data.append(df['tabu_time'].dropna())
            time_labels.append('Tabu')
        if 'hybrid_time' in df.columns:
            time_data.append(df['hybrid_time'].dropna())
            time_labels.append('Híbrido')
        
        ax1 = axes[0]
        bp1 = ax1.boxplot(time_data, labels=time_labels, patch_artist=True)
        for patch in bp1['boxes']:
            patch.set_facecolor('lightblue')
        ax1.set_ylabel('Tempo (segundos)', fontweight='bold')
        ax1.set_title('Distribuição dos Tempos de Execução', fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # Desvios do ótimo
        if 'sa_deviation' in df.columns or 'tabu_deviation' in df.columns:
            dev_data = []
            dev_labels = []
            
            if 'sa_deviation' in df.columns:
                dev_data.append(df['sa_deviation'].dropna())
                dev_labels.append('SA')
            if 'tabu_deviation' in df.columns:
                dev_data.append(df['tabu_deviation'].dropna())
                dev_labels.append('Tabu')
            if 'hybrid_deviation' in df.columns:
                dev_data.append(df['hybrid_deviation'].dropna())
                dev_labels.append('Híbrido')
            
            ax2 = axes[1]
            bp2 = ax2.boxplot(dev_data, labels=dev_labels, patch_artist=True)
            for patch in bp2['boxes']:
                patch.set_facecolor('lightcoral')
            ax2.set_ylabel('Desvio do Ótimo (%)', fontweight='bold')
            ax2.set_title('Qualidade da Solução (vs Ótimo)', fontweight='bold')
            ax2.axhline(y=0, color='green', linestyle='--', linewidth=2, label='Ótimo')
            ax2.legend()
            ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'batch_comparison.png'), dpi=150)
        print(f"  ✓ Gráfico salvo: batch_comparison.png")
        plt.close()
        
        # Gráfico 2: Scatter plot tamanho do problema vs tempo
        if 'bb_time' in df.columns and 'hybrid_time' in df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ax.scatter(df['num_patients'], df['bb_time'], 
                      label='Branch & Bound', alpha=0.6, s=50)
            ax.scatter(df['num_patients'], df['hybrid_time'], 
                      label='Híbrido', alpha=0.6, s=50)
            
            ax.set_xlabel('Número de Pacientes', fontweight='bold')
            ax.set_ylabel('Tempo (segundos)', fontweight='bold')
            ax.set_title('Escalabilidade: Tempo vs Tamanho do Problema', fontweight='bold')
            ax.legend()
            ax.grid(alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'scalability.png'), dpi=150)
            print(f"  ✓ Gráfico salvo: scalability.png")
            plt.close()
    
    def _generate_text_report(self, df):
        """Gera relatório textual detalhado."""
        report_path = os.path.join(self.output_dir, 'batch_report.txt')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("RELATÓRIO DE ANÁLISE EM BATCH\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Número de instâncias processadas: {len(df)}\n")
            f.write(f"Métodos testados: {[col.replace('_time', '') for col in df.columns if '_time' in col]}\n\n")
            
            f.write("ESTATÍSTICAS AGREGADAS\n")
            f.write("-" * 80 + "\n\n")
            
            # Resumo por método
            methods = []
            if 'bb_time' in df.columns:
                methods.append(('Branch & Bound', 'bb'))
            if 'sa_time' in df.columns:
                methods.append(('Simulated Annealing', 'sa'))
            if 'tabu_time' in df.columns:
                methods.append(('Tabu Search', 'tabu'))
            if 'hybrid_time' in df.columns:
                methods.append(('Híbrido', 'hybrid'))
            
            for method_name, prefix in methods:
                f.write(f"{method_name}:\n")
                
                time_col = f'{prefix}_time'
                obj_col = f'{prefix}_objective'
                dev_col = f'{prefix}_deviation'
                
                if time_col in df.columns:
                    times = df[time_col].dropna()
                    if len(times) > 0:
                        f.write(f"  Tempo médio: {times.mean():.2f}s (±{times.std():.2f})\n")
                        f.write(f"  Tempo mediano: {times.median():.2f}s\n")
                
                if obj_col in df.columns:
                    objs = df[obj_col].dropna()
                    if len(objs) > 0:
                        f.write(f"  Objetivo médio: {objs.mean():.2f}\n")
                
                if dev_col in df.columns:
                    devs = df[dev_col].dropna()
                    if len(devs) > 0:
                        f.write(f"  Desvio médio: {devs.mean():.2f}%\n")
                        f.write(f"  Instâncias ótimas: {(devs == 0).sum()}/{len(devs)}\n")
                
                f.write("\n")
            
            f.write("="*80 + "\n")
        
        print(f"  ✓ Relatório salvo: batch_report.txt")


# Script de exemplo
if __name__ == "__main__":
    # Configuração
    DATA_DIR = '/mnt/user-data/uploads'  # Diretório com os ficheiros .dat
    OUTPUT_DIR = '/mnt/user-data/outputs'
    
    # Criar analisador
    analyzer = BatchAnalyzer(DATA_DIR, OUTPUT_DIR)
    
    # OPÇÃO 1: Testar com poucos ficheiros primeiro (recomendado)
    print("TESTE COM POUCOS FICHEIROS (5 instâncias)")
    analyzer.run_batch_analysis(
        pattern='*.dat',
        max_files=5,  # Apenas 5 ficheiros para teste
        methods=['bb', 'sa', 'hybrid'],  # Excluir Tabu por ser lento
        lambda1=0.5,
        lambda2=0.5,
        time_limit=120  # 2 minutos por método
    )
    
    # OPÇÃO 2: Processar TODOS os ficheiros (comentado por segurança)
    # CUIDADO: Pode demorar HORAS!
    # analyzer.run_batch_analysis(
    #     pattern='*.dat',
    #     max_files=None,  # TODOS os ficheiros
    #     methods=['bb', 'sa', 'hybrid'],
    #     lambda1=0.5,
    #     lambda2=0.5,
    #     time_limit=300
    # )
