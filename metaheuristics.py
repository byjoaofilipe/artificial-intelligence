"""
Metaheurísticas para o problema de alocação de pacientes.
Implementa Simulated Annealing e Tabu Search (Métodos 2 e 3).
"""

import random
import math
import time
import copy
from data_parser import PatientAllocationData


class Solution:
    """Representa uma solução do problema."""
    
    def __init__(self, data: PatientAllocationData):
        self.data = data
        self.allocation = {}  # {patient_id: {'ward': ward_name, 'day': day}}
        self.objective_value = float('inf')
        self.feasible = False
        
    def copy(self):
        """Cria uma cópia da solução."""
        new_sol = Solution(self.data)
        new_sol.allocation = copy.deepcopy(self.allocation)
        new_sol.objective_value = self.objective_value
        new_sol.feasible = self.feasible
        return new_sol
    
    def evaluate(self, lambda1=0.5, lambda2=0.5):
        """
        Calcula o valor objetivo da solução.
        Verifica também se a solução é viável.
        """
        # Verificar viabilidade e calcular objetivo
        if not self._check_feasibility():
            self.feasible = False
            self.objective_value = float('inf')
            return self.objective_value
        
        self.feasible = True
        
        # Calcular objetivo 1: custo operacional
        f1 = self._calculate_operational_cost()
        
        # Calcular objetivo 2: equilíbrio de carga
        f2 = self._calculate_workload_balance()
        
        self.objective_value = lambda1 * f1 + lambda2 * f2
        return self.objective_value
    
    def _check_feasibility(self):
        """Verifica se a solução respeita todas as restrições."""
        
        # 1. Verificar se todos os pacientes foram alocados
        if len(self.allocation) != len(self.data.patients):
            return False
        
        # 2. Verificar janelas temporais
        for patient_id, alloc in self.allocation.items():
            patient = self.data.patients[patient_id]
            if not (patient['earliest'] <= alloc['day'] <= patient['latest']):
                return False
        
        # 3. Verificar capacidade de camas
        for ward_name, ward in self.data.wards.items():
            for d in range(self.data.num_days):
                patients_count = ward['carryover_patients'][d]
                
                for patient_id, alloc in self.allocation.items():
                    if alloc['ward'] == ward_name:
                        patient = self.data.patients[patient_id]
                        admit_day = alloc['day']
                        los = patient['los']
                        
                        # Paciente está na enfermaria no dia d?
                        if admit_day <= d < admit_day + los:
                            patients_count += 1
                
                if patients_count > ward['bed_capacity']:
                    return False
        
        # 4. Verificar compatibilidade enfermaria-especialização
        for patient_id, alloc in self.allocation.items():
            patient = self.data.patients[patient_id]
            spec = patient['specialization']
            ward = self.data.wards[alloc['ward']]
            
            if spec != ward['major_specialization'] and spec not in ward['minor_specializations']:
                return False
        
        return True
    
    def _calculate_operational_cost(self):
        """Calcula o custo operacional (delays + overtime + undertime)."""
        cost = 0.0
        
        # 1. Calcular delays
        for patient_id, alloc in self.allocation.items():
            patient = self.data.patients[patient_id]
            delay = alloc['day'] - patient['earliest']
            cost += self.data.weight_delay * delay
        
        # 2. Calcular overtime e undertime por especialização e dia
        for spec in self.data.specialisms.keys():
            for d in range(self.data.num_days):
                ot_used = 0
                
                # Somar duração das cirurgias no dia d
                for patient_id, alloc in self.allocation.items():
                    patient = self.data.patients[patient_id]
                    if patient['specialization'] == spec and alloc['day'] == d:
                        ot_used += patient['surgery_duration']
                
                ot_available = self.data.specialisms[spec]['ot_time'][d]
                
                if ot_used > ot_available:
                    overtime = ot_used - ot_available
                    cost += self.data.weight_overtime * overtime
                else:
                    undertime = ot_available - ot_used
                    cost += self.data.weight_undertime * undertime
        
        return cost
    
    def _calculate_workload_balance(self):
        """Calcula o máximo da carga de trabalho normalizada (objetivo de equilíbrio)."""
        max_workload = 0.0
        
        for ward_name, ward in self.data.wards.items():
            workload_capacity = ward['workload_capacity']
            
            for d in range(self.data.num_days):
                # Carga pré-existente
                total_workload = ward['carryover_workload'][d]
                
                # Adicionar carga dos pacientes alocados
                for patient_id, alloc in self.allocation.items():
                    if alloc['ward'] == ward_name:
                        patient = self.data.patients[patient_id]
                        admit_day = alloc['day']
                        los = patient['los']
                        
                        # Paciente está internado no dia d?
                        if admit_day <= d < admit_day + los:
                            day_of_stay = d - admit_day
                            workload = patient['workload_per_day'][day_of_stay]
                            
                            # Aplicar fator se for especialização menor
                            spec = patient['specialization']
                            if spec != ward['major_specialization'] and spec in ward['minor_specializations']:
                                workload *= self.data.specialisms[spec]['workload_factor']
                            
                            total_workload += workload
                
                # Normalizar
                normalized_workload = total_workload / workload_capacity
                max_workload = max(max_workload, normalized_workload)
        
        return max_workload


class SimulatedAnnealing:
    """Implementação de Simulated Annealing."""
    
    def __init__(self, data: PatientAllocationData, lambda1=0.5, lambda2=0.5):
        self.data = data
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        
        self.best_solution = None
        self.solve_time = None
    
    def _generate_initial_solution(self):
        """Gera uma solução inicial viável (greedy heuristic)."""
        solution = Solution(self.data)
        
        # Ordenar pacientes por janela temporal (urgentes primeiro)
        patients = sorted(
            self.data.patients.items(),
            key=lambda x: (x[1]['latest'] - x[1]['earliest'], x[1]['earliest'])
        )
        
        for patient_id, patient in patients:
            spec = patient['specialization']
            earliest = patient['earliest']
            latest = patient['latest']
            
            # Encontrar enfermaria compatível
            compatible_wards = []
            for ward_name, ward in self.data.wards.items():
                if spec == ward['major_specialization'] or spec in ward['minor_specializations']:
                    compatible_wards.append(ward_name)
            
            # Tentar alocar no primeiro dia possível
            allocated = False
            for d in range(earliest, latest + 1):
                if d >= self.data.num_days:
                    break
                
                for ward_name in compatible_wards:
                    # Verificar se tem capacidade (simplificado)
                    solution.allocation[patient_id] = {'ward': ward_name, 'day': d}
                    
                    if solution._check_feasibility():
                        allocated = True
                        break
                
                if allocated:
                    break
            
            # Se não conseguiu alocar, forçar alocação (pode ficar inviável)
            if not allocated:
                solution.allocation[patient_id] = {
                    'ward': compatible_wards[0],
                    'day': earliest
                }
        
        solution.evaluate(self.lambda1, self.lambda2)
        return solution
    
    def _get_neighbor(self, solution):
        """Gera uma solução vizinha fazendo pequenas modificações."""
        neighbor = solution.copy()
        
        # Escolher paciente aleatório
        patient_id = random.choice(list(neighbor.allocation.keys()))
        patient = self.data.patients[patient_id]
        
        # Tentar uma das três operações
        operation = random.choice(['change_day', 'change_ward', 'swap'])
        
        if operation == 'change_day':
            # Mudar o dia de admissão
            new_day = random.randint(patient['earliest'], patient['latest'])
            if new_day < self.data.num_days:
                neighbor.allocation[patient_id]['day'] = new_day
        
        elif operation == 'change_ward':
            # Mudar de enfermaria (se possível)
            spec = patient['specialization']
            compatible_wards = [
                w for w, ward in self.data.wards.items()
                if spec == ward['major_specialization'] or spec in ward['minor_specializations']
            ]
            if len(compatible_wards) > 1:
                current_ward = neighbor.allocation[patient_id]['ward']
                compatible_wards.remove(current_ward)
                neighbor.allocation[patient_id]['ward'] = random.choice(compatible_wards)
        
        elif operation == 'swap':
            # Trocar dias de dois pacientes
            patient_id2 = random.choice(list(neighbor.allocation.keys()))
            if patient_id != patient_id2:
                day1 = neighbor.allocation[patient_id]['day']
                day2 = neighbor.allocation[patient_id2]['day']
                neighbor.allocation[patient_id]['day'] = day2
                neighbor.allocation[patient_id2]['day'] = day1
        
        neighbor.evaluate(self.lambda1, self.lambda2)
        return neighbor
    
    def solve(self, max_iterations=10000, initial_temp=1000, cooling_rate=0.95, verbose=True):
        """
        Resolve o problema usando Simulated Annealing.
        
        Args:
            max_iterations: Número máximo de iterações
            initial_temp: Temperatura inicial
            cooling_rate: Taxa de arrefecimento
            verbose: Se True, mostra progresso
        """
        if verbose:
            print("\n" + "="*60)
            print("SIMULATED ANNEALING")
            print("="*60)
        
        start_time = time.time()
        
        # Gerar solução inicial
        current = self._generate_initial_solution()
        self.best_solution = current.copy()
        
        if verbose:
            print(f"Solução inicial: {current.objective_value:.2f} (viável: {current.feasible})")
        
        temperature = initial_temp
        
        for iteration in range(max_iterations):
            # Gerar vizinho
            neighbor = self._get_neighbor(current)
            
            # Aceitar ou rejeitar
            delta = neighbor.objective_value - current.objective_value
            
            if delta < 0 or (temperature > 0 and random.random() < math.exp(-delta / temperature)):
                current = neighbor
                
                # Atualizar melhor solução
                if current.objective_value < self.best_solution.objective_value:
                    self.best_solution = current.copy()
                    if verbose and iteration % 1000 == 0:
                        print(f"Iteração {iteration}: Nova melhor solução = {self.best_solution.objective_value:.2f}")
            
            # Arrefecer
            temperature *= cooling_rate
            
            # Critério de paragem
            if temperature < 0.01:
                break
        
        self.solve_time = time.time() - start_time
        
        if verbose:
            print(f"\n✓ Concluído em {self.solve_time:.2f}s")
            print(f"Melhor solução: {self.best_solution.objective_value:.2f}")
            print(f"Viável: {self.best_solution.feasible}")
        
        return {
            'objective_value': self.best_solution.objective_value,
            'solve_time': self.solve_time,
            'solution': self.best_solution.allocation,
            'feasible': self.best_solution.feasible
        }


class TabuSearch:
    """Implementação de Tabu Search."""
    
    def __init__(self, data: PatientAllocationData, lambda1=0.5, lambda2=0.5):
        self.data = data
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        
        self.best_solution = None
        self.solve_time = None
    
    def solve(self, max_iterations=5000, tabu_tenure=50, verbose=True):
        """
        Resolve o problema usando Tabu Search.
        
        Args:
            max_iterations: Número máximo de iterações
            tabu_tenure: Duração da lista tabu
            verbose: Se True, mostra progresso
        """
        if verbose:
            print("\n" + "="*60)
            print("TABU SEARCH")
            print("="*60)
        
        start_time = time.time()
        
        # Usar SA para gerar solução inicial
        sa = SimulatedAnnealing(self.data, self.lambda1, self.lambda2)
        current = sa._generate_initial_solution()
        self.best_solution = current.copy()
        
        tabu_list = []
        
        if verbose:
            print(f"Solução inicial: {current.objective_value:.2f}")
        
        for iteration in range(max_iterations):
            # Gerar vizinhança
            neighbors = []
            for _ in range(20):  # Gerar 20 vizinhos
                neighbor = sa._get_neighbor(current)
                neighbors.append(neighbor)
            
            # Ordenar por qualidade
            neighbors.sort(key=lambda x: x.objective_value)
            
            # Escolher melhor vizinho não-tabu
            for neighbor in neighbors:
                move = str(neighbor.allocation)
                
                if move not in tabu_list or neighbor.objective_value < self.best_solution.objective_value:
                    current = neighbor
                    tabu_list.append(move)
                    
                    # Manter tamanho da lista tabu
                    if len(tabu_list) > tabu_tenure:
                        tabu_list.pop(0)
                    
                    # Atualizar melhor
                    if current.objective_value < self.best_solution.objective_value:
                        self.best_solution = current.copy()
                        if verbose and iteration % 500 == 0:
                            print(f"Iteração {iteration}: Nova melhor = {self.best_solution.objective_value:.2f}")
                    
                    break
        
        self.solve_time = time.time() - start_time
        
        if verbose:
            print(f"\n✓ Concluído em {self.solve_time:.2f}s")
            print(f"Melhor solução: {self.best_solution.objective_value:.2f}")
        
        return {
            'objective_value': self.best_solution.objective_value,
            'solve_time': self.solve_time,
            'solution': self.best_solution.allocation,
            'feasible': self.best_solution.feasible
        }


# Teste
if __name__ == "__main__":
    data = PatientAllocationData('/mnt/user-data/uploads/s0m0.dat')
    
    # Testar SA
    sa = SimulatedAnnealing(data, lambda1=0.5, lambda2=0.5)
    sa_results = sa.solve(max_iterations=5000)
    
    # Testar Tabu
    ts = TabuSearch(data, lambda1=0.5, lambda2=0.5)
    ts_results = ts.solve(max_iterations=3000)
