"""
Benchmark and Comparison Script for Patient Allocation Algorithms

This script runs three different algorithms on multiple datasets and generates
comparison plots for objective values and running times.

Usage:
    python benchmark_comparison.py -d dataset1.dat dataset2.dat dataset3.dat
    python benchmark_comparison.py -d data/*.dat --lambda1 0.5 --lambda2 0.5
"""

import argparse
import sys
import os
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Import the algorithm modules
from data_parser import PatientAllocationData
from CBC_milp import PatientAllocationMILP_CBC
from metaheuristics import (
    run_metaheuristics,
    run_metaheuristics_no_opt,
    greedy_feasible_by_window_strict,
    greedy_local_improvement,
    IteratedLocalSearch,
    VariableNeighborhoodSearch,
    objective_value
)
from Hybrid_solver import HybridSolverCBC


class BenchmarkRunner:
    """
    Run benchmarks for all three algorithms across multiple datasets.
    """
    
    def __init__(self, datasets, lambda1=0.5, lambda2=0.5, output_dir="output"):
        """
        Initialize the benchmark runner.
        
        Args:
            datasets: List of paths to .dat files
            lambda1: Weight for objective 1
            lambda2: Weight for objective 2
            output_dir: Directory to save output plots
        """
        self.datasets = datasets
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.results = {
            'dataset_names': [],
            'milp_cbc': {'objectives': [], 'times': [], 'status': []},
            'metaheuristics_ILS': {'objectives': [], 'times': []},
            'metaheuristics_VNS': {'objectives': [], 'times': []},
            'metaheuristics_no_opt_ILS': {'objectives': [], 'times': []},
            'metaheuristics_no_opt_VNS': {'objectives': [], 'times': []},
            'hybrid': {'objectives': [], 'times': [], 'best_method': []}
        }
    
    def run_all(self, 
                milp_time_limit=300,
                mh_ils_time=3,
                mh_vns_time=3,
                hybrid_mh_time=3,
                hybrid_milp_time=180,
                threads=4):
        """
        Run all three algorithms on all datasets.
        
        Args:
            milp_time_limit: Time limit for pure MILP (seconds)
            mh_ils_time: Time for ILS in metaheuristics (minutes)
            mh_vns_time: Time for VNS in metaheuristics (minutes)
            hybrid_mh_time: Time for metaheuristic phase in hybrid (minutes)
            hybrid_milp_time: Time for MILP phase in hybrid (seconds)
            threads: Number of threads for solvers
        """
        print("\n" + "=" * 80)
        print("BENCHMARK: COMPARING THREE ALGORITHMS")
        print("=" * 80)
        print(f"Datasets: {len(self.datasets)}")
        print(f"Algorithms: MILP-CBC, Metaheuristics (ILS+VNS), Hybrid (MH+MILP)")
        print(f"Weights: λ1={self.lambda1}, λ2={self.lambda2}")
        print("=" * 80)
        
        for i, dataset_path in enumerate(self.datasets):
            dataset_name = Path(dataset_path).stem
            print(f"\n{'=' * 80}")
            print(f"DATASET {i+1}/{len(self.datasets)}: {dataset_name}")
            print(f"{'=' * 80}")
            
            try:
                # Load data
                print(f"\n📂 Loading data from '{dataset_path}'...")
                data = PatientAllocationData(dataset_path)
                print(f"✓ Loaded: {len(data.patients)} patients, {len(data.wards)} wards, {data.num_days} days")
                
                self.results['dataset_names'].append(dataset_name)
                
                # Algorithm 1: Pure MILP with CBC
                print(f"\n{'─' * 80}")
                print("ALGORITHM 1: MILP (CBC)")
                print(f"{'─' * 80}")
                milp_result = self._run_milp_cbc(data, milp_time_limit, threads)
                
                # Algorithm 2: Metaheuristics (Greedy + Local + ILS + VNS)
                print(f"\n{'─' * 80}")
                print("ALGORITHM 2: METAHEURISTICS (ILS + VNS)")
                print(f"{'─' * 80}")
                mh_result = run_metaheuristics(data, mh_ils_time, mh_vns_time)

                # Algorithm 3: Metaheuristics NO-OPT(Greedy + ILS + VNS)
                print(f"\n{'─' * 80}")
                print("ALGORITHM 3: METAHEURISTICS NO-OPT (ILS + VNS)")
                print(f"{'─' * 80}")
                mh_no_opt_result = run_metaheuristics_no_opt(data, mh_ils_time, mh_vns_time)
                
                # Algorithm 4: Hybrid (Metaheuristics + MILP with warm start)
                print(f"\n{'─' * 80}")
                print("ALGORITHM 4: HYBRID (Metaheuristics + MILP)")
                print(f"{'─' * 80}")
                hybrid_result = self._run_hybrid(data, hybrid_mh_time, hybrid_milp_time, threads)
                
                # Store results
                self._store_results(milp_result, mh_result, mh_no_opt_result, hybrid_result)
                
                # Print comparison for this dataset
                self._print_dataset_comparison(dataset_name, milp_result, mh_result, mh_no_opt_result, hybrid_result)
                
            except Exception as e:
                print(f"\n❌ ERROR processing dataset '{dataset_name}': {e}")
                import traceback
                traceback.print_exc()
                # Store None values for failed datasets
                self.results['milp_cbc']['objectives'].append(None)
                self.results['milp_cbc']['times'].append(None)
                self.results['milp_cbc']['status'].append('ERROR')
                self.results['metaheuristics_ILS']['objectives'].append(None)
                self.results['metaheuristics_ILS']['times'].append(None)
                self.results['metaheuristics_VNS']['objectives'].append(None)
                self.results['metaheuristics_VNS']['times'].append(None)
                self.results['metaheuristics_no_opt_ILS']['objectives'].append(None)
                self.results['metaheuristics_no_opt_ILS']['times'].append(None)
                self.results['metaheuristics_no_opt_VNS']['objectives'].append(None)
                self.results['metaheuristics_no_opt_VNS']['times'].append(None)
                self.results['hybrid']['objectives'].append(None)
                self.results['hybrid']['times'].append(None)
                self.results['hybrid']['best_method'].append('ERROR')
        
        # Generate comparison plots
        print(f"\n{'=' * 80}")
        print("GENERATING COMPARISON PLOTS")
        print(f"{'=' * 80}")
        self._generate_plots()
        
        # Print final summary
        self._print_final_summary()
    
    def _run_milp_cbc(self, data, time_limit, threads):
        """Run pure MILP solver with CBC."""
        print("Running MILP-CBC solver...")
        
        try:
            model = PatientAllocationMILP_CBC(data, self.lambda1, self.lambda2)
            model.build_model()
            
            start_time = time.time()
            results = model.solve(time_limit=time_limit, threads=threads, verbose=False)
            elapsed = time.time() - start_time
            
            if results:
                print(f"✓ MILP completed in {elapsed:.2f}s")
                print(f"  Objective: {results['objective_value']:.2f}")
                print(f"  Status: {results['status']}")
                return {
                    'objective': results['objective_value'],
                    'time': elapsed,
                    'status': results['status'],
                    'solution': results['solution']
                }
            else:
                print(f"⚠ MILP did not find solution in {elapsed:.2f}s")
                return {
                    'objective': None,
                    'time': elapsed,
                    'status': 'NO_SOLUTION',
                    'solution': None
                }
        except Exception as e:
            print(f"❌ MILP failed: {e}")
            return {
                'objective': None,
                'time': None,
                'status': 'ERROR',
                'solution': None
            }
    
    
    def _run_hybrid(self, data, mh_time, milp_time, threads):
        """Run hybrid solver (Metaheuristics + MILP with warm start)."""
        print("Running Hybrid solver...")
        
        try:
            hybrid = HybridSolverCBC(data, self.lambda1, self.lambda2)
            results = hybrid.solve(
                metaheuristic='ILS',
                mh_max_iter=50,
                mh_max_time_min=mh_time,
                milp_time_limit=milp_time,
                threads=threads,
                use_warm_start=True,
                verbose=False
            )
            
            print(f"✓ Hybrid completed in {results['total_time']:.2f}s")
            print(f"  Best objective: {results['best_objective']:.2f} (via {results['best_method']})")
            
            return results
        except Exception as e:
            print(f"❌ Hybrid failed: {e}")
            return {
                'best_objective': None,
                'total_time': None,
                'best_method': 'ERROR'
            }
    
    def _store_results(self, milp_result, mh_result, mh_no_opt_result, hybrid_result):
        """Store results from all algorithms."""
        # MILP
        self.results['milp_cbc']['objectives'].append(milp_result['objective'])
        self.results['milp_cbc']['times'].append(milp_result['time'])
        self.results['milp_cbc']['status'].append(milp_result['status'])
        
        # Metaheuristics OPT ILS
        self.results['metaheuristics_ILS']['objectives'].append(mh_result['ils']['objective_value'])
        self.results['metaheuristics_ILS']['times'].append(mh_result['ils']['solve_time'])
        
        # Metaheuristics OPT VNS
        self.results['metaheuristics_VNS']['objectives'].append(mh_result['vns']['objective_value'])
        self.results['metaheuristics_VNS']['times'].append(mh_result['vns']['solve_time'])

        # Metaheuristics NO OPT ILS
        self.results['metaheuristics_no_opt_ILS']['objectives'].append(mh_no_opt_result['ils']['objective_value'])
        self.results['metaheuristics_no_opt_ILS']['times'].append(mh_no_opt_result['ils']['solve_time'])

        # Metaheuristics NO OPT VNS
        self.results['metaheuristics_no_opt_VNS']['objectives'].append(mh_no_opt_result['vns']['objective_value'])
        self.results['metaheuristics_no_opt_VNS']['times'].append(mh_no_opt_result['vns']['solve_time'])

        # Hybrid
        self.results['hybrid']['objectives'].append(hybrid_result['best_objective'])
        self.results['hybrid']['times'].append(hybrid_result['total_time'])
        self.results['hybrid']['best_method'].append(hybrid_result['best_method'])
    
    def _print_dataset_comparison(self, dataset_name, milp_result, mh_result, mh_no_opt_result, hybrid_result):
        """Print comparison for a single dataset."""
        print(f"\n{'─' * 80}")
        print(f"COMPARISON FOR {dataset_name}")
        print(f"{'─' * 80}")
        
        print(f"\n{'Algorithm':<30} {'Objective':<15} {'Time (s)':<12} {'Notes'}")
        print(f"{'-' * 80}")
        
        # MILP
        obj_str = f"{milp_result['objective']:.2f}" if milp_result['objective'] else "N/A"
        time_str = f"{milp_result['time']:.2f}" if milp_result['time'] else "N/A"
        print(f"{'MILP-CBC':<30} {obj_str:<15} {time_str:<12} {milp_result['status']}")
        
        # Metaheuristics ILS
        obj_str = f"{mh_result['ils']['objective_value']:.2f}" if mh_result['ils']['objective_value'] else "N/A"
        time_str = f"{mh_result['ils']['solve_time']:.2f}" if mh_result['ils']['solve_time'] else "N/A"
        print(f"{'Metaheuristics ILS':<30} {obj_str:<15} {time_str:<12}")
        
        # Metaheuristics VNS
        obj_str = f"{mh_result['vns']['objective_value']:.2f}" if mh_result['vns']['objective_value'] else "N/A"
        time_str = f"{mh_result['vns']['solve_time']:.2f}" if mh_result['vns']['solve_time'] else "N/A"
        print(f"{'Metaheuristics VNS':<30} {obj_str:<15} {time_str:<12}")
        
        # Metaheuristics NO-OPT ILS
        obj_str = f"{mh_no_opt_result['ils']['objective_value']:.2f}" if mh_no_opt_result['ils']['objective_value'] else "N/A"
        time_str = f"{mh_no_opt_result['ils']['solve_time']:.2f}" if mh_no_opt_result['ils']['solve_time'] else "N/A"
        print(f"{'Metaheuristics NO-OPT ILS':<30} {obj_str:<15} {time_str:<12}")
        
        # Metaheuristics NO-OPT VNS
        obj_str = f"{mh_no_opt_result['vns']['objective_value']:.2f}" if mh_no_opt_result['vns']['objective_value'] else "N/A"
        time_str = f"{mh_no_opt_result['vns']['solve_time']:.2f}" if mh_no_opt_result['vns']['solve_time'] else "N/A"
        print(f"{'Metaheuristics NO-OPT VNS':<30} {obj_str:<15} {time_str:<12}")
        
        # Hybrid
        obj_str = f"{hybrid_result['best_objective']:.2f}" if hybrid_result['best_objective'] else "N/A"
        time_str = f"{hybrid_result['total_time']:.2f}" if hybrid_result['total_time'] else "N/A"
        print(f"{'Hybrid':<30} {obj_str:<15} {time_str:<12} Best: {hybrid_result['best_method']}")
        
        # Determine winner
        valid_results = []
        if milp_result['objective']:
            valid_results.append(('MILP-CBC', milp_result['objective']))
        if mh_result['ils']['objective_value']:
            valid_results.append(('Metaheuristics ILS', mh_result['ils']['objective_value']))
        if mh_result['vns']['objective_value']:
            valid_results.append(('Metaheuristics VNS', mh_result['vns']['objective_value']))
        if mh_no_opt_result['ils']['objective_value']:
            valid_results.append(('Metaheuristics NO-OPT ILS', mh_no_opt_result['ils']['objective_value']))
        if mh_no_opt_result['vns']['objective_value']:
            valid_results.append(('Metaheuristics NO-OPT VNS', mh_no_opt_result['vns']['objective_value']))
        if hybrid_result['best_objective']:
            valid_results.append(('Hybrid', hybrid_result['best_objective']))
        
        if valid_results:
            winner = min(valid_results, key=lambda x: x[1])
            print(f"\n🏆 Best solution: {winner[0]} with objective {winner[1]:.2f}")
    
    def _generate_plots(self):
        """Generate comparison plots for objectives and times."""
        # Filter out None values for plotting
        dataset_names = []
        milp_objs = []
        mh_ils_objs = []
        mh_vns_objs = []
        mh_no_opt_ils_objs = []
        mh_no_opt_vns_objs = []
        hybrid_objs = []
        
        milp_times = []
        mh_ils_times = []
        mh_vns_times = []
        mh_no_opt_ils_times = []
        mh_no_opt_vns_times = []
        hybrid_times = []
        
        for i, name in enumerate(self.results['dataset_names']):
            milp_obj = self.results['milp_cbc']['objectives'][i]
            mh_ils_obj = self.results['metaheuristics_ILS']['objectives'][i]
            mh_vns_obj = self.results['metaheuristics_VNS']['objectives'][i]
            mh_no_opt_ils_obj = self.results['metaheuristics_no_opt_ILS']['objectives'][i]
            mh_no_opt_vns_obj = self.results['metaheuristics_no_opt_VNS']['objectives'][i]
            hybrid_obj = self.results['hybrid']['objectives'][i]

            milp_time = self.results['milp_cbc']['times'][i]
            mh_ils_time = self.results['metaheuristics_ILS']['times'][i]
            mh_vns_time = self.results['metaheuristics_VNS']['times'][i]
            mh_no_opt_ils_time = self.results['metaheuristics_no_opt_ILS']['times'][i]
            mh_no_opt_vns_time = self.results['metaheuristics_no_opt_VNS']['times'][i]
            hybrid_time = self.results['hybrid']['times'][i]
            
            # Only include if at least one algorithm has valid results
            if any([milp_obj, mh_ils_obj, mh_vns_obj, mh_no_opt_ils_obj, mh_no_opt_vns_obj, hybrid_obj]):
                dataset_names.append(name)
                milp_objs.append(milp_obj if milp_obj else np.nan)
                mh_ils_objs.append(mh_ils_obj if mh_ils_obj else np.nan)
                mh_vns_objs.append(mh_vns_obj if mh_vns_obj else np.nan)
                mh_no_opt_ils_objs.append(mh_no_opt_ils_obj if mh_no_opt_ils_obj else np.nan)
                mh_no_opt_vns_objs.append(mh_no_opt_vns_obj if mh_no_opt_vns_obj else np.nan)
                hybrid_objs.append(hybrid_obj if hybrid_obj else np.nan)

                milp_times.append(milp_time if milp_time else np.nan)
                mh_ils_times.append(mh_ils_time if mh_ils_time else np.nan)
                mh_vns_times.append(mh_vns_time if mh_vns_time else np.nan)
                mh_no_opt_ils_times.append(mh_no_opt_ils_time if mh_no_opt_ils_time else np.nan)
                mh_no_opt_vns_times.append(mh_no_opt_vns_time if mh_no_opt_vns_time else np.nan)
                hybrid_times.append(hybrid_time if hybrid_time else np.nan)
        
        if not dataset_names:
            print("⚠ No valid results to plot")
            return
        
        # Plot 1: Objective Values Comparison
        self._plot_objectives(dataset_names, milp_objs, mh_ils_objs, mh_vns_objs, 
                             mh_no_opt_ils_objs, mh_no_opt_vns_objs, hybrid_objs)
        
        # Plot 2: Running Times Comparison
        self._plot_times(dataset_names, milp_times, mh_ils_times, mh_vns_times,
                        mh_no_opt_ils_times, mh_no_opt_vns_times, hybrid_times)
        
        print(f"\n✓ Plots saved to '{self.output_dir}' directory")
    
    def _plot_objectives(self, dataset_names, milp_objs, mh_ils_objs, mh_vns_objs, 
                         mh_no_opt_ils_objs, mh_no_opt_vns_objs, hybrid_objs):
        """Plot objective values comparison."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(dataset_names))
        width = 0.13
        
        bars1 = ax.bar(x - 2.5*width, milp_objs, width, label='MILP-CBC', color='#2E86AB', alpha=0.8)
        bars2 = ax.bar(x - 1.5*width, mh_ils_objs, width, label='MH ILS', color='#792BAE', alpha=0.8)
        bars3 = ax.bar(x - 0.5*width, mh_vns_objs, width, label='MH VNS', color='#A23B72', alpha=0.8)
        bars4 = ax.bar(x + 0.5*width, mh_no_opt_ils_objs, width, label='MH-NoOpt ILS', color='#8FA23B', alpha=0.8)
        bars5 = ax.bar(x + 1.5*width, mh_no_opt_vns_objs, width, label='MH-NoOpt VNS', color='#C9184A', alpha=0.8)
        bars6 = ax.bar(x + 2.5*width, hybrid_objs, width, label='Hybrid', color='#F18F01', alpha=0.8)
        
        ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
        ax.set_ylabel('Objective Value', fontsize=12, fontweight='bold')
        ax.set_title('Algorithm Comparison: Objective Values\n(Lower is Better)', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(dataset_names, rotation=45, ha='right')
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        def autolabel(bars):
            for bar in bars:
                height = bar.get_height()
                if not np.isnan(height):
                    ax.annotate(f'{height:.1f}',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom',
                                fontsize=7, rotation=90)
        
        autolabel(bars1)
        autolabel(bars2)
        autolabel(bars3)
        autolabel(bars4)
        autolabel(bars5)
        autolabel(bars6)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/objective_comparison.png', dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {self.output_dir}/objective_comparison.png")
        plt.close()
    
    def _plot_times(self, dataset_names, milp_times, mh_ils_times, mh_vns_times,
                    mh_no_opt_ils_times, mh_no_opt_vns_times, hybrid_times):
        """Plot running times comparison."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(dataset_names))
        width = 0.13
        
        bars1 = ax.bar(x - 2.5*width, milp_times, width, label='MILP-CBC', color='#2E86AB', alpha=0.8)
        bars2 = ax.bar(x - 1.5*width, mh_ils_times, width, label='MH ILS', color='#792BAE', alpha=0.8)
        bars3 = ax.bar(x - 0.5*width, mh_vns_times, width, label='MH VNS', color='#A23B72', alpha=0.8)
        bars4 = ax.bar(x + 0.5*width, mh_no_opt_ils_times, width, label='MH-NoOpt ILS', color='#8FA23B', alpha=0.8)
        bars5 = ax.bar(x + 1.5*width, mh_no_opt_vns_times, width, label='MH-NoOpt VNS', color='#C9184A', alpha=0.8)
        bars6 = ax.bar(x + 2.5*width, hybrid_times, width, label='Hybrid', color='#F18F01', alpha=0.8)
        
        ax.set_xlabel('Dataset', fontsize=12, fontweight='bold')
        ax.set_ylabel('Running Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_title('Algorithm Comparison: Running Times\n(Lower is Better)', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(dataset_names, rotation=45, ha='right')
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        def autolabel(bars):
            for bar in bars:
                height = bar.get_height()
                if not np.isnan(height):
                    ax.annotate(f'{height:.1f}s',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom',
                                fontsize=7, rotation=90)
        
        autolabel(bars1)
        autolabel(bars2)
        autolabel(bars3)
        autolabel(bars4)
        autolabel(bars5)
        autolabel(bars6)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/time_comparison.png', dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {self.output_dir}/time_comparison.png")
        plt.close()
    
    def _print_final_summary(self):
        """Print final summary of all results."""
        print(f"\n{'=' * 80}")
        print("FINAL SUMMARY")
        print(f"{'=' * 80}")
        
        print(f"\nTotal datasets processed: {len(self.results['dataset_names'])}")
        
        # Count wins for each algorithm
        algorithm_wins = {
            'MILP-CBC': 0,
            'MH ILS': 0,
            'MH VNS': 0,
            'MH-NoOpt ILS': 0,
            'MH-NoOpt VNS': 0,
            'Hybrid': 0
        }
        
        for i in range(len(self.results['dataset_names'])):
            objectives = []
            if self.results['milp_cbc']['objectives'][i]:
                objectives.append(('MILP-CBC', self.results['milp_cbc']['objectives'][i]))
            if self.results['metaheuristics_ILS']['objectives'][i]:
                objectives.append(('MH ILS', self.results['metaheuristics_ILS']['objectives'][i]))
            if self.results['metaheuristics_VNS']['objectives'][i]:
                objectives.append(('MH VNS', self.results['metaheuristics_VNS']['objectives'][i]))
            if self.results['metaheuristics_no_opt_ILS']['objectives'][i]:
                objectives.append(('MH-NoOpt ILS', self.results['metaheuristics_no_opt_ILS']['objectives'][i]))
            if self.results['metaheuristics_no_opt_VNS']['objectives'][i]:
                objectives.append(('MH-NoOpt VNS', self.results['metaheuristics_no_opt_VNS']['objectives'][i]))
            if self.results['hybrid']['objectives'][i]:
                objectives.append(('Hybrid', self.results['hybrid']['objectives'][i]))
            
            if objectives:
                winner = min(objectives, key=lambda x: x[1])[0]
                algorithm_wins[winner] += 1
        
        print(f"\n🏆 Algorithm Performance:")
        for algo, wins in algorithm_wins.items():
            print(f"  {algo:<20} {wins} wins")
        
        # Average times
        def get_valid_times(times_list):
            return [t for t in times_list if t is not None]
        
        valid_milp_times = get_valid_times(self.results['milp_cbc']['times'])
        valid_mh_ils_times = get_valid_times(self.results['metaheuristics_ILS']['times'])
        valid_mh_vns_times = get_valid_times(self.results['metaheuristics_VNS']['times'])
        valid_mh_no_opt_ils_times = get_valid_times(self.results['metaheuristics_no_opt_ILS']['times'])
        valid_mh_no_opt_vns_times = get_valid_times(self.results['metaheuristics_no_opt_VNS']['times'])
        valid_hybrid_times = get_valid_times(self.results['hybrid']['times'])
        
        print(f"\n⏱️ Average Running Times:")
        if valid_milp_times:
            print(f"  MILP-CBC:           {np.mean(valid_milp_times):.2f}s")
        if valid_mh_ils_times:
            print(f"  MH ILS:             {np.mean(valid_mh_ils_times):.2f}s")
        if valid_mh_vns_times:
            print(f"  MH VNS:             {np.mean(valid_mh_vns_times):.2f}s")
        if valid_mh_no_opt_ils_times:
            print(f"  MH-NoOpt ILS:       {np.mean(valid_mh_no_opt_ils_times):.2f}s")
        if valid_mh_no_opt_vns_times:
            print(f"  MH-NoOpt VNS:       {np.mean(valid_mh_no_opt_vns_times):.2f}s")
        if valid_hybrid_times:
            print(f"  Hybrid:             {np.mean(valid_hybrid_times):.2f}s")
        
        # Average objectives
        def get_valid_objs(objs_list):
            return [o for o in objs_list if o is not None]
        
        valid_milp_objs = get_valid_objs(self.results['milp_cbc']['objectives'])
        valid_mh_ils_objs = get_valid_objs(self.results['metaheuristics_ILS']['objectives'])
        valid_mh_vns_objs = get_valid_objs(self.results['metaheuristics_VNS']['objectives'])
        valid_mh_no_opt_ils_objs = get_valid_objs(self.results['metaheuristics_no_opt_ILS']['objectives'])
        valid_mh_no_opt_vns_objs = get_valid_objs(self.results['metaheuristics_no_opt_VNS']['objectives'])
        valid_hybrid_objs = get_valid_objs(self.results['hybrid']['objectives'])
        
        print(f"\n📊 Average Objective Values:")
        if valid_milp_objs:
            print(f"  MILP-CBC:           {np.mean(valid_milp_objs):.2f}")
        if valid_mh_ils_objs:
            print(f"  MH ILS:             {np.mean(valid_mh_ils_objs):.2f}")
        if valid_mh_vns_objs:
            print(f"  MH VNS:             {np.mean(valid_mh_vns_objs):.2f}")
        if valid_mh_no_opt_ils_objs:
            print(f"  MH-NoOpt ILS:       {np.mean(valid_mh_no_opt_ils_objs):.2f}")
        if valid_mh_no_opt_vns_objs:
            print(f"  MH-NoOpt VNS:       {np.mean(valid_mh_no_opt_vns_objs):.2f}")
        if valid_hybrid_objs:
            print(f"  Hybrid:             {np.mean(valid_hybrid_objs):.2f}")
        
        print(f"\n{'=' * 80}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark and compare patient allocation algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on multiple datasets
  python benchmark_comparison.py -d data1.dat data2.dat data3.dat
  
  # Run on all .dat files in a directory
  python benchmark_comparison.py -d data/*.dat
  
  # Custom time limits and weights
  python benchmark_comparison.py -d data/*.dat --lambda1 0.6 --lambda2 0.4 --milp-time 600
  
  # Specify output directory
  python benchmark_comparison.py -d data/*.dat -o results
        """
    )
    
    parser.add_argument(
        "-d", "--datasets",
        nargs="+",
        required=True,
        help="List of .dat files to process"
    )
    
    parser.add_argument(
        "--lambda1",
        type=float,
        default=0.5,
        help="Weight for objective 1. Default: 0.5"
    )
    
    parser.add_argument(
        "--lambda2",
        type=float,
        default=0.5,
        help="Weight for objective 2. Default: 0.5"
    )
    
    parser.add_argument(
        "--milp-time",
        type=int,
        default=300,
        help="Time limit for pure MILP (seconds). Default: 300"
    )
    
    parser.add_argument(
        "--mh-ils-time",
        type=int,
        default=3,
        help="Time for ILS in metaheuristics (minutes). Default: 3"
    )
    
    parser.add_argument(
        "--mh-vns-time",
        type=int,
        default=3,
        help="Time for VNS in metaheuristics (minutes). Default: 3"
    )
    
    parser.add_argument(
        "--hybrid-mh-time",
        type=int,
        default=3,
        help="Time for metaheuristic phase in hybrid (minutes). Default: 3"
    )
    
    parser.add_argument(
        "--hybrid-milp-time",
        type=int,
        default=180,
        help="Time for MILP phase in hybrid (seconds). Default: 180"
    )
    
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for solvers. Default: 4"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output",
        help="Output directory for plots. Default: output"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Validate datasets exist
    valid_datasets = []
    for dataset in args.datasets:
        if os.path.exists(dataset):
            valid_datasets.append(dataset)
        else:
            print(f"⚠ Warning: Dataset '{dataset}' not found, skipping...")
    
    if not valid_datasets:
        print("❌ ERROR: No valid datasets found!")
        sys.exit(1)
    
    print(f"\n✓ Found {len(valid_datasets)} valid dataset(s)")
    
    # Create benchmark runner
    runner = BenchmarkRunner(
        valid_datasets,
        lambda1=args.lambda1,
        lambda2=args.lambda2,
        output_dir=args.output
    )
    
    # Run all benchmarks
    try:
        runner.run_all(
            milp_time_limit=args.milp_time,
            mh_ils_time=args.mh_ils_time,
            mh_vns_time=args.mh_vns_time,
            hybrid_mh_time=args.hybrid_mh_time,
            hybrid_milp_time=args.hybrid_milp_time,
            threads=args.threads
        )
        
        print(f"\n✓ Benchmark completed successfully!")
        print(f"  Results saved to: {args.output}/")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Execution interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ ERROR during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())