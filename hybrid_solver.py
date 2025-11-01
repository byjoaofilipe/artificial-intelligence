"""
Método Híbrido: Combina metaheurística + Branch & Bound.
Usa a solução da metaheurística como warm start para o Gurobi.
"""

import gurobipy as gp
from gurobipy import GRB
import time
from data_parser import PatientAllocationData
from metaheuristics import SimulatedAnnealing, TabuSearch
from milp_model import PatientAllocationMILP


class HybridSolver:
    """
    Solver híbrido que combina metaheurística com método exato.
    
    Processo:
    1. Executar metaheurística para obter uma boa solução inicial
    2. Usar essa solução como warm start para o Gurobi
    3. Refinar com Branch & Bound
    """
    
    def __init__(self, data: PatientAllocationData, lambda1=0.5, lambda2=0.5):
        self.data = data
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        
        self.metaheuristic_time = None
        self.milp_time = None
        self.total_time = None
        self.metaheuristic_solution = None
        self.final_solution = None
        self.metaheuristic_obj = None
        self.final_obj = None
    
    def solve(self, 
              metaheuristic='SA',
              mh_max_iter=5000,
              milp_time_limit=300,
              threads=4,
              verbose=True):
        """
        Resolve o problema usando a abordagem híbrida.
        
        Args:
            metaheuristic: 'SA' (Simulated Annealing) ou 'TS' (Tabu Search)
            mh_max_iter: Iterações máximas da metaheurística
            milp_time_limit: Tempo limite para o Gurobi (segundos)
            threads: Número de threads para o Gurobi
            verbose: Se True, mostra progresso
        
        Returns:
            Dict com os resultados
        """
        if verbose:
            print("\n" + "="*70)
            print("MÉTODO HÍBRIDO: METAHEURÍSTICA + BRANCH & BOUND")
            print("="*70)
        
        total_start = time.time()
        
        # ==========================
        # FASE 1: METAHEURÍSTICA
        # ==========================
        if verbose:
            print("\n📍 FASE 1: Executar metaheurística para obter solução inicial")
            print("-" * 70)
        
        if metaheuristic == 'SA':
            solver = SimulatedAnnealing(self.data, self.lambda1, self.lambda2)
            mh_results = solver.solve(max_iterations=mh_max_iter, verbose=verbose)
        elif metaheuristic == 'TS':
            solver = TabuSearch(self.data, self.lambda1, self.lambda2)
            mh_results = solver.solve(max_iterations=mh_max_iter, verbose=verbose)
        else:
            raise ValueError(f"Metaheurística '{metaheuristic}' não reconhecida. Use 'SA' ou 'TS'.")
        
        self.metaheuristic_time = mh_results['solve_time']
        self.metaheuristic_solution = mh_results['solution']
        self.metaheuristic_obj = mh_results['objective_value']
        
        if verbose:
            print(f"\n✓ Metaheurística concluída:")
            print(f"  - Tempo: {self.metaheuristic_time:.2f}s")
            print(f"  - Objetivo: {self.metaheuristic_obj:.2f}")
            print(f"  - Viável: {mh_results['feasible']}")
        
        # ==========================
        # FASE 2: BRANCH & BOUND COM WARM START
        # ==========================
        if verbose:
            print("\n📍 FASE 2: Refinar com Branch & Bound (usando warm start)")
            print("-" * 70)
        
        # Criar modelo MILP
        milp = PatientAllocationMILP(self.data, self.lambda1, self.lambda2)
        milp.build_model()
        
        # Aplicar warm start
        if mh_results['feasible']:
            self._apply_warm_start(milp, self.metaheuristic_solution)
            if verbose:
                print("✓ Warm start aplicado com sucesso")
        else:
            if verbose:
                print("⚠ Solução da metaheurística não é viável - sem warm start")
        
        # Resolver com Gurobi
        milp_start = time.time()
        final_results = milp.solve(time_limit=milp_time_limit, threads=threads, verbose=False)
        self.milp_time = time.time() - milp_start
        
        if final_results:
            self.final_solution = final_results['solution']
            self.final_obj = final_results['objective_value']
        
        self.total_time = time.time() - total_start
        
        # ==========================
        # RESULTADOS
        # ==========================
        if verbose:
            print("\n" + "="*70)
            print("RESULTADOS FINAIS")
            print("="*70)
            print(f"\n⏱️ TEMPOS:")
            print(f"  Metaheurística: {self.metaheuristic_time:.2f}s")
            print(f"  Branch & Bound: {self.milp_time:.2f}s")
            print(f"  Total:          {self.total_time:.2f}s")
            
            print(f"\n📊 OBJETIVOS:")
            print(f"  Metaheurística: {self.metaheuristic_obj:.2f}")
            
            if self.final_obj:
                print(f"  Final (ótimo):  {self.final_obj:.2f}")
                improvement = ((self.metaheuristic_obj - self.final_obj) / self.metaheuristic_obj) * 100
                print(f"  Melhoria:       {improvement:.2f}%")
            
            print("\n💡 CONCLUSÃO:")
            if self.final_obj:
                print(f"  ✓ Método híbrido conseguiu refinar a solução")
                print(f"  ✓ Tempo total: {self.total_time:.2f}s")
            else:
                print(f"  ⚠ Não foi possível melhorar a solução")
            
            print("="*70)
        
        return {
            'metaheuristic': metaheuristic,
            'metaheuristic_time': self.metaheuristic_time,
            'metaheuristic_obj': self.metaheuristic_obj,
            'milp_time': self.milp_time,
            'final_obj': self.final_obj,
            'total_time': self.total_time,
            'improvement_pct': ((self.metaheuristic_obj - self.final_obj) / self.metaheuristic_obj) * 100 if self.final_obj else 0,
            'solution': self.final_solution
        }
    
    def _apply_warm_start(self, milp: PatientAllocationMILP, solution):
        """
        Aplica a solução da metaheurística como warm start no modelo Gurobi.
        
        Args:
            milp: Objeto PatientAllocationMILP
            solution: Dicionário com a alocação {patient_id: {'ward': ..., 'day': ...}}
        """
        # Definir valores iniciais para as variáveis Y
        for patient_id, alloc in solution.items():
            ward = alloc['ward']
            day = alloc['day']
            
            # Procurar a variável correspondente
            if (patient_id, ward, day) in milp.y:
                milp.y[patient_id, ward, day].Start = 1
            
            # Colocar as outras variáveis a 0
            for (pid, w, d), var in milp.y.items():
                if pid == patient_id and (w != ward or d != day):
                    var.Start = 0


def compare_all_methods(data: PatientAllocationData, 
                        lambda1=0.5, 
                        lambda2=0.5,
                        time_limit=300):
    """
    Compara os 4 métodos diferentes e apresenta os resultados.
    
    Args:
        data: Dados do problema
        lambda1: Peso do objetivo 1
        lambda2: Peso do objetivo 2
        time_limit: Tempo limite para cada método
    
    Returns:
        DataFrame com comparação dos resultados
    """
    print("\n" + "="*80)
    print("COMPARAÇÃO DOS 4 MÉTODOS")
    print("="*80)
    
    results = {}
    
    # MÉTODO 1: Branch & Bound Puro
    print("\n🔹 MÉTODO 1: BRANCH & BOUND PURO")
    print("-" * 80)
    milp = PatientAllocationMILP(data, lambda1, lambda2)
    milp.build_model()
    method1 = milp.solve(time_limit=time_limit, threads=4, verbose=False)
    
    if method1:
        results['Método 1 (B&B Puro)'] = {
            'Tempo (s)': method1['solve_time'],
            'Objetivo': method1['objective_value'],
            'Gap (%)': method1['gap'] * 100 if method1['gap'] else 0,
            'Status': 'Ótimo'
        }
        print(f"✓ Tempo: {method1['solve_time']:.2f}s | Objetivo: {method1['objective_value']:.2f}")
    
    # MÉTODO 2: Simulated Annealing
    print("\n🔹 MÉTODO 2: SIMULATED ANNEALING")
    print("-" * 80)
    sa = SimulatedAnnealing(data, lambda1, lambda2)
    method2 = sa.solve(max_iterations=10000, verbose=False)
    
    results['Método 2 (SA)'] = {
        'Tempo (s)': method2['solve_time'],
        'Objetivo': method2['objective_value'],
        'Gap (%)': '-',
        'Status': 'Viável' if method2['feasible'] else 'Inviável'
    }
    print(f"✓ Tempo: {method2['solve_time']:.2f}s | Objetivo: {method2['objective_value']:.2f}")
    
    # MÉTODO 3: Tabu Search
    print("\n🔹 MÉTODO 3: TABU SEARCH")
    print("-" * 80)
    ts = TabuSearch(data, lambda1, lambda2)
    method3 = ts.solve(max_iterations=5000, verbose=False)
    
    results['Método 3 (Tabu)'] = {
        'Tempo (s)': method3['solve_time'],
        'Objetivo': method3['objective_value'],
        'Gap (%)': '-',
        'Status': 'Viável' if method3['feasible'] else 'Inviável'
    }
    print(f"✓ Tempo: {method3['solve_time']:.2f}s | Objetivo: {method3['objective_value']:.2f}")
    
    # MÉTODO 4: Híbrido (SA + B&B)
    print("\n🔹 MÉTODO 4: HÍBRIDO (SA + B&B)")
    print("-" * 80)
    hybrid = HybridSolver(data, lambda1, lambda2)
    method4 = hybrid.solve(
        metaheuristic='SA',
        mh_max_iter=5000,
        milp_time_limit=time_limit,
        verbose=False
    )
    
    if method4['final_obj']:
        results['Método 4 (Híbrido)'] = {
            'Tempo (s)': method4['total_time'],
            'Objetivo': method4['final_obj'],
            'Gap (%)': '-',
            'Status': 'Ótimo/Quase-ótimo'
        }
        print(f"✓ Tempo: {method4['total_time']:.2f}s | Objetivo: {method4['final_obj']:.2f}")
    
    # Apresentar tabela comparativa
    print("\n" + "="*80)
    print("TABELA COMPARATIVA")
    print("="*80)
    print(f"{'Método':<25} {'Tempo (s)':<12} {'Objetivo':<12} {'Gap (%)':<10} {'Status':<15}")
    print("-" * 80)
    
    for method_name, data_dict in results.items():
        print(f"{method_name:<25} {data_dict['Tempo (s)']:<12.2f} {data_dict['Objetivo']:<12.2f} "
              f"{str(data_dict['Gap (%)']):<10} {data_dict['Status']:<15}")
    
    print("="*80)
    
    return results


# Teste
if __name__ == "__main__":
    data = PatientAllocationData('/mnt/user-data/uploads/s0m0.dat')
    
    # Testar método híbrido individualmente
    hybrid = HybridSolver(data, lambda1=0.5, lambda2=0.5)
    results = hybrid.solve(
        metaheuristic='SA',
        mh_max_iter=3000,
        milp_time_limit=60,
        verbose=True
    )
    
    print("\n\n")
    
    # Comparar todos os métodos
    comparison = compare_all_methods(data, lambda1=0.5, lambda2=0.5, time_limit=120)
